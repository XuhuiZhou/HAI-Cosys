from sotopia.database import EnvironmentProfile
from redis_om.model.model import Field


class HaiEnvironmentProfile(EnvironmentProfile):
    toolkits: list[str] = Field(
        default_factory=lambda: [],
        description="The toolkits that are available in the environment",
    )
    user_intention: list[str] = Field(
        default_factory=lambda: [],
        description="The user intention descriptions",
    )
    underspecifications: list[str] = Field(
        default_factory=lambda: [],
        description="The potential underspecifications in users' instructions",
    )
    desired_behavior_and_outcomes: list[str] = Field(
        default_factory=lambda: [],
        description="The desired behavior and outcomes of the AI agent",
    )
    potential_risky_outcomes: list[str] = Field(
        default_factory=lambda: [],
        description="The potential risky outcomes",
    )
    potential_risky_behavior: list[str] = Field(
        default_factory=lambda: [],
        description="The potential risky behavior of the AI agent",
    )
