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
    "bool": bool,
    "dict": dict,
    "enumerate": enumerate,
    "float": float,
    "int": int,
    "len": len,
    "list": list,
    "max": max,
    "min": min,
    "range": range,
    "round": round,
    "set": set,
    "sorted": sorted,
    "str": str,
    "sum": sum,
    "tuple": tuple,
    "zip": zip,
}


_FORBIDDEN_AST_NODES = (
    ast.Import,
    ast.ImportFrom,
    ast.With,
    ast.AsyncWith,
    ast.Raise,
    ast.Global,
    ast.Nonlocal,
)


_RUNNER_SCRIPT = r"""
import ast
import base64
import json
import sys

ALLOWED_BUILTINS = {
    "abs": abs,
    "all": all,
    "any": any,
    "bool": bool,
    "dict": dict,
    "enumerate": enumerate,
    "float": float,
    "int": int,
    "len": len,
    "list": list,
    "max": max,
    "min": min,
    "range": range,
    "round": round,
    "set": set,
    "sorted": sorted,
    "str": str,
    "sum": sum,
    "tuple": tuple,
    "zip": zip,
}

FORBIDDEN_AST_NODES = (
    ast.Import,
    ast.ImportFrom,
    ast.With,
    ast.AsyncWith,
    ast.Raise,
    ast.Global,
    ast.Nonlocal,
)


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


def main():
    raw = sys.argv[1] if len(sys.argv) > 1 else ""
    payload = json.loads(base64.b64decode(raw.encode("ascii")).decode("utf-8")) if raw else {}
    input_text = payload.get("input_text", "")
    custom_code = payload.get("custom_code", "")
    context = payload.get("context", {})

    if not str(custom_code).strip():
        raise RuntimeError("custom_code is empty")

    validate_code(custom_code)

    safe_globals = {
        "__builtins__": ALLOWED_BUILTINS,
        "json": json,
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

    print(json.dumps({"ok": True, "result": normalize_result(result)}))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}))
"""


class CodeExecutionError(RuntimeError):
    pass


class CodeRuntimeExecutor:
    def run(self, input_text: str, custom_code: str, context: dict | None = None) -> str:
        if not custom_code.strip():
            raise CodeExecutionError("custom_code is empty")

        self._validate_code(custom_code)
        payload = {
            "input_text": input_text,
            "custom_code": custom_code,
            "context": dict(context or {}),
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

            result = str(data.get("result") or "")
            if len(result) > settings.code_execution_max_output_chars:
                return result[: settings.code_execution_max_output_chars] + "\n...[truncated]"
            return result
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
