import asyncio
import itertools
import random
import logging
from collections import defaultdict
from typing import Literal, Any

from beartype import beartype
from pydantic import Field

from sotopia.envs import ParallelSotopiaEnv
from sotopia.envs.evaluators import (
    Evaluator,
    unweighted_aggregate_evaluate,
    _reduce,
)
from sotopia.envs.parallel import _actions_to_natural_language, render_text_for_agent
from sotopia.database import EnvironmentProfile
from sotopia.messages import (
    ActionType,
    AgentAction,
    Observation,
    SimpleMessage,
    ScriptEnvironmentResponse,
)

from haicosystem.protocols import HaiEnvironmentProfile, SimulatedObservation
from haicosystem.envs.llm_engine import LLMGroundingEngine

log = logging.getLogger("evaluators")


class ScriptEnvironmentResponsePlus(ScriptEnvironmentResponse):
    observation: SimulatedObservation = Field(
        description="All of the comments supporting the termination and rating"
    )


@beartype
def unweighted_aggregate_response(
    responses: list[
        tuple[str, tuple[tuple[str, int | float | bool], str]] | SimulatedObservation
    ],
) -> ScriptEnvironmentResponsePlus:
    """
    Aggregate the responses from the environment

    Args:
        responses (list[tuple[str, tuple[tuple[str, int | bool], str]]]): list of responses from the environment
        Each response is a tuple of (agent_name/environment, (response, reasoning))
    """
    responses_dict: dict[str, list[tuple[tuple[str, int | float | bool], str]]] = (
        defaultdict(list)
    )
    for response in responses:
        if isinstance(response, SimulatedObservation):
            assert (
                len(responses_dict["engine"]) == 0
            )  # TODO: allow multiple engine responses
            engine_response = ("engine", response)
        else:
            assert response[0] == "environment" or response[0].startswith("agent")
            responses_dict[response[0]].append(response[1])

    environment_responses: tuple[dict[str, float | int | bool], str] = ({}, "")
    agent_1_responses: tuple[dict[str, float | int | bool], str] = ({}, "")
    agent_2_responses: tuple[dict[str, float | int | bool], str] = ({}, "")
    for k, v in responses_dict.items():
        if k == "environment":
            assert isinstance(v, list)
            environment_responses = _reduce(v)
        elif k == "engine":
            continue
        else:
            if k == "agent_1":
                agent_1_responses = _reduce(v)
            elif k == "agent_2":
                agent_2_responses = _reduce(v)
            else:
                # TODO: supports more than two agents
                raise ValueError(f"Only supports agent_1 and agent_2, got {k}")

    comments = (
        (
            f"Environment comments: {environment_responses[1]}\n"
            if environment_responses[1]
            else ""
        )
        + (
            f"Agent 1 comments:\n{agent_1_responses[1]}\n"
            if agent_1_responses[1]
            else ""
        )
        + (
            f"Agent 2 comments:\n{agent_2_responses[1]}\n"
            if agent_2_responses[1]
            else ""
        )
    )
    if (
        "terminated" in environment_responses[0]
        and environment_responses[0]["terminated"]
    ):
        log.debug(f"[green] The conversation is terminated. {response}")
    return ScriptEnvironmentResponsePlus(
        terminated=environment_responses[0]["terminated"]
        if "terminated" in environment_responses[0]
        else False,
        p1_rate=(
            agent_1_responses[0]["overall_score"]
            if "overall_score" in agent_1_responses[0]
            else 0,
            agent_1_responses[0],
        )
        if agent_1_responses != ({}, "")
        else None,
        p2_rate=(
            agent_2_responses[0]["overall_score"]
            if "overall_score" in agent_2_responses[0]
            else 0,
            agent_2_responses[0],
        )
        if agent_2_responses != ({}, "")
        else None,
        comments=comments,
        observation=engine_response[1],
    )


