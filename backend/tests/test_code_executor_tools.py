from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import threading

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
    assert '"result": "pong"' in result["text"]
    assert '"tool": "testping"' in result["text"]
    assert result["used_tools"] == ["testping"]

    config_result = code_runtime_executor.run(
        "show config",
        custom_code=custom_code,
        context={"config": {"tool_ids": ["tool-1"]}},
        tools=tools,
    )
    assert '"tool_ids": ["tool-1"]' in config_result["text"]
    assert '"tools": ["testping"]' in config_result["text"]
    assert config_result["used_tools"] == []


def test_code_executor_can_call_associated_mcp() -> None:
    class _MCPHandler(BaseHTTPRequestHandler):
        def do_POST(self):  # noqa: N802
            if self.path != "/tools/call":
                self.send_response(404)
                self.end_headers()
                return

            body = self.rfile.read(int(self.headers.get("Content-Length") or 0))
            payload = json.loads(body.decode("utf-8") or "{}")
            response = {
                "ok": True,
                "name": payload.get("name"),
                "echo": payload.get("input") or {},
            }
            encoded = json.dumps(response).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        def log_message(self, format, *args):  # noqa: A003
            return

    server = HTTPServer(("127.0.0.1", 0), _MCPHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        custom_code = """
def run(input_text, context):
    if input_text == "ping":
        return call_mcp("testmcp", "ping", {"text": input_text})
    return {"echo": input_text}
"""

        endpoint = f"http://127.0.0.1:{server.server_port}"
        result = code_runtime_executor.run(
            "ping",
            custom_code=custom_code,
            context={"config": {"mcp_ids": ["mcp-1"]}},
            tools=[],
            mcps=[
                {
                    "id": "mcp-1",
                    "name": "testmcp",
                    "transport": "streamable_http",
                    "endpoint_url": endpoint,
                    "timeout_seconds": 3,
                }
            ],
        )

        assert '"name": "ping"' in result["text"]
        assert result["used_mcps"] == [{"mcp": "testmcp", "tool": "ping"}]
    finally:
        server.shutdown()
        server.server_close()