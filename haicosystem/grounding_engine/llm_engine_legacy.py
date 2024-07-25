import json
import logging
import re
from typing import Any, Optional, Sequence

from beartype import beartype
from langchain.callbacks.manager import (
    CallbackManager,
)
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain.chains import LLMChain
from langchain.prompts.base import BasePromptTemplate
from langchain.prompts.chat import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
)
from langchain.prompts.prompt import PromptTemplate
from langchain.schema import (
    AIMessage,
    HumanMessage,
    SystemMessage,
)
from langchain.tools.base import BaseTool, StructuredTool
from langchain_core.utils.input import get_color_mapping
from langchain_openai import ChatOpenAI
from pydantic import BaseModel
from sotopia.envs.evaluators import Evaluator
from sotopia.messages import AgentAction, Message

from haicosystem.envs.utils import format_tool_prompt
from haicosystem.protocols.messages import LangchainAgentAction, SimulatedObservation
from haicosystem.tools import get_toolkits_by_names
from haicosystem.tools.tool_interface import BaseToolkit
from haicosystem.tools.utils import validate_outputs

from ..generation_utils.prompts import (
    SIMULATOR_CRITIQUE,
    SIMULATOR_CRITIQUE_REPEAT,
    SIMULATOR_PROMPT,
    SIMULATOR_SYSTEM_INFO,
)
from .tool import arun_with_input_validation

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

    def create_simulator_prompt(
        self, use_chat_format: Optional[bool] = False
    ) -> BasePromptTemplate:
        """Create a the prompt for the simulator LLM."""
        if use_chat_format:
            simulator_system_message = SystemMessage(content=self.sim_system_info)
            simulator_instruction_message = HumanMessagePromptTemplate.from_template(
                template=self.sim_prompt_instruction
            )
            messages = [
                simulator_system_message,
                simulator_instruction_message,
            ]
            return ChatPromptTemplate.from_messages(messages=messages)
        else:
            template = "\n\n".join([self.sim_system_info, self.sim_prompt_instruction])
            input_variables = self._input_keys + ["simulator_scratchpad"]
            return PromptTemplate(template=template, input_variables=input_variables)

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
        self.toolkits = toolkits
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
        self.simulator_llm = ChatOpenAI(
            model_name=self.model_name,
            temperature=0.0,
            request_timeout=300,
            streaming=True,
            callbacks=[StreamingStdOutCallbackHandler()],
        )
        simulator_prompt = self.create_simulator_prompt(use_chat_format=True)
        self.llm_simulator_chain = LLMChain(
            llm=self.simulator_llm,
            prompt=simulator_prompt,
            callback_manager=None,
        )
        return tool_prompt

    @property
    def llm_simulator_tool(self) -> BaseTool:
        result = StructuredTool.from_function(
            func=lambda callbacks, **kwargs: self._get_simulated_observation(
                callbacks, **kwargs
            ),
            name="llm_simulator",
            description="Simulate the execution of a tool with a language model",
            args_schema=SimulatorInputModel,
        )
        return result

    def _get_current_toolkit_descriptions(self, tool_name: str) -> str:
        # NOTE: assume only one toolkit has the tool with tool_name
        for toolkit in self.toolkits:
            for tool in toolkit.tools:
                if tool.name == tool_name:
                    return toolkit.create_description(detail_level="low")
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

    def _extract_observation_and_thought(
        self, llm_output: str
    ) -> tuple[str, str] | None:
        """Parse out the observation from the LLM output."""
        # \s matches against tab/newline/whitespace
        regex = rf"{self.thought_summary_prefix}\s*([\s\S]*?){self.observation_prefix}\s*([\s\S]*)"
        match = re.search(regex, llm_output, re.DOTALL)
        if not match:
            return None
        thought_summary = match.group(1).strip()
        observation = match.group(2).strip()
        return observation, thought_summary

    def _get_simulated_observation(
        self, callback_manager: CallbackManager, **full_inputs: Any
    ) -> SimulatedObservation:
        streaming_output = self.llm_simulator_chain.llm.streaming
        if streaming_output:
            print("\n" + self.generatetion_prefix)
            # for handler in callback_manager.handlers:
            #     getattr(handler, "on_text")(
            #         "\n" + self.generatetion_prefix, verbose=self.verbose
            #     )
        full_output = self.llm_simulator_chain.predict(
            **full_inputs, stop=self.stop_seqs
        )
        parsed_output = self._extract_observation_and_thought(full_output)
        while parsed_output is None:
            full_inputs["simulator_scratchpad"] += full_output
            output = self.llm_simulator_chain.predict(
                **full_inputs, stop=self.stop_seqs
            )
            full_output += output
            parsed_output = self._extract_observation_and_thought(full_output)

        log_output = self.generatetion_prefix + full_output
        # remove all the text after self.observation_prefix
        log_output = log_output.split(self.observation_prefix)[0].strip()
        log_output = "\n" + log_output

        if not streaming_output and not log_output.isspace():
            for handler in callback_manager.handlers:
                getattr(handler, "on_tool_end")(log_output, verbose=self.verbose)

        sim_observation = SimulatedObservation(
            observation=parsed_output[0],
            thought_summary=parsed_output[1],
            log=full_output,
        )
        observation = self._critique_simulated_observation(
            callback_manager, sim_observation, full_inputs
        )
        return observation

    def _create_critiquer_prompt(
        self,
        simulator_inputs: dict[str, str],
        sim_observation: SimulatedObservation,
        critique_outputs: list[dict[str, str]],
    ) -> list:
        """Create a the prompt for the critiquer LLM."""
        simulator_prompt_temp = self.llm_simulator_chain.prompt
        use_chat_format = isinstance(simulator_prompt_temp, ChatPromptTemplate)
        simulator_prompt = simulator_prompt_temp.format_prompt(**simulator_inputs)

        critique_prompt_messages = []

        if use_chat_format:
            # add simulator prompt
            critique_prompt_messages += simulator_prompt.messages
        else:
            # add simulator prompt
            critique_prompt_messages.append(HumanMessage(content=simulator_prompt))

        # add simulator output
        simulator_output = sim_observation.log
        critique_prompt_messages.append(AIMessage(content=simulator_output))

        # The last dict in critique_outputs only contains the validation results
        for idx, crit_dict in enumerate(critique_outputs):
            prompt = self.critique_prompt if idx == 0 else self.critique_prompt_repeat
            prompt = f"{crit_dict['validation']}\n{prompt}"
            critique_prompt_messages.append(HumanMessage(content=prompt))
            if "critique" in crit_dict:
                # add critique output
                critique_prompt_messages.append(
                    AIMessage(content=crit_dict["critique"])
                )

        if not use_chat_format:
            critique_prompt_messages = "\n\n".join(
                [t.content for t in critique_prompt_messages]
            )

        return critique_prompt_messages

    @property
    def critique_prefix(self) -> str:
        return "Critique #{step}:"

    @property
    def revised_thought_summary_prefix(self) -> str:
        return "Revised Simulator Log Summary #{step}:"

    @property
    def revised_observation_prefix(self) -> str:
        return "Revised Observation #{step}:"

    def _extract_revised_observation_and_thought(
        self, critique_llm_output: str, current_step: int
    ) -> Optional[list[str]]:
        """Parse out the observation from the critiqued LLM output."""
        thought_summary_prefix = self.revised_thought_summary_prefix.format(
            step=current_step
        )
        observation_prefix = self.revised_observation_prefix.format(step=current_step)
        # \s matches against tab/newline/whitespace
        regex = rf"{thought_summary_prefix}(.*?)[\n]*{observation_prefix}[\s]*(.*)"
        match = re.search(regex, critique_llm_output, re.DOTALL)

        if not match:
            return None
        revised_thought_summary = match.group(1).strip()
        revised_observation = match.group(2).strip()
        return revised_observation, revised_thought_summary

    def _critique_simulated_observation(
        self,
        callback_manager: CallbackManager,
        sim_observation: SimulatedObservation,
        simulator_inputs: dict[str, Any],
    ) -> SimulatedObservation:
        streaming_output = self.simulator_llm.streaming
        tool_name = simulator_inputs["current_tool"]
        tool_mapping = dict(zip(self.tool_names, self.tools))
        tool = tool_mapping[tool_name]

        def get_validation_result(obs):
            msg = "The format of the output matches the specification of the tool."
            exception = None
            try:
                outputs = json.loads(obs)
            except json.decoder.JSONDecodeError as e:
                msg = "The output is not a valid JSON object."
                exception = e
            if exception is None:
                try:
                    validate_outputs(tool.returns, outputs)
                except ValueError as e:
                    msg = "The format of the output does not match the specification of the tool."
                    exception = e
            return f"Format Validation: {msg}", exception

        current_obs = sim_observation.observation
        critique_outputs = []
        sep = "\n\n"
        revised_output = None

        if self.max_allowed_steps <= 0:
            return sim_observation

        for step in range(self.max_allowed_steps):
            step_idx = step + 1

            validation_msg, exception = get_validation_result(current_obs)
            if exception is not None:
                validation_msg += f" {exception}"
            elif step_idx > self.num_critique_steps:
                # if we have enough number of critique steps and the last output obs is valid
                break

            critique_outputs.append({"validation": validation_msg})
            critiquer_prompt = self._create_critiquer_prompt(
                simulator_inputs,
                sim_observation,
                critique_outputs,
            )
            if streaming_output:
                print(f"\n\n{validation_msg}\n\n")
                # for handler in callback_manager.handlers:
                #     getattr(handler, "on_text")("\n\n", verbose=self.verbose)
            print("---------------------Hey I am revising---------------------")
            crit_out = self.simulator_llm.generate(
                [critiquer_prompt],
                stop=[
                    self.critique_prefix.format(step=step_idx + 1),
                    "Action:",
                    "Action Input:",
                ],
            )
            assert len(crit_out.generations) == 1
            # todo: this is for chat model
            crit_out = crit_out.generations[0][0].text
            # critique_outputs.append(crit_out)
            critique_outputs[-1]["critique"] = crit_out
            revised_output = self._extract_revised_observation_and_thought(
                crit_out, current_step=step_idx
            )
            current_obs = revised_output[0] if revised_output else current_obs

            log_output = sep + validation_msg + "\n" + crit_out
            if not streaming_output and not log_output.isspace():
                for handler in callback_manager.handlers:
                    getattr(handler, "on_tool_end")(log_output, verbose=self.verbose)

        # todo: extract sim_observation from sim_observation.log
        if revised_output is None:
            return sim_observation

        # todo: the correctness of logging need to be checked.
        logs = [sim_observation.log]
        for crit_dict in critique_outputs:
            logs.append(crit_dict["validation"] + "\n" + crit_dict["critique"])
        log_output_with_critique = sep.join(logs)

        critiqued_observation = SimulatedObservation(
            observation=revised_output[0],
            thought_summary=revised_output[1],
            log=log_output_with_critique,
        )
        # update log in observation
        return critiqued_observation

    def _construct_simulator_scratchpad(
        self,
        intermediate_steps: list[tuple[LangchainAgentAction, str]],
        include_simulator_log: bool = False,
        include_simulator_thought_summary: bool = True,
        include_simulator_last_step_only: bool = False,
    ):
        """Construct the scratchpad that without outputting the last observation."""

        # this is copied from the agent's _construct_scratchpad
        scratchpad = ""
        for idx, (action, observation) in enumerate(intermediate_steps):
            scratchpad += f"Action: {action.tool}\nAction Input: {action.tool_input}\n"

            if idx == len(intermediate_steps) - 1:
                scratchpad += "\n"
            else:
                if include_simulator_log and (
                    not include_simulator_last_step_only
                    or idx == len(intermediate_steps) - 2
                ):
                    scratchpad += f"\n{self.generatetion_prefix}{observation.log}\n"
                elif include_simulator_thought_summary and (
                    not include_simulator_last_step_only
                    or idx == len(intermediate_steps) - 2
                ):
                    scratchpad += f"\n{self.thought_summary_prefix}{observation.thought_summary}\n{self.observation_prefix}{observation.observation}\n"
                else:
                    scratchpad += (
                        f"\n{self.observation_prefix}{observation.observation}\n"
                    )
                # scratchpad += self.agent.llm_prefix

        # add prefix for generation
        scratchpad += self.generatetion_prefix
        # scratchpad = self.agent.llm_prefix + scratchpad
        return scratchpad

    def parse_action(self, action: str) -> LangchainAgentAction:
        json_action = json.loads(action)
        new_action = LangchainAgentAction(**json_action)
        return new_action

    async def __acall__(
        self,
        turn_number: int,
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
                color = self.color_mapping[tool_action.tool]

                empty_observation = ""  # for the current step
                intermediate_steps = []
                simulator_scratchpad = self._construct_simulator_scratchpad(
                    intermediate_steps + [(tool_action, empty_observation)]
                )
                full_inputs = {
                    "simulator_scratchpad": simulator_scratchpad,
                    "current_tool": tool_action.tool,
                    "current_tool_description": tool.description,
                    "toolkit_descriptions": self._get_current_toolkit_descriptions(
                        tool_action.tool
                    ),
                    "interaction_history": history,
                }
                tool_run_kwargs = self.tool_run_logging_kwargs()
                observation = await arun_with_input_validation(
                    self.llm_simulator_tool.arun,
                    full_inputs,
                    tool,
                    tool_action.tool_input,
                    verbose=self.verbose,
                    color=color,
                    **tool_run_kwargs,
                )
                return [observation]
        return [SimulatedObservation(observation="", thought_summary="", log="")]
