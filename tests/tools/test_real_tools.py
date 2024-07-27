from haicosystem.tools import ToolRegistry

def test_python_tool() -> None:
    python_executor = ToolRegistry.registry["python_interpreter"]["real_python_interpreter_execute"]

    result = python_executor.call({"script": "print('Hello, World!')"})

    assert result.result.status == "ok"
    assert result.result.output == "Hello, World!\n"

    result = python_executor.call('{\"script\": \"print(\'Hello, World!\')\"}')

    assert result.result.status == "ok"
    assert result.result.output == "Hello, World!\n"

    from haicosystem.tools.real_tools import PythonInterpreterInput

    result = python_executor.call(PythonInterpreterInput(script="print('Hello, World!')"))

    assert result.result.status == "ok"
    assert result.result.output == "Hello, World!\n"