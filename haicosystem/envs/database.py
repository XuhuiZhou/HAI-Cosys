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
    disired_outcome: list[str] = Field(
        default_factory=lambda: [],
        description="The desired behavior and outcomes of the AI agent",
    )
    risky_outcome: list[str] = Field(
        default_factory=lambda: [],
        description="The risky outcomes of the AI agent",
    )
