import asyncio
import json
import rich
import gin
import logging
import itertools
from sotopia.database import EpisodeLog
from typing import Literal, Type, cast, Any, Generator, TypeVar, Sequence

from beartype import beartype
from tqdm.asyncio import tqdm_asyncio

from sotopia.agents import LLMAgent
from sotopia.agents.base_agent import BaseAgent
from sotopia.envs.evaluators import (
    RuleBasedTerminatedEvaluator,
)
from sotopia.generation_utils.generate import LLM_Name
from sotopia.messages import AgentAction, Message, Observation
from sotopia.database import AgentProfile
from sotopia.samplers import BaseSampler, EnvAgentCombo
from sotopia.agents import Agents

from haicosystem.envs import ParellelHaicosystemEnv
from haicosystem.envs.database import HaiEnvironmentProfile
from haicosystem.agents import LLMAgentX
from haicosystem.envs.evaluators import SafetyLLMEvaluator
from haicosystem.envs.llm_engine import LlmGroundingEngine

ObsType = TypeVar("ObsType")
ActType = TypeVar("ActType")


class BridgeSampler(BaseSampler[ObsType, ActType]):
    def sample(
        self,
        agent_classes: Type[BaseAgent[ObsType, ActType]]
        | list[Type[BaseAgent[ObsType, ActType]]],
        n_agent: int = 3,
        replacement: bool = True,
        size: int = 1,
        env_params: dict[str, Any] = {},
        agents_params: list[dict[str, Any]] = [{}, {}],
    ) -> Generator[EnvAgentCombo[ObsType, ActType], None, None]:
        # This is a simplified version of the original function
        # The original function is not provided in the snippet
        assert (
            not isinstance(agent_classes, list) or len(agent_classes) == n_agent
        ), f"agent_classes should be a list of length {n_agent} or a single agent class"

        if not isinstance(agent_classes, list):
            agent_classes = [agent_classes] * n_agent
        assert (
            len(agents_params) == n_agent
        ), f"agents_params should be a list of length {n_agent}"
        filename = "./data/example_scenarios.json"
        with open(filename, "r") as file:
            env_profiles_json = json.load(file)
        env_profile = HaiEnvironmentProfile.parse_obj(env_profiles_json["official_122"])
        env = ParellelHaicosystemEnv(env_profile=env_profile, **env_params)
        agent_profiles = [
            AgentProfile.parse_obj(
                {
                    "first_name": "Xuhui",
                    "last_name": "Zhou",
                    "age": 30,
                    "occupation": "Software Engineer",
                }
            ),
            AgentProfile.parse_obj(
                {
                    "first_name": "X",
                    "last_name": "AI",
                    "occupation": "AI Assistant",
                }
            ),
        ]
        for _ in range(size):
            agents = [
                agent_class(agent_profile=agent_profile, **agent_params)
                for agent_class, agent_profile, agent_params in zip(
                    agent_classes, agent_profiles, agents_params
                )
            ]
            for agent, goal in zip(agents, env.profile.agent_goals):
                agent.goal = goal
            yield env, agents


def render_for_humans(episode: EpisodeLog) -> list[str]:
    """Generate a human readable version of the episode log.

    Returns:
        A tuple of (a list of agent_profiles, a list of str): The agent profiles, and the messages and rewards in each turn.
    """

    messages_and_rewards = []
    for idx, turn in enumerate(episode.messages):
        messages_in_this_turn = []
        if idx == 0:
            assert (
                len(turn) >= 2
            ), "The first turn should have at least environemnt messages"
            messages_in_this_turn.append(turn[0][2])
            messages_in_this_turn.append(turn[1][2])
        for sender, receiver, message in turn:
            if receiver == "Environment":
                if sender != "Environment":
                    if "did nothing" in message:
                        continue
                    else:
                        if "said:" in message:
                            messages_in_this_turn.append(f"{sender} {message}")
                        else:
                            messages_in_this_turn.append(f"{sender}: {message}")
                else:
                    messages_in_this_turn.append(message)
        messages_and_rewards.append("\n".join(messages_in_this_turn))
    messages_and_rewards.append(f"The reasoning is:\n{episode.reasoning}")
    messages_and_rewards.append(
        f"The rewards are:\nAgent 1: {episode.rewards[0]}\nAgent 2: {episode.rewards[1]}"
    )
    return messages_and_rewards


