import json
import logging
from typing import Any, Optional, Sequence

from beartype import beartype
from pydantic import BaseModel

from sotopia.envs.evaluators import Evaluator
from sotopia.messages import Message, AgentAction

from haicosystem.generation_utils.generate import agenerate_simulated_observation
from haicosystem.protocols import SimulatedObservation, LangchainAgentAction
from haicosystem.envs.utils import format_tool_prompt
from haicosystem.tools import get_toolkits_by_names
from haicosystem.tools.tool_interface import BaseToolkit
from haicosystem.tools.utils import DummyToolWithMessage

from langchain.tools.base import BaseTool, StructuredTool
from langchain_core.utils.input import get_color_mapping

from haicosystem.generation_utils import (
    SIMULATOR_SYSTEM_INFO,
    SIMULATOR_PROMPT,
    SIMULATOR_CRITIQUE,
    SIMULATOR_CRITIQUE_REPEAT,
)
from .tool import validate_inputs

log = logging.getLogger("evaluators")


class SimulatorInputModel(BaseModel):
    simulator_scratchpad: Optional[Any]
    current_tool: Optional[str]
    current_tool_description: Optional[str]
    toolkit_descriptions: Optional[str]
    interaction_history: Optional[str]


@beartype
class LlmGroundingEngine(Evaluator):
    def __init__(self, model_name: str, response_format: str = "basic") -> None:
        self.model_name = model_name
        self.prompt = ""
        self.response_format = response_format
        self.name_to_tool_map: dict[str, BaseTool] = {}
        self.color_mapping: dict[str, str] = {}
        self.toolkits: list[StructuredTool] = []
        self.tools: list[BaseTool] = []
        self.tool_prompt: str = ""
        self.verbose = True
        self._input_keys: list[str] = ["input"]
        self.sim_system_info: str = SIMULATOR_SYSTEM_INFO
        self.sim_prompt_instruction: str = SIMULATOR_PROMPT
        self.critique_prompt: str = SIMULATOR_CRITIQUE
        self.critique_prompt_repeat: str = SIMULATOR_CRITIQUE_REPEAT
        self.max_allowed_steps: int = 1
        self.num_critique_steps: int = 0
        self.tool_names: list[str] = []

    @staticmethod
    def get_all_tools(toolkits: Sequence[BaseToolkit]) -> list[BaseTool]:
        """Return all tools available to the agent."""
        all_tools = []
        for toolkit in toolkits:
            all_tools += toolkit.tools
        return all_tools

    def create_prompt(
        self,
        toolkits_names: list[str],
    ) -> str:
        """Create prompt in the style of the zero shot agent."""
        toolkits = get_toolkits_by_names(toolkits_names)
        # initialize the engine
        self.toolkits = toolkits  # type: ignore
        self.name_to_tool_map = {
            tool.name: tool for tool in self.get_all_tools(toolkits)
        }
        self.tools = self.get_all_tools(toolkits)
        # We construct a mapping from each tool to a color, used for logging.
        self.color_mapping = get_color_mapping(
            [tool.name for tool in self.tools], excluded_colors=["green", "red"]
        )
        toolkit_strings = "\n".join(
            [toolkit.create_description("medium") for toolkit in toolkits]
        )
        self.tool_names = [tool.name for tool in self.get_all_tools(toolkits)]
        tool_prompt = format_tool_prompt(toolkit_strings, ", ".join(self.tool_names))
        self.tool_prompt = tool_prompt
        return tool_prompt

    def _get_current_toolkit_descriptions(self, tool_name: str) -> str:
        # NOTE: assume only one toolkit has the tool with tool_name
        for toolkit in self.toolkits:
            for tool in toolkit.tools:  # type: ignore
                if tool.name == tool_name:
                    return toolkit.create_description(detail_level="low")  # type: ignore
        raise ValueError(f"Tool {tool_name} not found in any of the toolkits.")

    def __call__(
        self, turn_number: int, messages: list[tuple[str, Message]]
    ) -> list[tuple[str, tuple[tuple[str, int | float | bool], str]]]:
        raise NotImplementedError(
            "ReachGoalLLMEvaluator is not implemented for synchronous evaluation"
        )

    def tool_run_logging_kwargs(
        self,
    ) -> dict[
        str, str
    ]:  # copied from langchain, hard-coded for now; still not sure why we need this
        return {"llm_prefix": "Thought:", "observation_prefix": "Observation: "}

    @property
    def input_keys(self) -> list[str]:
        return self._input_keys

    @property
    def generatetion_prefix(self) -> str:
        return "Simulator Thought: "

    @property
    def observation_prefix(self) -> str:
        return "Observation:"

    @property
    def thought_summary_prefix(self) -> str:
        return "Simulator Log Summary:"

    @property
    def stop_seqs(self) -> list[str]:
        return [
            "\nThought:",
            "\n\tThought:",  # or {agent.llm_prefix.rstrip()}
            "\nAction:",
            "\n\tAction:",
        ]

    def parse_action(self, action: str) -> LangchainAgentAction:
        json_action = json.loads(action)
        new_action = LangchainAgentAction(**json_action)
        return new_action

    async def __acall__(  # type: ignore
        self,
        messages: list[tuple[str, Message]] | None,
        history: str = "",
        temperature: float = 0.0,
    ) -> list[SimulatedObservation]:
        # filter did nothing
        if not history and messages:
            messages_filtered = [
                (x, y)
                for x, y in messages
                if "did nothing" not in y.to_natural_language()
            ]
            history = "\n".join(
                [
                    (
                        f"{x} {y.to_natural_language()}"
                        if x != "Environment"
                        else y.to_natural_language()
                    )
                    for x, y in messages_filtered
                ]
            )
        messages_in_single_turn = []
        assert messages is not None
        for message in messages[::-1]:
            if message[0] == "Environment" and message[
                1
            ].to_natural_language().startswith("Turn"):
                break
            else:
                messages_in_single_turn.append(message)
        for message in messages_in_single_turn:
            # TODO: Add a lock mechanism to prevent multiple agents from calling the same tool
            _, message_content = message
            if (
                isinstance(message_content, AgentAction)
                and message_content.action_type == "action"
            ):
                tool_action = self.parse_action(message_content.argument)
                tool = self.name_to_tool_map[tool_action.tool]
                simulator_scratchpad = ""
                tool_run_kwargs = self.tool_run_logging_kwargs()
                try:
                    # params = load_dict(raw_inputs)
                    validate_inputs(tool.parameters, tool_action.tool_input)  # type: ignore
                except Exception as e:
                    error_observation = await DummyToolWithMessage().arun(
                        f'{{"error": "InvalidRequestException: {e}"}}',
                        **tool_run_kwargs,  # type: ignore
                    )
                    assert isinstance(error_observation, SimulatedObservation)
                    return [error_observation]
                observation = await agenerate_simulated_observation(
                    model_name=self.model_name,
                    history=history,
                    current_tool=tool_action.tool,
                    current_tool_description=tool.description,
                    toolkit_descriptions=self._get_current_toolkit_descriptions(
                        tool_action.tool
                    ),
                    simulator_scratchpad=simulator_scratchpad,
                    temperature=temperature,
                )
                return [observation]
        return [SimulatedObservation(observation="", thought_summary="", log="")]
