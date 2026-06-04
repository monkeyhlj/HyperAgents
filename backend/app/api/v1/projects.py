from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id, get_db
from app.schemas.project import MemberAddRequest, MemberManagerGrantRequest, Project, ProjectCreate, ProjectUpdate
from app.services.postgres_store import store


router = APIRouter()


@router.post("", response_model=Project)
def create_project(
    payload: ProjectCreate,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> Project:
    return store.add_project(
        db,
        payload_name=payload.name,
        payload_description=payload.description,
        owner_id=user_id,
    )


@router.get("", response_model=list[Project])
def list_projects(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> list[Project]:
    return store.list_projects(db, user_id)


@router.get("/{project_id}", response_model=Project)
def get_project_detail(
    project_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> Project:
    return store.get_project_for_user(db, project_id, user_id)


@router.patch("/{project_id}", response_model=Project)
def update_project(
    project_id: str,
    payload: ProjectUpdate,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> Project:
    return store.update_project(db, project_id=project_id, actor=user_id, payload=payload)


@router.delete("/{project_id}")
def delete_project(
    project_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> dict[str, bool]:
    store.delete_project(db, project_id=project_id, actor=user_id)
    return {"ok": True}


@router.post("/{project_id}/members", response_model=Project)
def add_project_member(
    project_id: str,
    payload: MemberAddRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> Project:
    return store.add_member(
        db,
        project_id,
        actor=user_id,
        new_member=payload.user_id,
        account=payload.account,
    )


@router.delete("/{project_id}/members/{member_id}", response_model=Project)
def remove_project_member(
    project_id: str,
    member_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> Project:
    return store.remove_member(db, project_id, actor=user_id, target_member=member_id)


@router.post("/{project_id}/member-managers", response_model=Project)
def grant_member_manager(
    project_id: str,
    payload: MemberManagerGrantRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> Project:
    return store.grant_member_manager(
        db,
        project_id=project_id,
        actor=user_id,
        manager_user_id=payload.user_id,
        account=payload.account,
    )


@router.delete("/{project_id}/member-managers/{member_id}", response_model=Project)
def revoke_member_manager(
    project_id: str,
    member_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> Project:
    return store.revoke_member_manager(db, project_id=project_id, actor=user_id, manager_user_id=member_id)
