from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.db.models import (
    ChatMessageModel,
    ChatSessionModel,
    ProjectMemberModel,
    ProjectModel,
    ResourceModel,
)
from app.models.enums import ResourceKind, Visibility
from app.schemas.project import Project
from app.schemas.resource import Resource


class PostgresStore:
    def add_project(self, db: Session, payload_name: str, payload_description: str, owner_id: str) -> Project:
        project = ProjectModel(name=payload_name, description=payload_description, owner_id=owner_id)
        db.add(project)
        db.commit()
        db.refresh(project)
        return self._to_project_schema(db, project)

    def list_projects(self, db: Session, user_id: str) -> list[Project]:
        stmt = (
            select(ProjectModel)
            .outerjoin(ProjectMemberModel, ProjectMemberModel.project_id == ProjectModel.id)
            .where(or_(ProjectModel.owner_id == user_id, ProjectMemberModel.user_id == user_id))
            .distinct()
        )
        projects = db.scalars(stmt).all()
        return [self._to_project_schema(db, item) for item in projects]

    def get_project(self, db: Session, project_id: str) -> ProjectModel:
        project = db.get(ProjectModel, project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        return project

    def assert_project_member(self, db: Session, project_id: str, user_id: str) -> ProjectModel:
        project = self.get_project(db, project_id)
        if user_id == project.owner_id:
            return project
        member_stmt = select(ProjectMemberModel).where(
            and_(ProjectMemberModel.project_id == project_id, ProjectMemberModel.user_id == user_id)
        )
        member = db.scalar(member_stmt)
        if not member:
            raise HTTPException(status_code=403, detail="No access to project")
        return project

    def add_member(self, db: Session, project_id: str, actor: str, new_member: str) -> Project:
        project = self.get_project(db, project_id)
        if actor != project.owner_id:
            raise HTTPException(status_code=403, detail="Only owner can add members")
        if new_member == project.owner_id:
            return self._to_project_schema(db, project)
        member_stmt = select(ProjectMemberModel).where(
            and_(ProjectMemberModel.project_id == project_id, ProjectMemberModel.user_id == new_member)
        )
        exists = db.scalar(member_stmt)
        if not exists:
            db.add(ProjectMemberModel(project_id=project_id, user_id=new_member))
            project.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(project)
        return self._to_project_schema(db, project)

    def add_resource(
        self,
        db: Session,
        project_id: str,
        owner_id: str,
        kind: ResourceKind,
        name: str,
        description: str,
        visibility: Visibility,
        model_provider: str | None,
        model_name: str | None,
        config: dict,
    ) -> Resource:
        resource = ResourceModel(
            project_id=project_id,
            owner_id=owner_id,
            kind=kind.value,
            name=name,
            description=description,
            visibility=visibility.value,
            model_provider=model_provider,
            model_name=model_name,
            config=config,
        )
        db.add(resource)
        db.commit()
        db.refresh(resource)
        return self._to_resource_schema(resource)

    def list_project_resources(
        self,
        db: Session,
        project_id: str,
        user_id: str,
        kind: ResourceKind | None,
        visibility: Visibility | None = None,
    ) -> list[Resource]:
        project = self.assert_project_member(db, project_id, user_id)

        stmt = select(ResourceModel).where(ResourceModel.project_id == project_id)
        if kind is not None:
            stmt = stmt.where(ResourceModel.kind == kind.value)
        if visibility is not None:
            stmt = stmt.where(ResourceModel.visibility == visibility.value)

        candidates = db.scalars(stmt).all()
        result: list[Resource] = []
        for item in candidates:
            item_visibility = Visibility(item.visibility)
            if item_visibility == Visibility.PUBLIC:
                result.append(self._to_resource_schema(item))
                continue
            if item_visibility == Visibility.PRIVATE:
                if item.owner_id == user_id:
                    result.append(self._to_resource_schema(item))
                continue
            if user_id == project.owner_id or self._is_member(db, project_id, user_id):
                result.append(self._to_resource_schema(item))
        return result

    def list_public_resources(
        self,
        db: Session,
        kind: ResourceKind,
        limit: int = 200,
    ) -> list[Resource]:
        stmt = (
            select(ResourceModel)
            .where(
                ResourceModel.kind == kind.value,
                ResourceModel.visibility == Visibility.PUBLIC.value,
            )
            .order_by(ResourceModel.updated_at.desc())
            .limit(limit)
        )
        return [self._to_resource_schema(item) for item in db.scalars(stmt).all()]

    def create_chat_session(self, db: Session, project_id: str, user_id: str, title: str) -> dict:
        self.assert_project_member(db, project_id, user_id)
        session = ChatSessionModel(project_id=project_id, title=title, owner_id=user_id)
        db.add(session)
        db.commit()
        db.refresh(session)
        return {
            "id": session.id,
            "project_id": session.project_id,
            "title": session.title,
            "owner_id": session.owner_id,
            "created_at": session.created_at.isoformat(),
        }

    def append_chat_message(self, db: Session, session_id: str, role: str, text: str) -> None:
        session = db.get(ChatSessionModel, session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Chat session not found")
        db.add(ChatMessageModel(session_id=session_id, role=role, text=text))
        db.commit()

    def get_chat_session_for_user(self, db: Session, session_id: str, user_id: str) -> ChatSessionModel:
        session = db.get(ChatSessionModel, session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Chat session not found")
        self.assert_project_member(db, session.project_id, user_id)
        return session

    def get_agent_resource_for_project(self, db: Session, project_id: str, agent_id: str) -> ResourceModel:
        resource = db.get(ResourceModel, agent_id)
        if not resource or resource.project_id != project_id:
            raise HTTPException(status_code=404, detail="Agent resource not found")
        if resource.kind != ResourceKind.AGENT.value:
            raise HTTPException(status_code=400, detail="Provided agent_id is not an agent resource")
        return resource

    def _to_project_schema(self, db: Session, project: ProjectModel) -> Project:
        members_stmt = select(ProjectMemberModel.user_id).where(ProjectMemberModel.project_id == project.id)
        members = list(db.scalars(members_stmt).all())
        return Project(
            id=project.id,
            created_at=project.created_at,
            updated_at=project.updated_at,
            name=project.name,
            description=project.description,
            owner_id=project.owner_id,
            members=members,
        )

    def _to_resource_schema(self, resource: ResourceModel) -> Resource:
        return Resource(
            id=resource.id,
            created_at=resource.created_at,
            updated_at=resource.updated_at,
            project_id=resource.project_id,
            owner_id=resource.owner_id,
            kind=ResourceKind(resource.kind),
            name=resource.name,
            description=resource.description,
            visibility=Visibility(resource.visibility),
            model_provider=resource.model_provider,
            model_name=resource.model_name,
            config=resource.config,
        )

    def _is_member(self, db: Session, project_id: str, user_id: str) -> bool:
        stmt = select(ProjectMemberModel.id).where(
            and_(ProjectMemberModel.project_id == project_id, ProjectMemberModel.user_id == user_id)
        )
        return db.scalar(stmt) is not None


store = PostgresStore()
