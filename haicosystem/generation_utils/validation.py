from typing import Type

from beartype import beartype
from langchain.output_parsers import PydanticOutputParser
from langchain.tools.base import BaseTool
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel
from sotopia.generation_utils import agenerate

from haicosystem.generation_utils import SIMULATOR_CRITIQUE
from haicosystem.protocols import SimulatedObservation


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
