from langchain.schema import AgentAction
from pydantic import Field
from sotopia.messages import Message, ScriptBackground
from sotopia.utils import format_docstring


class HaiScriptBackground(ScriptBackground):
    def to_natural_language(self) -> str:
        if self.p1_background or self.p2_background:
            p1_background = self.p1_background if self.p1_background else "Unknown"
            p2_background = self.p2_background if self.p2_background else "Unknown"
            # Not using AND, since in stranger relation the background is not visible
            return format_docstring(
                f"""Here is the context of this simulation:
            #### Scenario:
            {self.scenario}
            #### Background Information:
            Participants: {self.p1_name} and {self.p2_name}
            {self.p1_name}'s background: {p1_background}
            {self.p2_name}'s background: {p2_background}
            {self.p1_name}'s goal: {self.p1_goal}
            {self.p2_name}'s goal: {self.p2_goal}
            """
            )
        else:
            return format_docstring(
                f"""Here is the context of this simulation:
            #### Scenario:
            {self.scenario}
            #### Background Information:
            Participants: {self.p1_name} and {self.p2_name}
            {self.p1_name}'s goal: {self.p1_goal}
            {self.p2_name}'s goal: {self.p2_goal}
            """
            )


class SimulatedObservation(Message):
    """Simulated observation."""

    log: str = Field(
        description="a clear and concise summary of the [Simulator]'s step-by-step thought process ([Simulator Thought])for simulating accurate and realistic [Observation] for the tool call ([Action]/[Action Input]) based on corresponding [Tool Specifications]",
        default="",
    )
    thought_summary: str = Field(description="[Simulator Log Summary]", default="")
    observation: str = Field(
        description="[Observation]: the simulated tool execution output, which should be a JSON string with fields matching the tool's [Returns] specification.",
        default="",
    )

    def to_natural_language(self) -> str:
        return "Observation: \n" + self.observation

    def __str__(self) -> str:
        return self.observation

    def __repr__(self) -> str:
        return self.observation


class LangchainAgentAction(AgentAction):
    def action_api(self) -> None:
        # TODO: Implement the action API
        raise NotImplementedError
