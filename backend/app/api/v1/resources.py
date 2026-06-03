from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id, get_db
from app.models.enums import ResourceKind, Visibility
from app.schemas.resource import Resource, ResourceCreate
from app.services.postgres_store import store


router = APIRouter()


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
        config=payload.config,
    )


@router.get("/projects/{project_id}", response_model=list[Resource])
def list_resources(
    project_id: str,
    kind: ResourceKind | None = Query(default=None),
    visibility: Visibility | None = Query(default=None),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> list[Resource]:
    return store.list_project_resources(db, project_id, user_id, kind, visibility)
