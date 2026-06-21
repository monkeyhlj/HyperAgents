from __future__ import annotations

import ast
import base64
import json
import os
import subprocess
import sys
import tempfile
from typing import Any

from app.core.config import settings


_ALLOWED_BUILTINS: dict[str, Any] = {
    "abs": abs,
    "all": all,
    "any": any,
    "BaseException": BaseException,
    "bool": bool,
    "callable": callable,
    "dict": dict,
    "enumerate": enumerate,
    "Exception": Exception,
    "float": float,
    "isinstance": isinstance,
    "issubclass": issubclass,
    "int": int,
    "KeyError": KeyError,
    "len": len,
    "list": list,
    "max": max,
    "min": min,
    "RuntimeError": RuntimeError,
    "range": range,
    "round": round,
    "set": set,
    "sorted": sorted,
    "str": str,
    "sum": sum,
    "TypeError": TypeError,
    "type": type,
    "tuple": tuple,
    "ValueError": ValueError,
    "zip": zip,
}

_ALLOWED_IMPORT_NAMES = {
    "datetime",
    "httpx",
    "json",
    "math",
    "re",
    "requests",
    "time",
}


_FORBIDDEN_AST_NODES = (
    ast.With,
    ast.AsyncWith,
    ast.Raise,
    ast.Global,
    ast.Nonlocal,
)


