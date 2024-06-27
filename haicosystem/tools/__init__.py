# from .real_tools import *
from .register import toolkits_factory
from .tool_interface import FunctionToolkit
from .virtual_tools import *  # noqa: F403
from langchain.tools.base import BaseTool


def get_toolkits_by_names(names: list[str]) -> list[FunctionToolkit]:
    toolkits = []
    for name in names:
        toolkit = toolkits_factory(name)
        if toolkit:
            toolkits.append(toolkit())
        else:
            print(f"Warning: toolkit {name} not found")
    return toolkits


def get_tool_class_by_name(toolkits: list[FunctionToolkit], name: str) -> BaseTool:
    for toolkit in toolkits:
        try:
            return toolkit[name]
        except ValueError:
            pass
    raise ValueError(f"Tool {name} does not exist in these toolkits")
