"""Tool interface"""

import logging
from types import UnionType
from typing import Any, Callable, Generic, Literal, TypeVar, cast

from pydantic import BaseModel, ValidationError
from pydantic.generics import GenericModel

logger = logging.getLogger(__name__)

T_input = TypeVar("T_input", bound=BaseModel)
T_output = TypeVar("T_output")
T_exception = TypeVar("T_exception", bound=Exception | None)


class Ok(GenericModel, Generic[T_output]):
    status: Literal["ok"] = "ok"
    output: T_output


class Err(GenericModel, Generic[T_exception]):
    status: Literal["err"] = "err"
    error: T_exception

    class Config:
        arbitrary_types_allowed = True


class Result(GenericModel, Generic[T_output, T_exception]):
    result: Ok[T_output] | Err[T_exception]


class BaseTool(Generic[T_input, T_output, T_exception]):
    name: str = ""
    toolkit: str = ""
    summary: str = ""
    description: str = ""
    input_type: type[T_input]
    output_type: type[T_output]
    exception_type: type[T_exception] | UnionType
    ok_type: type[Ok[T_output]] = Ok
    err_type: type[Err[T_exception]] = Err

    @classmethod
    def run(cls, input: T_input) -> T_output:
        raise NotImplementedError

    @classmethod
    def call(
        cls, input: T_input | str | bytes | dict[str, Any]
    ) -> Result[T_output, T_exception]:
        if not isinstance(input, cls.input_type):
            try:
                if isinstance(input, dict):
                    input = cls.input_type.parse_obj(input)
                else:
                    input = cls.input_type.parse_raw(input)
            except ValidationError as e:
                logger.error(f"Error parsing input: {str(input)}")
                raise e
        input = cast(T_input, input)
        try:
            return Result(result=Ok(output=cls.run(input)))
        except Exception as e:
            if isinstance(e, cls.exception_type):
                return Result(result=Err(error=e))
            else:
                raise e

    @classmethod
    async def acall(self, _: T_input) -> Result[T_output, T_exception]:
        raise NotImplementedError


class ToolRegistry:
    registry: dict[str, dict[str, type[BaseTool[BaseModel, Any, Exception]]]] = {}

    @classmethod
    def register(
        cls,
        *,
        tool_name: str,
        toolkit_name: str,
        input_type: type[T_input],
        output_type: type[T_output],
        exception_type: type[Exception] | UnionType | None,
        tool_summary: str = "",
        tool_description: str = "",
    ) -> Callable[
        [type[BaseTool[T_input, T_output, T_exception]]], type[BaseTool[T_input, T_output, T_exception]]
    ]:
        def register_tool(
            tool: type[BaseTool[T_input, T_output, T_exception]],
        ) -> type[BaseTool[T_input, T_output, T_exception]]:
            if toolkit_name not in cls.registry:
                cls.registry[toolkit_name] = {}
            if tool_name in cls.registry[toolkit_name]:
                logger.warning(
                    f"Tool {tool_name} already registered in toolkit {toolkit_name}. Overwriting."
                )
            # Note on ignoring the static type check:
            # We ignore the static type checking of the tools
            # because the tools' call method is dynamically type checked
            cls.registry[toolkit_name][tool_name] = tool # type: ignore[assignment]
            tool.name = tool_name
            tool.toolkit = toolkit_name
            tool.summary = tool_summary
            tool.description = tool_description
            tool.input_type = input_type
            tool.output_type = output_type
            tool.ok_type = Ok[output_type] # type: ignore[valid-type]
            if exception_type is None:
                tool.exception_type = None # type: ignore[assignment]
            elif isinstance(exception_type, UnionType):
                if all(issubclass(t, Exception) for t in exception_type.__args__):
                    tool.exception_type = exception_type
                else:
                    raise ValueError("Exception type must be a Union of Exceptions.")
            elif issubclass(exception_type, Exception):
                tool.exception_type = exception_type # type: ignore[assignment]
            else:
                raise ValueError(f"Invalid exception type: {exception_type}")
            tool.err_type = Err[exception_type] # type: ignore[valid-type]
            return tool

        return register_tool
