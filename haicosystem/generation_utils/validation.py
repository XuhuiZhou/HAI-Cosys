from typing import Type

from beartype import beartype
from langchain.output_parsers import PydanticOutputParser
from langchain.tools.base import BaseTool
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel
from sotopia.generation_utils import agenerate

from haicosystem.generation_utils import SIMULATOR_CRITIQUE
from haicosystem.protocols import (
    HaiAgentAction,
    LangchainAgentAction,
    SimulatedObservation,
)


@beartype
async def validate_observation(
    obs: SimulatedObservation,
    tool_output_parser: Type[BaseModel] | None,
    tool: BaseTool | None = None,
    model_name: str = "gpt-4o",
    temperature: float = 0.7,
) -> tuple[bool, str]:
    """
    Validate the observation against the tool's output parser.
    """
    if not tool_output_parser and not tool:
        raise ValueError("Either tool_output_parser or tool must be provided.")

    output_parser = JsonOutputParser()
    try:
        output_parser.invoke(obs.observation)
        if '"error":' in obs.observation:
            return True, obs.observation
        if tool_output_parser:
            output_parser = PydanticOutputParser(pydantic_object=tool_output_parser)
            output_parser.invoke(obs.observation)
        return True, obs.observation
    except Exception:
        if tool_output_parser:
            output_parser = PydanticOutputParser(pydantic_object=tool_output_parser)
        try:
            correted_observation = await agenerate(
                model_name=model_name,
                template=SIMULATOR_CRITIQUE,
                input_values=dict(
                    log=obs.log,
                    thought_summary=obs.thought_summary,
                    observation=obs.observation,
                ),
                output_parser=output_parser,
                temperature=temperature,
            )
            assert isinstance(correted_observation, BaseModel)
            return False, correted_observation.json()
        except Exception as e:
            return False, f"{{'error': {e}}}"


@beartype
async def validate_agentAction(
    action: HaiAgentAction,
    tool_output_parser: Type[LangchainAgentAction],
    model_name: str = "gpt-4o",
    temperature: float = 0.7,
) -> tuple[bool, str]:
    """
    Validate the agent's action can be parse by into LangchainAgentAction
    """
    output_parser = PydanticOutputParser(pydantic_object=tool_output_parser)  # type: ignore
    try:
        output_parser.invoke(action.argument)
    except Exception as e:
        print(f"Error: {e}")
        try:
            corrected_action = await agenerate(
                model_name=model_name,
                template=SIMULATOR_CRITIQUE,
                input_values=dict(
                    action_type=action.action_type,
                    action_argument=action.argument,
                ),
                output_parser=output_parser,
                temperature=temperature,
            )
            assert isinstance(corrected_action, BaseModel)
            return False, corrected_action.json()
        except Exception as e:
            return False, LangchainAgentAction(
                tool="none", tool_input={}, log=f"{{'error': {e}}}"
            ).to_json_str()
    return True, action.argument