@gin.configurable
async def arun_one_episode(
    env: ParellelHaicosystemEnv,
    agent_list: Sequence[BaseAgent[Observation, AgentAction]],
    omniscient: bool = False,
    script_like: bool = False,
    json_in_script: bool = False,
    tag: str | None = None,
    push_to_db: bool = False,
) -> list[tuple[str, str, Message]]:
    agents = Agents({agent.agent_name: agent for agent in agent_list})
    environment_messages = env.reset(agents=agents, omniscient=omniscient)
    agents.reset()

    messages: list[list[tuple[str, str, Message]]] = []

    # Main Event Loop
    done = False
    messages.append(
        [
            ("Environment", agent_name, environment_messages[agent_name])
            for agent_name in env.agents
        ]
    )
    # set goal for agents
    for index, agent_name in enumerate(env.agents):
        agents[agent_name].goal = env.profile.agent_goals[index]
    rewards: list[list[float]] = []
    reasons: list[str] = []
    while not done:
        # gather agent messages
        agent_messages: dict[str, AgentAction] = dict()
        actions = await asyncio.gather(
            *[
                agents[agent_name].aact(environment_messages[agent_name])
                for agent_name in env.agents
            ]
        )
        if script_like:
            # manually mask one message
            agent_mask = env.action_mask
            for idx in range(len(agent_mask)):
                print("Current mask: ", agent_mask)
                if agent_mask[idx] == 0:
                    print("Action not taken: ", actions[idx])
                    actions[idx] = AgentAction(action_type="none", argument="")
                else:
                    print("Current action taken: ", actions[idx])

        # actions = cast(list[AgentAction], actions)
        for idx, agent_name in enumerate(env.agents):
            agent_messages[agent_name] = actions[idx]

            messages[-1].append((agent_name, "Environment", agent_messages[agent_name]))

        # send agent messages to environment
        (
            environment_messages,
            rewards_in_turn,
            terminated,
            ___,
            info,
        ) = await env.astep(agent_messages)
        messages.append(
            [
                ("Environment", agent_name, environment_messages[agent_name])
                for agent_name in env.agents
            ]
        )
        # print("Environment message: ", environment_messages)
        # exit(0)
        rewards.append([rewards_in_turn[agent_name] for agent_name in env.agents])
        reasons.append(
            " ".join(info[agent_name]["comments"] for agent_name in env.agents)
        )
        done = all(terminated.values())

    # TODO: clean up this part
    epilog = EpisodeLog(
        environment=env.profile.pk,
        agents=[agent.profile.pk for agent in agent_list],
        tag=tag,
        models=[env.model_name, agent_list[0].model_name, agent_list[1].model_name],
        messages=[
            [(m[0], m[1], m[2].to_natural_language()) for m in messages_in_turn]
            for messages_in_turn in messages
        ],
        reasoning=info[env.agents[0]]["comments"],
        rewards=[info[agent_name]["complete_rating"] for agent_name in env.agents],
        rewards_prompt=info["rewards_prompt"]["overall_prompt"],
    )
    rich.print(epilog.rewards_prompt)
    conversation = render_for_humans(epilog)
    for message in conversation:
        rich.print(message)

    if push_to_db:
        try:
            epilog.save()
        except Exception as e:
            logging.error(f"Failed to save episode log: {e}")
    # flatten nested list messages
    return list(itertools.chain(*messages))


def get_agent_class(
    model_name: str,
    agent_role: str,
) -> Type[BaseAgent[Observation, AgentAction]]:
    if agent_role == "human":
        return LLMAgentX
    else:
        return LLMAgent


@beartype
async def run_server(
    model_dict: dict[str, LLM_Name],
    agents_roles: dict[str, str],
    sampler: BaseSampler[Observation, AgentAction] = BridgeSampler(),
    action_order: Literal["simutaneous", "round-robin", "random"] = "round-robin",
    env_agent_combo_list: list[EnvAgentCombo[Observation, AgentAction]] = [],
    tag: str | None = None,
    push_to_db: bool = False,
    using_async: bool = True,
) -> list[list[tuple[str, str, Message]]]:
    """
    Doc incomplete

    Args:
        omniscient (bool): Whether the agent knows the goal of the other, default to False
        script_like (bool): Whether we generate the turn in script like manner, default to False
        json_in_script (bool): Whether we requires the script generator to return json (Only valid when script_like is True), default to False

    Note: env_agent_combo_list is optional. When it defaults to [], sampler is used
    else the sampler is not used. Please pass in BaseSampler or simply not specify it when using this option.
    """

    assert not (push_to_db and tag is None), "please provide a tag when push to db"

    # Create Environment and agents
    # This step will be moved to outside this function

    env_params = {
        "model_name": model_dict["env"],
        "action_order": action_order,
        "evaluators": [
            RuleBasedTerminatedEvaluator(max_turn_number=20, max_stale_turn=2),
        ],
        "terminal_evaluators": [
            SafetyLLMEvaluator(model_dict["env"]),
        ],
        "grounding_engines": [
            LlmGroundingEngine(model_name=model_dict["env"]),
        ],
    }
    agents_model_dict = {
        "agent1": model_dict["agent1"],
        "agent2": model_dict["agent2"],
    }

    if env_agent_combo_list:
        assert (
            type(sampler) is BaseSampler
        ), "No sampler should be used when `env_agent_combo_list` is not empty"
        env_agent_combo_iter = iter(env_agent_combo_list)
    else:
        env_agent_combo_iter = sampler.sample(
            agent_classes=[
                get_agent_class(model_name, agents_role)
                for model_name, agents_role in zip(
                    agents_model_dict.values(), agents_roles.values()
                )
            ],
            n_agent=len(agents_model_dict),
            env_params=env_params,
            agents_params=[
                {"model_name": model_name} if model_name != "bridge" else {}
                for model_name in agents_model_dict.values()
            ],
        )
    episode_futures = [
        arun_one_episode(
            env=env_agent_combo[0],
            agent_list=env_agent_combo[1],
            tag=tag,
            push_to_db=push_to_db,
        )
        for env_agent_combo in env_agent_combo_iter
    ]

    batch_results = (
        await tqdm_asyncio.gather(*episode_futures, desc="Running one batch")
        if using_async
        else [await i for i in episode_futures]
    )

    return cast(list[list[tuple[str, str, Message]]], batch_results)
