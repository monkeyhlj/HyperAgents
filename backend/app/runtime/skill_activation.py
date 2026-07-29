"""Skill discovery and activation helpers.

This module keeps Skill selection deterministic and reusable outside chat.py.
It intentionally separates listing/discovery from activation so MCP/tool
capabilities are not mistaken for Agent Skills.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from app.runtime.skill_loader import discover_skill_scripts


@dataclass
class SkillActivationResult:
    discovery_prompt: str
    activated_skills: list[dict[str, Any]] = field(default_factory=list)
    activation_reasons: list[dict[str, Any]] = field(default_factory=list)

    @property
    def activated_names(self) -> list[str]:
        return [skill_display_name(skill) for skill in self.activated_skills]


def is_skill_listing_query(text: str) -> bool:
    normalized = (text or "").strip().lower()
    patterns = [
        r"有哪些\s*skills?",
        r"有哪?些\s*skill",
        r"what\s+skills?\s+do\s+you\s+have",
        r"list\s+.*skills?",
        r"当前\s*skills?",
        r"有什么\s*skills?",
        r"现在\s*.*\s*什么\s*skills?",
    ]
    return any(re.search(pattern, normalized, flags=re.IGNORECASE) for pattern in patterns)


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


def render_bound_skills(bound_skills: list[dict[str, Any]]) -> str:
    if not bound_skills:
        return "当前没有绑定任何 Skill。"

    lines = ["当前我已绑定并可用的 Skills："]
    for idx, skill in enumerate(bound_skills, start=1):
        name = skill.get("name") or skill.get("skill_id")
        version = skill.get("version") or "-"
        entrypoint = skill.get("entrypoint") or "-"
        desc = skill.get("description") or ""
        purpose = skill.get("purpose") or desc or "未提供"
        capabilities = skill.get("capabilities") or []
        caps_text = "、".join(str(item) for item in capabilities[:6]) if capabilities else "-"
        lines.append(f"{idx}. {name}")
        lines.append(f"   - 用途: {purpose}")
        lines.append(f"   - version: {version}")
        lines.append(f"   - entrypoint: {entrypoint}")
        lines.append(f"   - capabilities: {caps_text}")
        if desc:
            lines.append(f"   - description: {desc}")

    lines.append("如你希望我调用某个 Skill，请直接说“使用 <Skill 名称> 来处理 …”，我会在回复中标注使用的 Skill。")
    return "\n".join(lines)


def extract_mentioned_skills(text: str, bound_skills: list[dict[str, Any]]) -> list[str]:
    normalized = (text or "").lower()
    result: list[str] = []
    for item in bound_skills:
        name = str(item.get("name") or "").strip()
        if name and name.lower() in normalized:
            result.append(name)
    return list(dict.fromkeys(result))


def _skill_match_haystack(skill: dict[str, Any]) -> str:
    parts = [
        skill.get("name") or "",
        skill.get("description") or "",
        skill.get("purpose") or "",
        " ".join(str(item) for item in (skill.get("capabilities") or [])),
    ]
    return " ".join(str(part) for part in parts if part).lower()


def _explicitly_requested_skills(bound_skills: list[dict[str, Any]], user_text: str) -> list[tuple[dict[str, Any], str]]:
    normalized = (user_text or "").strip().lower()
    if not normalized:
        return []

    requested: list[tuple[dict[str, Any], str]] = []
    for skill in bound_skills:
        for alias in sorted(skill_aliases(skill), key=len, reverse=True):
            if re.search(rf"(?<![a-z0-9_-]){re.escape(alias)}(?![a-z0-9_-])", normalized):
                reason = "explicit_name" if alias == skill_display_name(skill).lower() else f"explicit_alias:{alias}"
                requested.append((skill, reason))
                break
            if re.search(rf"(?:使用|用|调用|activate|use)\s*{re.escape(alias)}\s*skill", normalized):
                requested.append((skill, f"explicit_skill_phrase:{alias}"))
                break
    return requested


def _skill_matches_request(skill: dict[str, Any], user_text: str) -> tuple[bool, str]:
    normalized = (user_text or "").strip().lower()
    if not normalized:
        return False, ""

    for alias in skill_aliases(skill):
        if alias and re.search(rf"(?<![a-z0-9_-]){re.escape(alias)}(?![a-z0-9_-])", normalized):
            return True, f"alias:{alias}"

    for capability in skill.get("capabilities") or []:
        capability_text = str(capability).strip().lower()
        if capability_text and len(capability_text) >= 3 and capability_text in normalized:
            return True, f"capability:{capability_text}"

    haystack = _skill_match_haystack(skill)
    for token in re.split(r"[\s,，。；;、/|()（）\[\]{}:：]+", normalized):
        token = token.strip()
        if len(token) >= 4 and token in haystack:
            return True, f"keyword:{token}"

    for source_name, source in (("purpose", skill.get("purpose") or ""), ("description", skill.get("description") or "")):
        for phrase in re.split(r"[，。；;、\n\r]+", str(source).lower()):
            phrase = phrase.strip()
            if len(phrase) >= 6 and phrase in normalized:
                return True, f"{source_name}:{phrase[:40]}"

    return False, ""


class SkillActivationEngine:
    def discover(self, bound_skills: list[dict[str, Any]]) -> str:
        if not bound_skills:
            return "No Agent Skills are bound to this agent. Do not claim any Skill is available."

        lines = [
            "Agent Skills are lightweight, reusable instruction packages. Use progressive disclosure:",
            "1. Discovery: first consider only each Skill name and short description.",
            "2. Activation: load and follow full SKILL.md instructions only when the user task matches that Skill; when a load_skill tool is available, use it before following detailed Skill workflows.",
            "3. Execution: follow activated instructions strictly; use attached scripts/templates only when the runtime supports that action.",
            "",
            "Available Skills (discovery view):",
        ]
        for skill in bound_skills:
            name = skill_display_name(skill)
            purpose = skill.get("purpose") or skill.get("description") or "No short description provided"
            capabilities = skill.get("capabilities") or []
            entrypoint = skill.get("entrypoint") or ""
            executable = "yes" if entrypoint else "no"
            scripts = discover_skill_scripts(skill)
            script_hint = f"; scripts={scripts}" if scripts else ""
            lines.append(f"- {name}: {purpose}; capabilities={capabilities}; executable={executable}{script_hint}")
        lines.append("When a user asks about available skills, answer from the discovery list only.")
        return "\n".join(lines)

    def activate(self, user_text: str, bound_skills: list[dict[str, Any]]) -> SkillActivationResult:
        discovery_prompt = self.discover(bound_skills)
        if not bound_skills or is_skill_listing_query(user_text):
            return SkillActivationResult(discovery_prompt=discovery_prompt)

        activated: list[dict[str, Any]] = []
        reasons: list[dict[str, Any]] = []

        for skill, reason in _explicitly_requested_skills(bound_skills, user_text):
            if skill not in activated:
                activated.append(skill)
                reasons.append({"skill": skill_display_name(skill), "reason": reason})

        if not activated:
            for skill in bound_skills:
                matched, reason = _skill_matches_request(skill, user_text)
                if matched:
                    activated.append(skill)
                    reasons.append({"skill": skill_display_name(skill), "reason": reason})

        lines = [discovery_prompt]
        if activated:
            lines.extend(["", "Activated Skill instructions for this request:"])
            for skill in activated:
                name = skill_display_name(skill)
                instructions = (skill.get("skill_md_content") or skill.get("purpose") or skill.get("description") or "").strip()
                lines.append(f"\n--- Skill: {name} ---")
                lines.append(instructions or "No detailed SKILL.md instructions were uploaded for this Skill.")
            lines.extend([
                "",
                "When you use an activated Skill, include a final line exactly like: 使用的 Skill: <skill name>",
            ])
        else:
            lines.extend([
                "",
                "No full Skill instructions are activated for this request. Do not claim to use a Skill unless the user's task clearly matches one; ask a clarifying question if needed.",
            ])

        return SkillActivationResult(
            discovery_prompt="\n".join(lines),
            activated_skills=activated,
            activation_reasons=reasons,
        )


skill_activation_engine = SkillActivationEngine()