_RUNNER_SCRIPT = r"""
import ast
import base64
import datetime
import httpx
import json
import math
import sys
import re
import time

ALLOWED_BUILTINS = {
    "abs": abs,
    "all": all,
    "any": any,
    "BaseException": BaseException,
    "bool": bool,
    "callable": callable,
    "dict": dict,
    "enumerate": enumerate,
    "Exception": Exception,
    "float": float,
    "isinstance": isinstance,
    "issubclass": issubclass,
    "int": int,
    "KeyError": KeyError,
    "len": len,
    "list": list,
    "max": max,
    "min": min,
    "RuntimeError": RuntimeError,
    "range": range,
    "round": round,
    "set": set,
    "sorted": sorted,
    "str": str,
    "sum": sum,
    "TypeError": TypeError,
    "type": type,
    "tuple": tuple,
    "ValueError": ValueError,
    "zip": zip,
}

ALLOWED_IMPORT_NAMES = {
    "datetime",
    "httpx",
    "json",
    "math",
    "re",
    "requests",
    "time",
}

ALLOWED_IMPORT_MODULES = {
    "datetime": datetime,
    "httpx": httpx,
    "json": json,
    "math": math,
    "re": re,
    "requests": httpx,
    "time": time,
}

FORBIDDEN_AST_NODES = (
    ast.With,
    ast.AsyncWith,
    ast.Raise,
    ast.Global,
    ast.Nonlocal,
)


def safe_import(name, globals=None, locals=None, fromlist=(), level=0):
    if level not in (0, None):
        raise ImportError("Relative imports are not allowed")
    module_name = str(name or "").strip()
    base_name = module_name.split(".")[0]
    module = ALLOWED_IMPORT_MODULES.get(base_name)
    if module is None:
        raise ImportError(f"Import not allowed: {module_name}")
    return module


ALLOWED_BUILTINS["__import__"] = safe_import


def normalize_result(value):
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, ensure_ascii=False)
    except TypeError:
        return str(value)


def validate_code(custom_code):
    tree = ast.parse(custom_code)
    for node in ast.walk(tree):
        if isinstance(node, FORBIDDEN_AST_NODES):
            raise RuntimeError(f"Forbidden syntax: {node.__class__.__name__}")
        if isinstance(node, ast.Import):
            for alias in node.names:
                base_name = str(alias.name or "").split(".")[0]
                if base_name not in ALLOWED_IMPORT_NAMES:
                    raise RuntimeError(f"Import not allowed: {alias.name}")
        if isinstance(node, ast.ImportFrom):
            if not node.module:
                raise RuntimeError("Relative imports are not allowed")
            base_name = str(node.module).split(".")[0]
            if base_name not in ALLOWED_IMPORT_NAMES:
                raise RuntimeError(f"Import not allowed: {node.module}")


def execute_tool(tools, tool_name, input_data, context):
    tool_map = {
        str(item.get("name") or "").strip(): item
        for item in (tools or [])
        if str(item.get("name") or "").strip()
    }
    tool_spec = tool_map.get(str(tool_name).strip())
    if not tool_spec:
        raise RuntimeError(f"Tool not found: {tool_name}")

    runtime = str(tool_spec.get("runtime") or "python").strip().lower()
    if runtime != "python":
        raise RuntimeError(f"Unsupported tool runtime: {runtime}")

    entrypoint = str(tool_spec.get("entrypoint") or "run").strip() or "run"
    tool_code = str(tool_spec.get("code") or "")
    if not tool_code.strip():
        raise RuntimeError(f"Tool code is empty: {tool_name}")

    validate_code(tool_code)

    tool_globals = {
        "__builtins__": ALLOWED_BUILTINS,
        "httpx": httpx,
        "json": json,
        "re": re,
        "requests": httpx,
    }
    tool_locals = {}
    exec(compile(tool_code, f"<tool:{tool_name}>", "exec"), tool_globals, tool_locals)

    tool_func = tool_locals.get(entrypoint)
    if not callable(tool_func):
        raise RuntimeError(f"Tool entrypoint not callable: {tool_name}.{entrypoint}")

    tool_context = dict(context or {})
    tool_context["tool"] = {
        "name": tool_spec.get("name"),
        "runtime": runtime,
        "entrypoint": entrypoint,
    }
    safe_input = input_data if isinstance(input_data, dict) else {"value": input_data}
    return tool_func(safe_input, tool_context)


def execute_mcp(mcps, mcp_name, tool_name, input_data):
    mcp_map = {
        str(item.get("name") or "").strip(): item
        for item in (mcps or [])
        if str(item.get("name") or "").strip()
    }
    mcp_spec = mcp_map.get(str(mcp_name).strip())
    if not mcp_spec:
        raise RuntimeError(f"MCP not found: {mcp_name}")

    transport = str(mcp_spec.get("transport") or "streamable_http").strip().lower()
    if transport != "streamable_http":
        raise RuntimeError(f"Unsupported MCP transport: {transport}")

    endpoint_url = str(mcp_spec.get("endpoint_url") or "").strip()
    if not endpoint_url:
        raise RuntimeError(f"MCP endpoint_url is empty: {mcp_name}")

    timeout_seconds = float(mcp_spec.get("timeout_seconds") or 8)
    headers = mcp_spec.get("headers") or {}
    safe_input = input_data if isinstance(input_data, dict) else {"value": input_data}
    payload = {"name": str(tool_name).strip(), "input": safe_input}

    with httpx.Client(timeout=timeout_seconds) as client:
        response = client.post(
            f"{endpoint_url.rstrip('/')}/tools/call",
            json=payload,
            headers=headers,
        )
        response.raise_for_status()
        content_type = (response.headers.get("content-type") or "").lower()
        if "application/json" in content_type:
            return response.json()
        return {"ok": True, "text": response.text}


def main():
    raw = sys.argv[1] if len(sys.argv) > 1 else ""
    payload = json.loads(base64.b64decode(raw.encode("ascii")).decode("utf-8")) if raw else {}
    input_text = payload.get("input_text", "")
    custom_code = payload.get("custom_code", "")
    context = payload.get("context", {})
    tools = payload.get("tools", [])
    mcps = payload.get("mcps", [])
    tool_calls = []
    mcp_calls = []

    if not str(custom_code).strip():
        raise RuntimeError("custom_code is empty")

    validate_code(custom_code)

    def call_tool(tool_name, input_data=None):
        tool_name_text = str(tool_name).strip()
        result = execute_tool(tools, tool_name_text, input_data or {}, context)
        tool_calls.append(tool_name_text)
        return result

    def list_tools():
        return [str(item.get("name") or "") for item in tools if str(item.get("name") or "").strip()]

    def call_mcp(mcp_name, tool_name, input_data=None):
        mcp_name_text = str(mcp_name).strip()
        tool_name_text = str(tool_name).strip()
        result = execute_mcp(mcps, mcp_name_text, tool_name_text, input_data or {})
        mcp_calls.append({"mcp": mcp_name_text, "tool": tool_name_text})
        return result

    def list_mcps():
        return [str(item.get("name") or "") for item in mcps if str(item.get("name") or "").strip()]

    safe_globals = {
        "__builtins__": ALLOWED_BUILTINS,
        "httpx": httpx,
        "json": json,
        "re": re,
        "requests": httpx,
        "call_tool": call_tool,
        "list_tools": list_tools,
        "call_mcp": call_mcp,
        "list_mcps": list_mcps,
    }
    safe_locals = {}

    exec(compile(custom_code, "<agent_custom_code>", "exec"), safe_globals, safe_locals)

    if callable(safe_locals.get("run")):
        result = safe_locals["run"](input_text, context)
    elif callable(safe_locals.get("agent_main")):
        result = safe_locals["agent_main"](input_text, context)
    elif "RESULT" in safe_locals:
        result = safe_locals["RESULT"]
    else:
        raise RuntimeError("custom_code must define run(input_text, context) or agent_main(...) or RESULT")

    used_tools_list = []
    if tool_calls:
        used_tools_list = list(dict.fromkeys(tool_calls))

    used_mcps_list = []
    if mcp_calls:
        seen = set()
        for item in mcp_calls:
            key = (item.get("mcp"), item.get("tool"))
            if key in seen:
                continue
            seen.add(key)
            used_mcps_list.append({"mcp": str(item.get("mcp") or ""), "tool": str(item.get("tool") or "")})

    print(json.dumps({
        "ok": True,
        "result": normalize_result(result),
        "used_tools": used_tools_list,
        "used_mcps": used_mcps_list,
    }))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}))
"""


