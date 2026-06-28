from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
import json

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
                    system_prompt=payload.system_prompt,
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
                system_prompt=payload.system_prompt,
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
