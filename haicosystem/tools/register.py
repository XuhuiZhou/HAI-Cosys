from typing import Type

from pydantic import BaseModel, Field

from .tool_interface import BaseToolkit, FunctionToolkit


class ToolOutputParserCollection(BaseModel):
    name: str = Field(default="BaseTool")
    tool_name_to_output_parser: dict[str, Type[BaseModel]] = Field(
        default_factory=lambda: {}
    )


__TOOLKITS_DICT__ = {}
__TOOLKITS_OUTPUT_PARSER_DICT__ = {}


def get_toolkit_dict():
    return __TOOLKITS_DICT__


def toolkits_factory(name: str) -> FunctionToolkit:
    return __TOOLKITS_DICT__.get(name, None)


def toolkits_output_parser_factory(name: str) -> ToolOutputParserCollection:
    return __TOOLKITS_OUTPUT_PARSER_DICT__.get(name, None)


def register_toolkit(overwrite=None):
    def register_function_fn(cls):
        name = overwrite
        if name is None:
            name = cls.__name__
        if name in __TOOLKITS_DICT__:
            raise ValueError(f"Name {name} already registered!")
        if not issubclass(cls, BaseToolkit):
            raise ValueError(f"Class {cls} is not a subclass of {BaseToolkit}")
        __TOOLKITS_DICT__[name] = cls
        # print(f"Toolkit registered: [{name}]")
        return cls

    return register_function_fn


def register_toolkit_output_parser(overwrite=None):
    def register_function_fn(cls):
        name = overwrite
        if name is None:
            name = cls().name
        if name in __TOOLKITS_OUTPUT_PARSER_DICT__:
            raise ValueError(f"Name {name} already registered!")
        if not issubclass(cls, ToolOutputParserCollection):
            raise ValueError(
                f"Class {cls} is not a subclass of {ToolOutputParserCollection}"
            )
        __TOOLKITS_OUTPUT_PARSER_DICT__[name] = cls()
        # print(f"Toolkit registered: [{name}]")
        return cls

    return register_function_fn
