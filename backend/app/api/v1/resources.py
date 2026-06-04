from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id, get_db
from app.models.enums import ResourceKind, Visibility
from app.runtime.code_executor import code_runtime_executor
from app.runtime.executor import runtime_executor
from app.schemas.resource import (
    CodeVersionPublishRequest,
    CodeVersionRecord,
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
    if (payload.run_mode or "llm").strip().lower() == "code":
        text = code_runtime_executor.run(
            payload.text,
            custom_code=payload.custom_code or "",
            context={
                "project_id": payload.project_id,
                "user_id": user_id,
                "config": payload.config,
            },
        )
    else:
        text = runtime_executor.run_chat(
            payload.text,
            model_provider=payload.model_provider,
            model_name=payload.model_name,
            provider_profile=payload.provider_profile,
            system_prompt=payload.system_prompt,
        )
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


@router.get("/{resource_id}/code-versions", response_model=list[CodeVersionRecord])
def list_code_versions(
    resource_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> list[CodeVersionRecord]:
    return store.list_resource_code_versions(db, resource_id=resource_id, actor=user_id)


@router.post("/{resource_id}/code-versions/publish", response_model=list[CodeVersionRecord])
def publish_code_version(
    resource_id: str,
    payload: CodeVersionPublishRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> list[CodeVersionRecord]:
    return store.publish_resource_code_version(
        db,
        resource_id=resource_id,
        actor=user_id,
        note=payload.note,
        code=payload.code,
    )


@router.post("/{resource_id}/code-versions/{version_id}/rollback", response_model=list[CodeVersionRecord])
def rollback_code_version(
    resource_id: str,
    version_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> list[CodeVersionRecord]:
    return store.rollback_resource_code_version(db, resource_id=resource_id, version_id=version_id, actor=user_id)
