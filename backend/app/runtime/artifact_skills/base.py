from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ArtifactSkillResult:
    handled: bool
    answer: str = ""
    saved_files: list[str] = field(default_factory=list)
    runtime_events: list[dict[str, Any]] = field(default_factory=list)
    used_skills: list[str] = field(default_factory=list)