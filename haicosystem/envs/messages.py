from pydantic import Field
from sotopia.messages import Message
from langchain.schema import AgentAction


class SimulatedObservation(Message):
    """Simulated observation."""

    observation: str = Field(description="the observation")
    thought_summary: str = Field(description="the thought summary", default="")
    log: str = Field(description="the log", default="")

    def to_natural_language(self) -> str:
        return "Observation: \n" + self.observation

    def __str__(self):
        return self.observation

    def __repr__(self):
        return self.observation


class LangchainAgentAction(AgentAction):
    def action_api(self):
        # TODO: Implement the action API
        raise NotImplementedError
