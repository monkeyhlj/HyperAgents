from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id, get_db
from app.models.enums import ResourceKind, Visibility
from app.schemas.resource import Resource, ResourceCreate, ResourceTemplate, ResourceUpdate
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


@router.delete("/{resource_id}")
def delete_resource(
    resource_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> dict[str, bool]:
    store.delete_resource(db, resource_id=resource_id, actor=user_id)
    return {"ok": True}
