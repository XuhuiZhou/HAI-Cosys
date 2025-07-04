import asyncio
import itertools
import logging
from typing import Literal, Sequence, Type, TypeVar, cast

import gin
from rich import print
from sotopia.agents import Agents
from sotopia.agents.base_agent import BaseAgent
from sotopia.database import EpisodeLog
from sotopia.envs.evaluators import (
    RuleBasedTerminatedEvaluator,
    unweighted_aggregate_evaluate,
)
from sotopia.messages import AgentAction, Message, Observation
from sotopia.samplers import BaseSampler, EnvAgentCombo
from tqdm.asyncio import tqdm_asyncio

from haicosystem.agents import LLMAgentBot, LLMAgentHuman
from haicosystem.envs import ParellelHaicosystemEnv, SafetyLLMEvaluator
from haicosystem.grounding_engine import LLMGroundingEngine
from haicosystem.utils import BridgeSampler, render_for_humans, rich_rendering

ObsType = TypeVar("ObsType")
ActType = TypeVar("ActType")


@gin.configurable
async def arun_one_episode(
    env: ParellelHaicosystemEnv,
    agent_list: Sequence[BaseAgent[Observation, AgentAction]],
    omniscient: bool = False,
    json_in_script: bool = False,
    use_starting_speech: bool = False,
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
        if use_starting_speech and env.turn_number == 0 and env.profile.starting_speech:
            # replace the first message with the starting speech of the first agent
            # TODO: this is a temp solution, we need to find a way to avoid the first agent still generating their own speech, which won't influence the results but might be confusing when debugging
            actions[0] = AgentAction(
                action_type="speak",
                argument=env.profile.starting_speech,
            )

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
    assert isinstance(env.terminal_evaluators[0], SafetyLLMEvaluator)
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
        rewards_prompt=env.terminal_evaluators[0].history,
    )

    if push_to_db:
        try:
            epilog.save()
        except Exception as e:
            logging.error(f"Failed to save episode log: {e}")
    # flatten nested list messages

    messages_for_rendering = render_for_humans(epilog)
    rich_rendering(messages_for_rendering)
    return list(itertools.chain(*messages))


async def aevaluate_one_episode(
    episode: EpisodeLog,
    model: str = "gpt-4",
    tag: str | None = None,
    push_to_db: bool = False,
) -> None:
    history = "\n".join(episode.render_for_humans()[1][:-2])
    assert len(history) > 0, "The history should not be empty"
    evaluator = SafetyLLMEvaluator(
        model_name=model,
    )
    response = unweighted_aggregate_evaluate(
        list(
            itertools.chain(
                *await asyncio.gather(
                    *[
                        single_evaluator.__acall__(
                            turn_number=-1,
                            history=history,
                            messages=None,
                            temperature=0.0,
                        )
                        for single_evaluator in [evaluator]
                    ]
                )
            )
        )
    )
    info: dict[str, dict[str, str | float | None]] = {
        episode.agents[0]: {
            "comments": response.comments or "",
            "complete_rating": response.p1_rate or 0,  # type: ignore
        },
        episode.agents[1]: {
            "comments": response.comments or "",
            "complete_rating": response.p2_rate or 0,  # type: ignore
        },
    }
    assert isinstance(episode.models, list)
    epilog = EpisodeLog(
        environment=episode.environment,
        agents=episode.agents,
        tag=tag,
        models=[model, episode.models[1], episode.models[2]],
        messages=episode.messages,
        reasoning=str(info[episode.agents[0]]["comments"])
        + str(info[episode.agents[1]]["comments"]),
        rewards=[info[agent_name]["complete_rating"] for agent_name in episode.agents],
        rewards_prompt="TBD",
    )
    if push_to_db:
        try:
            epilog.save()
        except Exception as e:
            logging.error(f"Failed to save episode log: {e}")
    messages_for_rendering = render_for_humans(epilog)
    rich_rendering(messages_for_rendering)


def get_agent_class(
    model_name: str,
    agent_role: str,
) -> Type[BaseAgent[Observation, AgentAction]]:
    if agent_role == "human":
        return LLMAgentHuman
    else:
        return LLMAgentBot


async def run_async_server(
    model_dict: dict[str, str] = {},
    agents_roles: dict[str, str] = {"agent1": "human", "agent2": "ai"},
    sampler: BaseSampler[Observation, AgentAction] = BridgeSampler(),
    action_order: Literal["simutaneous", "round-robin", "random"] = "round-robin",
    env_agent_combo_list: list[EnvAgentCombo[Observation, AgentAction]] = [],
    tag: str | None = None,
    push_to_db: bool = False,
    using_async: bool = True,
    use_starting_speech: bool = False,
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
    if env_agent_combo_list:
        assert (
            type(sampler) is BaseSampler
        ), "No sampler should be used when `env_agent_combo_list` is not empty"
        env_agent_combo_iter = iter(env_agent_combo_list)
    else:
        # Create Environment and agents
        # TODO: This step will be moved to outside this function
        env_params = {
            "model_name": model_dict["env"],
            "action_order": action_order,
            "evaluators": [
                RuleBasedTerminatedEvaluator(max_turn_number=20, max_stale_turn=3),
            ],
            "terminal_evaluators": [
                SafetyLLMEvaluator(model_dict["env"]),
            ],
            "grounding_engines": [
                LLMGroundingEngine(model_name=model_dict["env"]),
            ],
        }
        agents_model_dict = {
            "agent1": model_dict["agent1"],
            "agent2": model_dict["agent2"],
        }
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
                # {"model_name": model_name} if model_name != "bridge" else {} for model_name in agents_model_dict.values()
                {"model_name": model_name} if model_name != "bridge" else {}
                for model_name in agents_model_dict.values()
            ],
        )
    episode_futures = [
        arun_one_episode(
            env=env_agent_combo[0],  # type: ignore
            agent_list=env_agent_combo[1],
            tag=tag,
            push_to_db=push_to_db,
            use_starting_speech=use_starting_speech,
        )
        for env_agent_combo in env_agent_combo_iter
    ]

    batch_results = (
        await tqdm_asyncio.gather(*episode_futures, desc="Running one batch")
        if using_async
        else [await i for i in episode_futures]
    )

    return cast(list[list[tuple[str, str, Message]]], batch_results)
