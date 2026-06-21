from app.runtime.code_executor import code_runtime_executor


def test_code_executor_can_call_associated_tool() -> None:
    custom_code = """
def run(input_text, context):
    if input_text == "ping":
        return call_tool("testping", {"action": "ping", "text": input_text})
    if input_text == "show config":
        return {
            "tool_ids": context.get("config", {}).get("tool_ids", []),
            "tools": list_tools(),
        }
    return {"echo": input_text}
"""

    tool_code = """
def run(input_data, context):
    if input_data.get("action") == "ping":
        return {"ok": True, "result": "pong", "tool": context.get("tool", {}).get("name")}
    return {"ok": True, "echo": input_data}
"""

    tools = [
        {
            "id": "tool-1",
            "name": "testping",
            "runtime": "python",
            "entrypoint": "run",
            "code": tool_code,
        }
    ]

    result = code_runtime_executor.run(
        "ping",
        custom_code=custom_code,
        context={"config": {"tool_ids": ["tool-1"]}},
        tools=tools,
    )
    assert '"result": "pong"' in result
    assert '"tool": "testping"' in result
    assert '"used_tools": ["testping"]' in result

    config_result = code_runtime_executor.run(
        "show config",
        custom_code=custom_code,
        context={"config": {"tool_ids": ["tool-1"]}},
        tools=tools,
    )
    assert '"tool_ids": ["tool-1"]' in config_result
    assert '"tools": ["testping"]' in config_result
    assert '"used_tools"' not in config_result