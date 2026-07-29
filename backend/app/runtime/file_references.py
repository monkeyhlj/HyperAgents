from __future__ import annotations

import re

_PATH_PREFIXES = ("uploads", "generated", "chat_outputs")
_PATH_RE = re.compile(
    r"((?:uploads|generated|chat_outputs)/[^\s，。；;：:]+?\.[A-Za-z0-9]{1,8})",
    flags=re.IGNORECASE,
)


def extract_referenced_file_paths(text: str) -> list[str]:
    """Extract My Files relative paths mentioned in user text.

    The runtime only accepts paths under known My Files namespaces. Absolute
    paths and traversal are intentionally ignored here; final validation happens
    in user_file_service when a file is actually opened.
    """
    normalized = (text or "").replace("\\", "/")
    paths: list[str] = []
    for match in _PATH_RE.finditer(normalized):
        path = match.group(1).strip().strip("'\"`)")
        if not path or ".." in path.split("/"):
            continue
        if not path.lower().startswith(tuple(f"{prefix}/" for prefix in _PATH_PREFIXES)):
            continue
        if path not in paths:
            paths.append(path)
    return paths