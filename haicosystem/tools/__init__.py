# from .register import toolkits_factory, toolkits_output_parser_factory
from .real_tools import RealPythonInterpreterExecute
from .tool_interface import BaseTool, Err, Ok, Result, ToolRegistry
from .virtual_tools import VenmoSendMoney

# from .tool_parser import *  # noqa: F403
# from .virtual_tools import *  # noqa: F403

__all__ = [
    "RealPythonInterpreterExecute",
    "VenmoSendMoney",
    "BaseTool",
    "ToolRegistry",
    "Result",
    "Ok",
    "Err",
]

# def get_toolkits_by_names(names: list[str]) -> list[FunctionToolkit]:
#     toolkits = []
#     for name in names:
#         toolkit = toolkits_factory(name)
#         if toolkit:
#             toolkits.append(toolkit())
#         else:
#             print(f"Warning: toolkit {name} not found")
#     return toolkits


# def get_toolkit_output_parser_by_names(names: list[str]) -> dict[str, Type[BaseModel]]:
#     parsers = {}
#     for name in names:
#         parser = toolkits_output_parser_factory(name)
#         if parser:
#             parsers.update(parser.tool_name_to_output_parser)
#         else:
#             print(f"Warning: toolkit output parser {name} not found")
#     return parsers


# def get_tool_class_by_name(toolkits: list[FunctionToolkit], name: str) -> BaseTool:
#     for toolkit in toolkits:
#         try:
#             return toolkit[name]
#         except ValueError:
#             pass
#     raise ValueError(f"Tool {name} does not exist in these toolkits")
