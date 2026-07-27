from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
import json
import re

from app.api.deps import get_current_user_id, get_db
from app.models.enums import ResourceKind, Visibility
from app.runtime.code_executor import code_runtime_executor
from app.runtime.llm_service import LLMRequest, llm_service
from app.schemas.resource import (
    OwnedResource,
    Resource,
    ResourceCreate,
    ResourcePreviewChatRequest,
    ResourcePreviewChatResponse,
    ResourceTemplate,
    ResourceUpdate,
)
from app.services.default_resource_store import default_resource_store
from app.services.postgres_store import store


router = APIRouter()


def _skill_display_name(skill: dict) -> str:
    return str(skill.get("name") or skill.get("skill_id") or "skill").strip()


def _is_skill_listing_query(text: str) -> bool:
    normalized = (text or "").strip().lower()
    return any(pattern in normalized for pattern in ("skill", "skills", "技能", "能力")) and any(
        word in normalized for word in ("哪些", "有什么", "list", "available", "当前", "现在")
    )


def _skill_matches_request(skill: dict, user_text: str) -> bool:
    normalized = (user_text or "").strip().lower()
    if not normalized:
        return False

    name = _skill_display_name(skill).lower()
    if name and name in normalized:
        return True

    for capability in skill.get("capabilities") or []:
        capability_text = str(capability).strip().lower()
        if capability_text and capability_text in normalized:
            return True

    haystack = " ".join(
        str(part)
        for part in (
            skill.get("name") or "",
            skill.get("description") or "",
            skill.get("purpose") or "",
            " ".join(str(item) for item in (skill.get("capabilities") or [])),
        )
        if part
    ).lower()
    for token in re.split(r"[\s,，。；;、/|()（）\[\]{}:：]+", normalized):
        token = token.strip()
        if len(token) >= 3 and token in haystack:
            return True

    return False


def _explicitly_requested_skills(bound_skills: list[dict], user_text: str) -> list[dict]:
    normalized = (user_text or "").strip().lower()
    if not normalized:
        return []

    requested: list[dict] = []
    for skill in bound_skills:
        name = _skill_display_name(skill).lower()
        if name and re.search(rf"(?<![a-z0-9_-]){re.escape(name)}(?![a-z0-9_-])", normalized):
            requested.append(skill)
    return requested


def _build_skill_preview_prompt(bound_skills: list[dict], user_text: str) -> str:
    if not bound_skills:
        return ""

    lines = [
        "Agent Skills are lightweight, reusable instruction packages. Use progressive disclosure:",
        "1. Discovery: first consider only each Skill name and short description.",
        "2. Activation: load and follow full SKILL.md instructions only when the user task matches that Skill.",
        "3. Execution: follow activated instructions strictly.",
        "",
        "Available Skills (discovery view):",
    ]
    for item in bound_skills:
        purpose = item.get("purpose") or item.get("description") or "No short description provided"
        lines.append(f"- {_skill_display_name(item)}: {purpose}; capabilities={item.get('capabilities') or []}")

    if _is_skill_listing_query(user_text):
        activated = []
    else:
        activated = _explicitly_requested_skills(bound_skills, user_text)
        if not activated:
            activated = [item for item in bound_skills if _skill_matches_request(item, user_text)]
    if not activated and len(bound_skills) == 1 and not _is_skill_listing_query(user_text):
        activated = bound_skills

    if activated:
        lines.append("")
        lines.append("Activated Skill instructions for this request:")
        for item in activated:
            instructions = (item.get("skill_md_content") or item.get("purpose") or item.get("description") or "").strip()
            lines.append(f"\n--- Skill: {_skill_display_name(item)} ---")
            lines.append(instructions or "No detailed SKILL.md instructions were uploaded for this Skill.")
        lines.append("")
        lines.append("When you use an activated Skill, include a final line exactly like: 使用的 Skill: <skill name>")
    else:
        lines.append("")
        lines.append("No full Skill instructions are activated for this request. Do not claim to use a Skill unless the user's task clearly matches one.")

    return "\n".join(lines)


@router.get("/defaults", response_model=list[ResourceTemplate])
def list_default_resource_templates(
    kind: ResourceKind | None = Query(default=None),
    visibility: Visibility | None = Query(default=None),
    user_id: str = Depends(get_current_user_id),
) -> list[ResourceTemplate]:
    _ = user_id
    templates = default_resource_store.list_templates()
    result: list[ResourceTemplate] = []
    for item in templates:
        if kind and item.kind != kind:
            continue
        if visibility and item.visibility != visibility:
            continue
        result.append(item)
    return result