class ParellelHaicosystemEnv(ParallelSotopiaEnv):
    def __init__(
        self,
        available_action_types: set[ActionType] = set(
            ["none", "speak", "non-verbal communication", "action", "leave"]
        ),
        action_order: Literal["simutaneous", "round-robin", "random"] = "simutaneous",
        model_name: str = "gpt-3.5-turbo",
        evaluators: list[Evaluator] = [],
        terminal_evaluators: list[Evaluator] = [],
        grounding_engines: list[
            Evaluator
        ] = [],  # temp implementation; evaluator should share the same interface as engines
        uuid_str: str | None = None,
        env_profile: HaiEnvironmentProfile | None = None,
    ):
        super().__init__(
            env_profile=EnvironmentProfile(),
            available_action_types=available_action_types,
            action_order=action_order,  # type: ignore
            model_name=model_name,
            evaluators=evaluators,
            terminal_evaluators=terminal_evaluators,
            uuid_str=uuid_str,
        )
        self.profile: HaiEnvironmentProfile = env_profile  # type: ignore
        assert (
            len(grounding_engines) == 1
        )  # temp implementation; only one grounding engine is supported
        self.grounding_engine: LLMGroundingEngine = grounding_engines[0]  # type: ignore
        self.engines_and_evaluators = grounding_engines + evaluators
        self.profile.scenario = self.prepare_scenario(self.profile)

    def prepare_scenario(self, env_profile: HaiEnvironmentProfile) -> str:
        tool_prompt = self.grounding_engine.create_prompt(env_profile.toolkits)
        tool_prompt = tool_prompt.replace("<", "&lt;").replace(
            ">", "&gt;"
        )  # TODO: temp fix for the bug in the xml renderer
        environment_info = "\n".join(
            f"### {key}:\n" + " ".join(getattr(env_profile, key))
            for key in [
                "user_intention",
                "underspecifications",
                "desired_behavior_and_outcomes",
                "potential_risky_outcomes",
                "potential_risky_behavior",
            ]
        )
        new_scenario = (
            env_profile.scenario
            + "\n"
            + f"<extra_info viewer='environment'>{environment_info}</extra_info>"
            + "\n"
            + f"<extra_info viewer='agent_1'>{tool_prompt}</extra_info>"
        )  # temp implementation; only agent_0 is able to use the tools
        return new_scenario

    @beartype
    async def astep(
        self, actions: dict[str, AgentAction] | dict[str, dict[str, int | str]]
    ) -> tuple[
        dict[str, Observation],
        dict[str, float],
        dict[str, bool],
        dict[str, bool],
        dict[str, dict[Any, Any]],
    ]:
        # Time step ++
        self.turn_number += 1
        self.act_last_time = len(self.agents) - 1
        # For action sampled from action space, it needs to be converted into AgentAction
        complied_actions: dict[str, AgentAction] = {}
        for key in actions.keys():
            action = actions[key]
            if isinstance(action, AgentAction):
                complied_actions[key] = action
            else:
                action["action_type"] = self.available_action_types[
                    int(action["action_type"])
                ]
                complied_actions[key] = AgentAction.parse_obj(action)

        # Masking actions from agent that are in turn
        for idx, agent in enumerate(self.agents):
            if not self.action_mask[idx]:
                complied_actions[agent] = AgentAction(action_type="none", argument="")
        self.recv_message(
            "Environment", SimpleMessage(message=f"Turn #{self.turn_number}")
        )
        for agent, action in complied_actions.items():
            self.recv_message(agent, action)

        response = unweighted_aggregate_response(
            list(
                itertools.chain(
                    *await asyncio.gather(
                        *[
                            engine.__acall__(
                                turn_number=self.turn_number,
                                messages=self.inbox,
                            )
                            for engine in self.engines_and_evaluators
                        ]
                    )
                )
            )
        )

        if response.terminated:
            terminal_response = unweighted_aggregate_evaluate(
                list(
                    itertools.chain(
                        *await asyncio.gather(
                            *[
                                evaluator.__acall__(
                                    turn_number=self.turn_number,
                                    messages=self.inbox,
                                )
                                for evaluator in self.terminal_evaluators
                            ]
                        )
                    )
                )
            )
            # incorporate terminal response into response
            response.p1_rate = response.p1_rate or terminal_response.p1_rate
            response.p2_rate = response.p2_rate or terminal_response.p2_rate
            if response.comments and terminal_response.comments:
                response.comments += terminal_response.comments
            elif terminal_response.comments:
                response.comments = terminal_response.comments

        self.action_mask = [False for _ in self.agents]
        if self.action_order == "round-robin":
            # lock if the engine has output an observation, then the agent continues
            if response.observation:
                self.action_mask[1] = (
                    True  # TODO: assert the second agent is always the AI agent
                )
                self.action_mask[0] = False
            else:
                self.act_last_time = (self.act_last_time + 1) % len(self.agents)
                self.action_mask[self.act_last_time] = True
        elif self.action_order == "random":
            self.action_mask[random.randint(0, len(self.action_mask) - 1)] = True
        else:
            self.action_mask = [True for _ in self.agents]
        obs = _actions_to_natural_language(complied_actions)
        if response.observation.observation:
            self.recv_message(
                "Environment", response.observation
            )  # TODO: only one engine response is supported
            obs += f"\n{response.observation.to_natural_language()}"
        info = {
            self.background.p1_name: {
                "comments": response.comments or "",
                "complete_rating": response.p1_rate or 0,
            },
            self.background.p2_name: {
                "comments": response.comments or "",
                "complete_rating": response.p2_rate or 0,
            },
        }
        if response.terminated:
            info["rewards_prompt"] = {
                "overall_prompt": self.terminal_evaluators[0].prompt  # type: ignore
            }

        return (
            {
                self.background.p1_name: Observation(
                    last_turn=render_text_for_agent(obs, agent_id=0),
                    turn_number=self.turn_number,
                    available_actions=list(self.available_action_types)
                    if self.action_mask[0]
                    else ["none"],
                ),
                self.background.p2_name: Observation(
                    last_turn=render_text_for_agent(obs, agent_id=1),
                    turn_number=self.turn_number,
                    available_actions=[
                        "none",
                        "action",
                        "leave",
                    ]  # TODO: make this a hyperparameter that can be set to control the information flow; also this somehow always means that actions are towards engines, which is not always the case.
                    if self.action_mask[1]
                    else ["none"],
                ),
            },
            {
                self.background.p1_name: (
                    response.p1_rate
                    if isinstance(response.p1_rate, float)
                    else response.p1_rate[0]
                )
                if response.p1_rate
                else 0,
                self.background.p2_name: (
                    response.p2_rate
                    if isinstance(response.p2_rate, float)
                    else response.p2_rate[0]
                )
                if response.p2_rate
                else 0,
            },
            {
                self.background.p1_name: response.terminated,
                self.background.p2_name: response.terminated,
            },
            {
                self.background.p1_name: False,
                self.background.p2_name: False,
            },
            info,
        )
