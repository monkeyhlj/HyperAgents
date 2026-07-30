from __future__ import annotations

import json
import re
from typing import Any

_TEMPLATE_RE = re.compile(r"{{\s*([^{}]+?)\s*}}")


def render_template(value: Any, context: dict[str, Any]) -> Any:
    if isinstance(value, str):
        return _render_string(value, context)
    if isinstance(value, list):
        return [render_template(item, context) for item in value]
    if isinstance(value, dict):
        return {key: render_template(item, context) for key, item in value.items()}
    return value


def resolve_path(path: str, context: dict[str, Any]) -> Any:
    current: Any = context
    for part in path.strip().split("."):
        if isinstance(current, dict):
            current = current.get(part)
        elif isinstance(current, list) and part.isdigit():
            index = int(part)
            current = current[index] if 0 <= index < len(current) else None
        else:
            return None
    return current


def _render_string(text: str, context: dict[str, Any]) -> Any:
    matches = list(_TEMPLATE_RE.finditer(text))
    if not matches:
        return text
    if len(matches) == 1 and matches[0].span() == (0, len(text)):
        return resolve_path(matches[0].group(1), context)

    def replace(match: re.Match[str]) -> str:
        value = resolve_path(match.group(1), context)
        if value is None:
            return ""
        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False)
        return str(value)

    return _TEMPLATE_RE.sub(replace, text)
