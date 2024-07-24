import json
import logging
from typing import Sequence, Type
from pydantic import BaseModel

from beartype import beartype

from sotopia.envs.evaluators import Evaluator
from sotopia.messages import Message, AgentAction

from haicosystem.protocols import SimulatedObservation, LangchainAgentAction
from haicosystem.envs.utils import format_tool_prompt
from haicosystem.tools import get_toolkit_output_parser_by_names, get_toolkits_by_names
from haicosystem.tools.tool_interface import BaseToolkit
from haicosystem.tools.utils import DummyToolWithMessage

from langchain.tools.base import BaseTool

from haicosystem.generation_utils import (
    SIMULATOR_SYSTEM_INFO,
    SIMULATOR_PROMPT,
    SIMULATOR_CRITIQUE,
    SIMULATOR_CRITIQUE_REPEAT,
    obtain_history_for_environment,
    agenerate_simulated_observation,
    validate_observation,
)
from .tool import validate_inputs

log = logging.getLogger("evaluators")


@beartype
class LLMGroundingEngine(Evaluator):
    def __init__(self, model_name: str, response_format: str = "basic") -> None:
        self.model_name = model_name
        self.prompt = ""
        self.response_format = response_format
        self.name_to_tool_map: dict[str, BaseTool] = {}
        self.toolkits: Sequence[BaseToolkit] = []
        self.tool_parser: dict[str, Type[BaseModel]] = {}
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

    def _get_current_toolkit_descriptions(self, tool_name: str) -> str:
        # NOTE: assume only one toolkit has the tool with tool_name
        for toolkit in self.toolkits:
            for tool in toolkit.tools:
                if tool.name == tool_name:
                    return toolkit.create_description(detail_level="low")
        raise ValueError(f"Tool {tool_name} not found in any of the toolkits.")

    def create_prompt(
        self,
        toolkits_names: list[str],
    ) -> str:
        """Create prompt in the style of the zero shot agent."""
        # initialize the engine
        self.toolkits = get_toolkits_by_names(toolkits_names)
        self.tool_parser = get_toolkit_output_parser_by_names(toolkits_names)
        self.name_to_tool_map = {
            tool.name: tool for tool in self.get_all_tools(self.toolkits)
        }
        self.tools = self.get_all_tools(self.toolkits)
        toolkit_strings = "\n".join(
            [toolkit.create_description("medium") for toolkit in self.toolkits]
        )
        self.tool_names = [tool.name for tool in self.get_all_tools(self.toolkits)]
        tool_prompt = format_tool_prompt(toolkit_strings, ", ".join(self.tool_names))
        self.tool_prompt = tool_prompt
        return tool_prompt

    def tool_run_logging_kwargs(
        self,
    ) -> dict[
        str, str
    ]:  # copied from langchain, hard-coded for now; still not sure why we need this
        return {"llm_prefix": "Thought:", "observation_prefix": "Observation: "}

    def parse_action(self, action: str) -> LangchainAgentAction:
        json_action = json.loads(action)
        new_action = LangchainAgentAction(**json_action)
        return new_action

    def __call__(
        self, turn_number: int, messages: list[tuple[str, Message]]
    ) -> list[tuple[str, tuple[tuple[str, int | float | bool], str]]]:
        raise NotImplementedError(
            "ReachGoalLLMEvaluator is not implemented for synchronous evaluation"
        )

    async def __acall__(  # type: ignore
        self,
        turn_number: int,
        messages: list[tuple[str, Message]] | None,
        history: str = "",
        temperature: float = 0.0,
    ) -> list[SimulatedObservation]:
        # filter did nothing
        if not history and messages:
            history = obtain_history_for_environment(messages)
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
                tool = self.name_to_tool_map.get(tool_action.tool, None)
                if not tool:
                    return [
                        SimulatedObservation(
                            observation=f'{{"error": InvalidRequestException: Tool {tool_action.tool} not found in the toolkits. Please use one of the following tools: {", ".join(self.tool_names)}}}',
                            thought_summary="",
                            log="",
                        )
                    ]
                tool_run_kwargs = self.tool_run_logging_kwargs()
                try:
                    # params = load_dict(raw_inputs)
                    validate_inputs(tool.parameters, tool_action.tool_input)  # type: ignore
                except Exception as e:
                    error_observation = await DummyToolWithMessage().arun(
                        f'{{"error": "InvalidRequestException: {e}"}}',
                        **tool_run_kwargs,  # type: ignore
                    )
                    error = SimulatedObservation(
                        log="", thought_summary="", observation=error_observation
                    )
                    assert isinstance(error, SimulatedObservation)
                    return [error]
                observation = await agenerate_simulated_observation(
                    model_name=self.model_name,
                    history=history,
                    current_tool=tool_action.tool,
                    current_tool_description=tool.description,
                    toolkit_descriptions=self._get_current_toolkit_descriptions(
                        tool_action.tool
                    ),
                    temperature=temperature,
                )
                # Validate and correct the observation
                is_valid, corrected_observation_string = await validate_observation(
                    observation, self.tool_parser[tool.name], tool
                )
                if not is_valid:
                    observation.observation = corrected_observation_string
                return [observation]
        return [SimulatedObservation(observation="", thought_summary="", log="")]
