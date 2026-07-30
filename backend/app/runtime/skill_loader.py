"""Helpers for progressive Agent Skill loading."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.runtime.skill_service import get_skill_package_root


def skill_display_name(skill: dict[str, Any]) -> str:
    return str(skill.get("name") or skill.get("skill_id") or "skill").strip()


def skill_aliases(skill: dict[str, Any]) -> set[str]:
    name = skill_display_name(skill).strip().lower()
    aliases = {name} if name else set()
    if name == "frontend-design":
        aliases.add("front-design")
    if name == "front-design":
        aliases.add("frontend-design")
    if name in {"spreadsheet", "spreadsheets"}:
        aliases.add("xlsx")
    if name == "xlsx":
        aliases.update({"spreadsheet", "spreadsheets", "excel"})
    return {item for item in aliases if item}


def find_skill(bound_skills: list[dict[str, Any]], skill_name: str) -> dict[str, Any] | None:
    requested = str(skill_name or "").strip().lower()
    if not requested:
        return None
    for skill in bound_skills:
        if requested in skill_aliases(skill):
            return skill
    return None


def discover_skill_scripts(skill: dict[str, Any]) -> list[str]:
    skill_id = str(skill.get("skill_id") or "").strip()
    if not skill_id:
        return []
    try:
        root = get_skill_package_root(skill_id)
    except Exception:
        return []
    scripts_dir = root / "scripts"
    if not scripts_dir.exists() or not scripts_dir.is_dir():
        return []
    scripts: list[str] = []
    for path in sorted(scripts_dir.rglob("*.py")):
        if not path.is_file() or "__pycache__" in path.parts:
            continue
        scripts.append(path.relative_to(root).as_posix())
    return scripts


def build_skill_catalog_text(bound_skills: list[dict[str, Any]]) -> str:
    if not bound_skills:
        return "- No Agent Skills are bound."
    lines: list[str] = []
    for skill in bound_skills:
        name = skill_display_name(skill)
        desc = skill.get("description") or skill.get("purpose") or "No short description provided"
        scripts = discover_skill_scripts(skill)
        script_hint = f"; scripts={scripts}" if scripts else ""
        executable = "yes" if str(skill.get("entrypoint") or "").strip() else "no"
        lines.append(f"- {name}: {desc}; executable={executable}{script_hint}")
    return "\n".join(lines)


def render_loaded_skill(skill: dict[str, Any]) -> str:
    name = skill_display_name(skill)
    scripts = discover_skill_scripts(skill)
    entrypoint = str(skill.get("entrypoint") or "").strip() or "-"
    content = str(skill.get("skill_md_content") or skill.get("purpose") or skill.get("description") or "").strip()
    payload = {
        "skill": name,
        "entrypoint": entrypoint,
        "scripts": scripts,
    }
    return (
        f"Loaded Agent Skill: {name}\n"
        f"Metadata: {json.dumps(payload, ensure_ascii=False)}\n\n"
        "Full SKILL.md instructions:\n"
        f"{content or 'No detailed SKILL.md instructions were uploaded for this Skill.'}"
    )
