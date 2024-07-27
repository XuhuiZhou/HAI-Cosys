"""Tool interface"""

import logging
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
    summary: str = ""
    description: str = ""
    input_type: type[T_input]
    output_type: type[T_output]
    exception_type: type[T_exception]

    @classmethod
    def run(cls, input: T_input) -> T_output:
        raise NotImplementedError

    @classmethod
    def call(cls, input: T_input | str | bytes | dict[str, Any]) -> Result[T_output, T_exception]:
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
    registry: dict[str, dict[str, type[BaseTool[Any, Any, Exception]]]] = {}

    @classmethod
    def register(
        cls, tool_name: str, toolkit_name: str
    ) -> Callable[
        [type[BaseTool[Any, Any, Exception]]], type[BaseTool[Any, Any, Exception]]
    ]:
        def register_tool(
            tool: type[BaseTool[Any, Any, Exception]],
        ) -> type[BaseTool[Any, Any, Exception]]:
            if toolkit_name not in cls.registry:
                cls.registry[toolkit_name] = {}
            if tool_name in cls.registry[toolkit_name]:
                logger.warning(
                    f"Tool {tool_name} already registered in toolkit {toolkit_name}. Overwriting."
                )
            cls.registry[toolkit_name][tool_name] = tool
            return tool

        return register_tool
