from fastapi import FastAPI
from pydantic import BaseModel


app = FastAPI(title="HyperAgents Mock MCP Server", version="0.1.0")


class ToolCallRequest(BaseModel):
    name: str
    input: dict = {}


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "server": "mock-mcp"}


@app.get("/tools")
def list_tools() -> dict:
    return {
        "tools": [
            {
                "name": "ping",
                "description": "Return pong",
                "input_schema": {
                    "type": "object",
                    "properties": {"text": {"type": "string"}},
                },
            },
            {
                "name": "echo",
                "description": "Echo input payload",
                "input_schema": {"type": "object"},
            },
        ]
    }


@app.post("/tools/call")
def call_tool(payload: ToolCallRequest) -> dict:
    if payload.name == "ping":
        return {"ok": True, "name": "ping", "result": "pong", "echo": payload.input.get("text", "")}
    if payload.name == "echo":
        return {"ok": True, "name": "echo", "result": payload.input}
    return {"ok": False, "error": f"Unknown tool: {payload.name}"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8099)
