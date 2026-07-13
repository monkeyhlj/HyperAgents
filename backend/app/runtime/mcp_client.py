"""MCP client supporting streamable_http and SSE (2024-11-05) transports."""
from __future__ import annotations

import json
import queue
import re
import threading
import uuid
from typing import Any
from urllib.parse import urlparse

import httpx


# ---------------------------------------------------------------------------
# Name helpers
# ---------------------------------------------------------------------------

def _sanitize_name(name: str) -> str:
    """Strip chars that are invalid in OpenAI function names; cap at 40."""
    return re.sub(r"[^a-zA-Z0-9_-]", "_", name)[:40]


def make_openai_tool_name(mcp_name: str, tool_name: str) -> str:
    """Build a namespaced OpenAI function name: mcp__{mcp}__{tool}."""
    return f"mcp__{_sanitize_name(mcp_name)}__{_sanitize_name(tool_name)}"


def parse_openai_tool_name(openai_name: str) -> tuple[str, str] | None:
    """Parse 'mcp__{mcp}__{tool}' → (mcp_name, tool_name). Returns None if not parseable."""
    if not openai_name.startswith("mcp__"):
        return None
    rest = openai_name[5:]
    idx = rest.find("__")
    if idx < 0:
        return None
    return rest[:idx], rest[idx + 2:]


def mcp_tool_to_openai(mcp_name: str, tool: dict) -> dict:
    """Convert an MCP tool definition to OpenAI function-call format."""
    tool_name = str(tool.get("name") or "")
    openai_name = make_openai_tool_name(mcp_name, tool_name)
    schema = dict(tool.get("inputSchema") or {"type": "object", "properties": {}})
    schema.pop("$schema", None)
    return {
        "type": "function",
        "function": {
            "name": openai_name,
            "description": str(tool.get("description") or ""),
            "parameters": schema,
        },
    }


def extract_tool_result_text(result: Any) -> str:
    """Extract a plain-text string from an MCP tool result."""
    if isinstance(result, dict):
        content = result.get("content")
        if isinstance(content, list):
            parts = [
                str(item.get("text") or "")
                for item in content
                if isinstance(item, dict) and item.get("type") == "text"
            ]
            return "\n".join(parts) if parts else json.dumps(result)
        if "text" in result:
            return str(result["text"])
    return json.dumps(result) if result is not None else ""


# ---------------------------------------------------------------------------
# streamable_http transport
# ---------------------------------------------------------------------------

class MCPStreamableHttpClient:
    """Client for the REST-style streamable_http MCP transport."""

    def __init__(self, mcp_spec: dict) -> None:
        self.endpoint_url = str(mcp_spec.get("endpoint_url") or "").strip()
        self.headers = dict(mcp_spec.get("headers") or {})
        self.timeout = float(mcp_spec.get("timeout_seconds") or 8)

    def list_tools(self) -> list[dict]:
        base = self.endpoint_url.rstrip("/")
        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(f"{base}/tools", headers=self.headers)
            response.raise_for_status()
            raw = response.json()
        if isinstance(raw, dict):
            return raw.get("tools") or []
        return raw if isinstance(raw, list) else []

    def call_tool(self, tool_name: str, arguments: dict) -> Any:
        base = self.endpoint_url.rstrip("/")
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                f"{base}/tools/call",
                json={"name": tool_name, "input": arguments},
                headers=self.headers,
            )
            response.raise_for_status()
            ct = (response.headers.get("content-type") or "").lower()
            return response.json() if "application/json" in ct else {"ok": True, "text": response.text}


# ---------------------------------------------------------------------------
# SSE transport (MCP 2024-11-05 spec)
# ---------------------------------------------------------------------------

