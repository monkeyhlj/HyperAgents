from __future__ import annotations

import re
from typing import Any

from app.runtime.workflow.template import resolve_path

_OP_RE = re.compile(r"^(.+?)\s*(==|!=|>=|<=|>|<|not\s+in|in)\s*(.+?)$", re.IGNORECASE)


def select_next_step(step: dict[str, Any], output_data: Any, step_ids: list[str], current_index: int) -> str | None:
    context = {"output": output_data}
    routing = step.get("routing") or []
    for route in routing:
        if not isinstance(route, dict):
            continue
        next_id = route.get("next")
        if not next_id:
            continue
        if route.get("default") is True:
            return str(next_id)
        condition = str(route.get("condition") or "").strip()
        if condition and evaluate_condition(condition, context):
            return str(next_id)

    next_index = current_index + 1
    if next_index < len(step_ids):
        return step_ids[next_index]
    return None


def evaluate_condition(condition: str, context: dict[str, Any]) -> bool:
    match = _OP_RE.match(condition.strip())
    if not match:
        return False
    left_raw, op, right_raw = match.group(1).strip(), match.group(2).strip().lower(), match.group(3).strip()
    left = _read_operand(left_raw, context)
    right = _read_operand(right_raw, context)

    try:
        if op == "==":
            return left == right
        if op == "!=":
            return left != right
        if op == ">":
            return _coerce_number(left) > _coerce_number(right)
        if op == ">=":
            return _coerce_number(left) >= _coerce_number(right)
        if op == "<":
            return _coerce_number(left) < _coerce_number(right)
        if op == "<=":
            return _coerce_number(left) <= _coerce_number(right)
        if op == "in":
            return left in right if isinstance(right, (list, tuple, set, str)) else False
        if op == "not in":
            return left not in right if isinstance(right, (list, tuple, set, str)) else False
    except Exception:
        return False
    return False


def _read_operand(raw: str, context: dict[str, Any]) -> Any:
    text = raw.strip()
    if (text.startswith("'") and text.endswith("'")) or (text.startswith('"') and text.endswith('"')):
        return text[1:-1]
    if text.lower() == "true":
        return True
    if text.lower() == "false":
        return False
    if text.lower() == "null":
        return None
    try:
        if "." in text:
            return float(text)
        return int(text)
    except ValueError:
        pass
    return resolve_path(text, context)


def _coerce_number(value: Any) -> float:
    return float(value)
