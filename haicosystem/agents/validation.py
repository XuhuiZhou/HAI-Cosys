from pydantic import BaseModel
from typing import Type
from beartype import beartype
from langchain.output_parsers import PydanticOutputParser
from sotopia.generation_utils.generate import format_bad_output
from sotopia.messages import AgentAction


@beartype
async def validate_agentAction(
    action: AgentAction,
    tool_output_parser: Type[BaseModel],
) -> AgentAction:
    """
    Validate the agent's action can be parse by into LangchainAgentAction
    """
    output_parser = PydanticOutputParser(pydantic_object=tool_output_parser)  # type: ignore
    try:
        output_parser.invoke(action.argument)
    except Exception as e:
        print(f"Error: {e}")
        try:
            reformat_action_argument = format_bad_output(
                action.argument, format_instructions=output_parser.get_format_instructions()
            ) 
            output_parser.invoke(reformat_action_argument)
            action.argument = reformat_action_argument
        except Exception as e:
            pass
    return action