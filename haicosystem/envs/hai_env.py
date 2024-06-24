from sotopia.envs import ParallelSotopiaEnv
from typing import Literal
from sotopia.envs.evaluators import Evaluator
from sotopia.messages import ActionType
from sotopia.database import EnvironmentProfile


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
        uuid_str: str | None = None,
        env_profile: EnvironmentProfile | None = None,
    ):
        super().__init__(
            env_profile=env_profile,
            available_action_types=available_action_types,
            action_order=action_order,
            model_name=model_name,
            evaluators=evaluators,
            terminal_evaluators=terminal_evaluators,
            uuid_str=uuid_str,
        )
