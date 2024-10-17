from typing import Callable, Dict, Optional, Type

from pydantic import BaseModel, Field

from .tool_interface import BaseToolkit, FunctionToolkit


class ToolOutputParserCollection(BaseModel):
    name: str = Field(default="BaseTool")
    tool_name_to_output_parser: dict[str, Type[BaseModel]] = Field(
        default_factory=lambda: {}
    )


__TOOLKITS_DICT__: Dict[str, FunctionToolkit] = {}
__TOOLKITS_OUTPUT_PARSER_DICT__: Dict[str, ToolOutputParserCollection] = {}


def get_toolkit_dict() -> Dict[str, FunctionToolkit]:
    return __TOOLKITS_DICT__


def toolkits_factory(name: str) -> Optional[FunctionToolkit]:
    return __TOOLKITS_DICT__.get(name, None)


def toolkits_output_parser_factory(name: str) -> Optional[ToolOutputParserCollection]:
    return __TOOLKITS_OUTPUT_PARSER_DICT__.get(name, None)


def register_toolkit(
    overwrite: Optional[str] = None,
) -> Callable[[Type[FunctionToolkit]], Type[FunctionToolkit]]:
    def register_function_fn(cls: Type[FunctionToolkit]) -> Type[FunctionToolkit]:
        name = overwrite
        if name is None:
            name = cls.__name__
        if name in __TOOLKITS_DICT__:
            raise ValueError(f"Name {name} already registered!")
        if not issubclass(cls, BaseToolkit):
            raise ValueError(f"Class {cls} is not a subclass of {BaseToolkit}")
        __TOOLKITS_DICT__[name] = cls  # type: ignore
        # print(f"Toolkit registered: [{name}]")
        return cls

    return register_function_fn


def register_toolkit_output_parser(
    overwrite: Optional[str] = None,
) -> Callable[[Type[ToolOutputParserCollection]], Type[ToolOutputParserCollection]]:
    def register_function_fn(
        cls: Type[ToolOutputParserCollection],
    ) -> Type[ToolOutputParserCollection]:
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