class CodeExecutionError(RuntimeError):
    pass


class CodeRuntimeExecutor:
    def run(
        self,
        input_text: str,
        custom_code: str,
        context: dict | None = None,
        tools: list[dict] | None = None,
        mcps: list[dict] | None = None,
    ) -> str:
        if not custom_code.strip():
            raise CodeExecutionError("custom_code is empty")

        self._validate_code(custom_code)
        payload = {
            "input_text": input_text,
            "custom_code": custom_code,
            "context": dict(context or {}),
            "tools": list(tools or []),
            "mcps": list(mcps or []),
        }
        encoded_payload = base64.b64encode(json.dumps(payload, ensure_ascii=False).encode("utf-8")).decode("ascii")
        runner_path = None

        try:
            with tempfile.NamedTemporaryFile("w", suffix="_ha_code_runner.py", delete=False, encoding="utf-8") as handle:
                handle.write(_RUNNER_SCRIPT)
                runner_path = handle.name

            proc = subprocess.run(
                [sys.executable, "-I", runner_path, encoded_payload],
                capture_output=True,
                text=True,
                timeout=settings.code_execution_timeout_seconds,
                check=False,
            )
            raw_output = (proc.stdout or "").strip()
            if not raw_output:
                stderr = (proc.stderr or "").strip()
                raise CodeExecutionError(stderr or "Code execution returned empty output")

            # Runner always prints one JSON line as the last line.
            last_line = raw_output.splitlines()[-1]
            try:
                data = json.loads(last_line)
            except json.JSONDecodeError as exc:
                raise CodeExecutionError("Invalid code execution output") from exc

            if not data.get("ok"):
                raise CodeExecutionError(str(data.get("error") or "Code execution failed"))

            result_text = str(data.get("result") or "")
            used_tools = list(data.get("used_tools") or [])
            used_mcps = list(data.get("used_mcps") or [])
            if len(result_text) > settings.code_execution_max_output_chars:
                result_text = result_text[: settings.code_execution_max_output_chars] + "\n...[truncated]"
            return {"text": result_text, "used_tools": used_tools, "used_mcps": used_mcps}
        except subprocess.TimeoutExpired as exc:
            raise CodeExecutionError(
                f"Code execution timeout after {settings.code_execution_timeout_seconds}s"
            ) from exc
        finally:
            if runner_path and os.path.exists(runner_path):
                try:
                    os.remove(runner_path)
                except OSError:
                    pass

    def _validate_code(self, custom_code: str) -> None:
        try:
            tree = ast.parse(custom_code)
        except SyntaxError as exc:
            raise CodeExecutionError(f"Syntax error: {exc}") from exc

        for node in ast.walk(tree):
            if isinstance(node, _FORBIDDEN_AST_NODES):
                raise CodeExecutionError(f"Forbidden syntax: {node.__class__.__name__}")
            if isinstance(node, ast.Import):
                for alias in node.names:
                    base_name = str(alias.name or "").split(".")[0]
                    if base_name not in _ALLOWED_IMPORT_NAMES:
                        raise CodeExecutionError(f"Import not allowed: {alias.name}")
            if isinstance(node, ast.ImportFrom):
                if not node.module:
                    raise CodeExecutionError("Relative imports are not allowed")
                base_name = str(node.module).split(".")[0]
                if base_name not in _ALLOWED_IMPORT_NAMES:
                    raise CodeExecutionError(f"Import not allowed: {node.module}")

    def _normalize_result(self, value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value
        try:
            return json.dumps(value, ensure_ascii=False)
        except TypeError:
            return str(value)


code_runtime_executor = CodeRuntimeExecutor()
