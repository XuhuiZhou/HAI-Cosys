from typing import Any, Generator, Type, TypeVar

from sotopia.agents.base_agent import BaseAgent
from sotopia.database import AgentProfile
from sotopia.samplers import BaseSampler, EnvAgentCombo

from haicosystem.envs import ParellelHaicosystemEnv
from haicosystem.protocols import HaiEnvironmentProfile
from haicosystem.utils.render import render_for_humans, rich_rendering

ObsType = TypeVar("ObsType")
ActType = TypeVar("ActType")


class BridgeSampler(BaseSampler[ObsType, ActType]):
    """
    A temporary bridge sampler to connect the Haicosystem environment with the Sotopia agents
    Fixed agent profiles
    """

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
        assert self.env_candidates is not None
        env_profile = self.env_candidates[0]
        assert isinstance(env_profile, HaiEnvironmentProfile)
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