class MCPSSEClient:
    """Client for MCP SSE transport.

    Flow:
      1. GET to SSE endpoint → server sends an ``endpoint`` event whose data is
         the message URL (absolute or relative).
      2. POST ``initialize`` JSON-RPC request to that URL.
      3. On ``initialize`` response → POST ``notifications/initialized``, then
         POST the actual request.
      4. Wait for the response event whose ``id`` matches the request.
    """

    def __init__(self, mcp_spec: dict) -> None:
        self.endpoint_url = str(mcp_spec.get("endpoint_url") or "").strip()
        self.headers = dict(mcp_spec.get("headers") or {})
        self.timeout = float(mcp_spec.get("timeout_seconds") or 8)

    def _execute(self, method: str, params: dict) -> Any:
        responses: dict = {}
        done = threading.Event()
        msg_endpoint: list[str | None] = [None]
        init_id = str(uuid.uuid4())
        req_id = str(uuid.uuid4())

        endpoint_url = self.endpoint_url
        headers = self.headers
        timeout = self.timeout

        def _post(url: str, payload: dict) -> None:
            with httpx.Client(timeout=timeout) as pc:
                pc.post(url, json=payload, headers=headers)

        def _on_event(event: dict) -> None:
            evt_type = event.get("event", "message")
            data = event.get("data", "")

            if evt_type == "endpoint":
                url = data.strip()
                if not url.startswith("http"):
                    parsed = urlparse(endpoint_url)
                    url = f"{parsed.scheme}://{parsed.netloc}{url}"
                msg_endpoint[0] = url
                try:
                    _post(url, {
                        "jsonrpc": "2.0",
                        "id": init_id,
                        "method": "initialize",
                        "params": {
                            "protocolVersion": "2024-11-05",
                            "capabilities": {},
                            "clientInfo": {"name": "hyperagents", "version": "0.1.0"},
                        },
                    })
                except Exception as exc:
                    responses["__error"] = str(exc)
                    done.set()

            elif evt_type == "message" and data:
                try:
                    msg = json.loads(data)
                    mid = msg.get("id")
                    if mid == init_id:
                        url = msg_endpoint[0]
                        if not url:
                            responses["__error"] = "No message endpoint after initialize"
                            done.set()
                            return
                        try:
                            _post(url, {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})
                            _post(url, {"jsonrpc": "2.0", "id": req_id, "method": method, "params": params})
                        except Exception as exc:
                            responses["__error"] = str(exc)
                            done.set()
                    elif mid == req_id:
                        responses["msg"] = msg
                        done.set()
                except json.JSONDecodeError:
                    pass

        def _read_stream() -> None:
            try:
                with httpx.Client(timeout=timeout + 60) as client:
                    with client.stream("GET", endpoint_url, headers=headers) as response:
                        evt: dict = {}
                        for line in response.iter_lines():
                            if done.is_set():
                                break
                            line = line.strip()
                            if line.startswith("event:"):
                                evt["event"] = line[6:].strip()
                            elif line.startswith("data:"):
                                evt["data"] = line[5:].strip()
                            elif line == "":
                                if evt:
                                    _on_event(evt)
                                evt = {}
            except Exception as exc:
                if not done.is_set():
                    responses["__error"] = str(exc)
                    done.set()

        threading.Thread(target=_read_stream, daemon=True).start()
        done.wait(timeout=timeout + 30)

        if "__error" in responses:
            raise RuntimeError(f"MCP SSE error: {responses['__error']}")
        if not done.is_set():
            raise RuntimeError(f"MCP SSE timeout waiting for: {method}")

        msg = responses.get("msg", {})
        if "error" in msg:
            raise RuntimeError(f"MCP error response: {msg['error']}")
        return msg.get("result")

    def list_tools(self) -> list[dict]:
        result = self._execute("tools/list", {})
        return (result or {}).get("tools") or []

    def call_tool(self, tool_name: str, arguments: dict) -> Any:
        return self._execute("tools/call", {"name": tool_name, "arguments": arguments})


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def get_mcp_client(mcp_spec: dict) -> MCPStreamableHttpClient | MCPSSEClient:
    transport = str(mcp_spec.get("transport") or "streamable_http").strip().lower()
    if transport == "sse":
        return MCPSSEClient(mcp_spec)
    return MCPStreamableHttpClient(mcp_spec)