@router.post("/projects/{project_id}", response_model=Resource)
def create_resource(
    project_id: str,
    payload: ResourceCreate,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> Resource:
    store.assert_project_member(db, project_id, user_id)
    return store.add_resource(
        db,
        project_id=project_id,
        owner_id=user_id,
        kind=payload.kind,
        name=payload.name,
        description=payload.description,
        visibility=payload.visibility,
        model_provider=payload.model_provider,
        model_name=payload.model_name,
        provider_profile=payload.provider_profile,
        provider_connection_id=payload.provider_connection_id,
        config=payload.config,
    )


@router.get("/mine", response_model=list[OwnedResource])
def list_owned_resources(
    kind: ResourceKind | None = Query(default=None),
    q: str | None = Query(default=None, max_length=120),
    project_q: str | None = Query(default=None, max_length=120),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> list[OwnedResource]:
    return store.list_owned_resources(db, user_id=user_id, kind=kind, keyword=q, project_keyword=project_q)


@router.post("/preview-chat", response_model=ResourcePreviewChatResponse)
def preview_resource_chat(
    payload: ResourcePreviewChatRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> ResourcePreviewChatResponse:
    store.assert_project_member(db, payload.project_id, user_id)
    system_prompt = payload.system_prompt
    config = payload.config or {}
    skill_ids = [str(item) for item in (config.get("skill_ids") or []) if item]
    bound_skills = store.list_skill_resources_for_project(
        db,
        project_id=payload.project_id,
        skill_ids=skill_ids,
        actor=user_id,
    )
    skill_prompt = _build_skill_preview_prompt(bound_skills, payload.text)
    if skill_prompt:
        system_prompt = f"{system_prompt}\n\n{skill_prompt}" if system_prompt else skill_prompt

    provider_connection = None
    if payload.provider_connection_id:
        provider_connection = store.get_provider_connection_runtime_config(
            db,
            connection_id=payload.provider_connection_id,
            actor=user_id,
        )
    if (payload.run_mode or "llm").strip().lower() == "code":
        tools = store.list_tool_resources_for_project(
            db,
            project_id=payload.project_id,
            tool_ids=list((payload.config or {}).get("tool_ids") or []),
            actor=user_id,
        )
        mcps = store.list_mcp_resources_for_project(
            db,
            project_id=payload.project_id,
            mcp_ids=list((payload.config or {}).get("mcp_ids") or []),
            actor=user_id,
        )
        code_result = code_runtime_executor.run(
            payload.text,
            custom_code=payload.custom_code or "",
            context={
                "project_id": payload.project_id,
                "user_id": user_id,
                "config": payload.config,
            },
            tools=tools,
            mcps=mcps,
        )
        text = code_result.get("text", "") if isinstance(code_result, dict) else str(code_result)
        if llm_service.code_requests_llm(text) and (provider_connection or payload.model_provider or payload.model_name):
            text = llm_service.generate(
                LLMRequest(
                    text=payload.text,
                    model_provider=payload.model_provider,
                    model_name=payload.model_name,
                    provider_profile=payload.provider_profile,
                    provider_connection_id=payload.provider_connection_id,
                    provider_connection=provider_connection,
                    system_prompt=system_prompt,
                )
            ).text
    else:
        text = llm_service.generate(
            LLMRequest(
                text=payload.text,
                model_provider=payload.model_provider,
                model_name=payload.model_name,
                provider_profile=payload.provider_profile,
                    provider_connection_id=payload.provider_connection_id,
                    provider_connection=provider_connection,
                system_prompt=system_prompt,
            )
        ).text
    return ResourcePreviewChatResponse(text=text)


@router.get("/projects/{project_id}", response_model=list[Resource])
def list_resources(
    project_id: str,
    kind: ResourceKind | None = Query(default=None),
    visibility: Visibility | None = Query(default=None),
    include_defaults: bool = Query(default=True),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> list[Resource]:
    custom_resources = store.list_project_resources(db, project_id, user_id, kind, visibility)
    if not include_defaults:
        return custom_resources

    default_resources = default_resource_store.list_resources_for_project(project_id, kind=kind, visibility=visibility)
    return [*default_resources, *custom_resources]


@router.patch("/{resource_id}", response_model=Resource)
def update_resource(
    resource_id: str,
    payload: ResourceUpdate,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> Resource:
    return store.update_resource(db, resource_id=resource_id, actor=user_id, payload=payload)


@router.get("/{resource_id}", response_model=Resource)
def get_resource(
    resource_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> Resource:
    return store.get_resource(db, resource_id=resource_id, actor=user_id)


@router.delete("/{resource_id}")
def delete_resource(
    resource_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> dict[str, bool]:
    store.delete_resource(db, resource_id=resource_id, actor=user_id)
    return {"ok": True}


