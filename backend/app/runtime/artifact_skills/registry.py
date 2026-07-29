from __future__ import annotations

from typing import Any, Callable

from app.runtime.artifact_skills.base import ArtifactSkillResult

ArtifactSkillHandler = Callable[..., ArtifactSkillResult]

_HANDLERS: list[ArtifactSkillHandler] = []


def register_artifact_skill_handler(handler: ArtifactSkillHandler) -> None:
    """Register an optional generic artifact handler.

    Uploaded Agent Skills should normally execute through SkillRuntime when they
    declare an entrypoint. This registry is intentionally empty by default so the
    backend does not hard-code behavior for particular Skill names like xlsx or
    front-design.
    """
    if handler not in _HANDLERS:
        _HANDLERS.append(handler)


def run_artifact_skill_pipelines(
    *,
    user_id: str,
    user_text: str,
    active_skill_names: list[str],
    bound_skills: list[dict[str, Any]],
) -> ArtifactSkillResult:
    """Run optional generic artifact handlers after Skill activation.

    This is a compatibility extension point only. It must not import or encode
    behavior for a specific uploaded Skill package. Skill-specific behavior
    belongs in the Skill package itself, preferably behind a declared entrypoint.
    """
    if not active_skill_names:
        return ArtifactSkillResult(handled=False)

    for handler in list(_HANDLERS):
        result = handler(
            user_id=user_id,
            user_text=user_text,
            active_skill_names=active_skill_names,
            bound_skills=bound_skills,
        )
        if result.handled:
            return result

    return ArtifactSkillResult(handled=False)
