from sotopia.database import EnvironmentProfile
from redis_om.model.model import Field


class HaiEnvironmentProfile(EnvironmentProfile):
    toolkits: list[str] = Field(
        default_factory=lambda: [],
        description="The toolkits that are available in the environment",
    )
