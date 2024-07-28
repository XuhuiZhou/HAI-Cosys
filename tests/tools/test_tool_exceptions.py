import pytest
from haicosystem.tools import ToolRegistry, BaseTool
from pydantic import BaseModel

class DivisionInput(BaseModel):
    dividend: int | str
    divisor: int | str

class UncaughtError(Exception):
    pass

@ToolRegistry.register(
    tool_name="division",
    toolkit_name="math",
    input_type=DivisionInput,
    output_type=int,
    exception_type=ZeroDivisionError | ValueError,
)
class Division(BaseTool[DivisionInput, int, ZeroDivisionError | ValueError]):
    @classmethod
    def run(cls, input: DivisionInput) -> int:
        if input.divisor == "uncaught error":
            raise UncaughtError("You got an uncaught error.")
        return int(input.dividend) // int(input.divisor)
    
def test_tool_registry() -> None:
    DivisionExecutor = ToolRegistry.registry["math"]["division"]

    result = DivisionExecutor.call({"dividend": 1, "divisor": 0})

    assert result.result.status == "err"
    assert isinstance(result.result.error, ZeroDivisionError)

    result = DivisionExecutor.call({"dividend": "*", "divisor": "*"})

    assert result.result.status == "err"
    assert isinstance(result.result.error, ValueError)

    with pytest.raises(UncaughtError):
        DivisionExecutor.call({"dividend": 1, "divisor": "uncaught error"})