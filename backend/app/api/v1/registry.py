from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id, get_db
from app.models.enums import ResourceKind, Visibility
from app.schemas.registry import RegistryItemCreate, RegistryListResponse
from app.schemas.resource import Resource
from app.services.postgres_store import store


router = APIRouter()
_ALLOWED_REGISTRY_KINDS = {ResourceKind.MCP, ResourceKind.TOOL, ResourceKind.SKILL}


def _assert_registry_kind(kind: ResourceKind) -> None:
    if kind not in _ALLOWED_REGISTRY_KINDS:
        raise HTTPException(status_code=400, detail="Registry kind must be one of: mcp, tool, skill")


@router.post("/projects/{project_id}/{kind}", response_model=Resource)
def create_registry_item(
    project_id: str,
    kind: ResourceKind,
    payload: RegistryItemCreate,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> Resource:
    _assert_registry_kind(kind)
    store.assert_project_member(db, project_id, user_id)
    return store.add_resource(
        db=db,
        project_id=project_id,
        owner_id=user_id,
        kind=kind,
        name=payload.name,
        description=payload.description,
        visibility=payload.visibility,
        model_provider=payload.model_provider,
        model_name=payload.model_name,
        config=payload.config,
    )


@router.get("/projects/{project_id}/{kind}", response_model=RegistryListResponse)
def list_registry_items(
    project_id: str,
    kind: ResourceKind,
    visibility: Visibility | None = Query(default=None),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> RegistryListResponse:
    _assert_registry_kind(kind)
    items = store.list_project_resources(db, project_id, user_id, kind, visibility)
    return RegistryListResponse(items=items, total=len(items))


@router.get("/public/{kind}", response_model=RegistryListResponse)
def list_public_registry_items(
    kind: ResourceKind,
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> RegistryListResponse:
    _assert_registry_kind(kind)
    items = store.list_public_resources(db, kind, limit)
    return RegistryListResponse(items=items, total=len(items))
