from pydantic import BaseModel
from typing import Type
from beartype import beartype
from sotopia.generation_utils import agenerate
from langchain.output_parsers import PydanticOutputParser
from haicosystem.generation_utils import SIMULATOR_CRITIQUE
from haicosystem.protocols import SimulatedObservation


@beartype
async def validate_observation(
    obs: SimulatedObservation,
    tool_output_parser: Type[BaseModel],
    model_name: str = "gpt-4o",
    temperature: float = 0.7,
) -> tuple[bool, str]:
    """
    Validate the observation against the tool's output parser.
    """
    output_parser = PydanticOutputParser(pydantic_object=tool_output_parser)  # type: ignore
    if '"error":' in obs.observation:
        return True, obs.observation
    try:
        output_parser.invoke(obs.observation)
    except Exception as e:
        print(f"Error: {e}")
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
    return True, ""
