from datetime import datetime
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.db.models import (
    ChatMessageModel,
    ChatSessionModel,
    ProjectMemberPermissionModel,
    ProjectMemberModel,
    ProjectModel,
    ResourceModel,
    RuntimeRunEventModel,
    RuntimeRunModel,
    UserModel,
)
from app.models.enums import ResourceKind, Visibility
from app.schemas.auth import UserProfile, UserSearchItem
from app.schemas.project import Project, ProjectUpdate
from app.schemas.resource import OwnedResource, Resource, ResourceUpdate
from app.services.auth_utils import hash_password, verify_password


class PostgresStore:
    @staticmethod
    def _normalize_resource_payload(
        kind: ResourceKind,
        model_provider: str | None,
        model_name: str | None,
        provider_profile: str | None,
        config: dict,
    ) -> tuple[str | None, str | None, str | None, dict]:
        normalized_config = dict(config or {})
        if kind == ResourceKind.AGENT:
            if provider_profile:
                normalized_config["provider_profile"] = provider_profile
            return model_provider, model_name, provider_profile, normalized_config

        # Non-agent resources should not carry provider profile in config.
        for key in ("provider_profile",):
            normalized_config.pop(key, None)

        return None, None, None, normalized_config

    def create_user(
        self,
        db: Session,
        username: str,
        password: str,
        email: str | None = None,
        display_name: str | None = None,
    ) -> UserProfile:
        normalized_username = username.strip().lower()
        normalized_email = email.strip().lower() if email else None

        exists_by_username = db.scalar(select(UserModel).where(UserModel.username == normalized_username))
        if exists_by_username:
            raise HTTPException(status_code=409, detail="Username already exists")

        if normalized_email:
            exists_by_email = db.scalar(select(UserModel).where(UserModel.email == normalized_email))
            if exists_by_email:
                raise HTTPException(status_code=409, detail="Email already exists")

        user = UserModel(
            username=normalized_username,
            email=normalized_email,
            display_name=display_name.strip() if display_name else normalized_username,
            hashed_password=hash_password(password),
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return self._to_user_profile(user)

    def authenticate_user(self, db: Session, account: str, password: str) -> UserProfile:
        normalized = account.strip().lower()
        stmt = select(UserModel).where(or_(UserModel.username == normalized, UserModel.email == normalized))
        user = db.scalar(stmt)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid account or password")
        if not user.is_active:
            raise HTTPException(status_code=403, detail="User is inactive")
        if not verify_password(password, user.hashed_password):
            raise HTTPException(status_code=401, detail="Invalid account or password")
        return self._to_user_profile(user)

    def get_user_profile(self, db: Session, user_id: str) -> UserProfile:
        user = db.get(UserModel, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return self._to_user_profile(user)

    def search_users(self, db: Session, q: str, limit: int = 10) -> list[UserSearchItem]:
        keyword = q.strip().lower()
        if not keyword:
            return []
        pattern = f"%{keyword}%"
        stmt = (
            select(UserModel)
            .where(
                or_(
                    UserModel.username.ilike(pattern),
                    UserModel.display_name.ilike(pattern),
                )
            )
            .order_by(UserModel.username.asc())
            .limit(limit)
        )
        users = db.scalars(stmt).all()
        return [
            UserSearchItem(id=item.id, username=item.username, display_name=item.display_name)
            for item in users
        ]

    def add_project(self, db: Session, payload_name: str, payload_description: str, owner_id: str) -> Project:
        project = ProjectModel(name=payload_name, description=payload_description, owner_id=owner_id)
        db.add(project)
        db.commit()
        db.refresh(project)
        return self._to_project_schema(db, project)

    def update_project(self, db: Session, project_id: str, actor: str, payload: ProjectUpdate) -> Project:
        project = self.get_project(db, project_id)
        if actor != project.owner_id:
            raise HTTPException(status_code=403, detail="Only owner can edit project")

        if payload.name is not None:
            project.name = payload.name
        if payload.description is not None:
            project.description = payload.description
        project.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(project)
        return self._to_project_schema(db, project)

    def delete_project(self, db: Session, project_id: str, actor: str) -> None:
        project = self.get_project(db, project_id)
        if actor != project.owner_id:
            raise HTTPException(status_code=403, detail="Only owner can delete project")
        db.delete(project)
        db.commit()

    def list_projects(self, db: Session, user_id: str) -> list[Project]:
        identifiers = self._member_identifiers(db, user_id)
        stmt = (
            select(ProjectModel)
            .outerjoin(ProjectMemberModel, ProjectMemberModel.project_id == ProjectModel.id)
            .where(or_(ProjectModel.owner_id == user_id, ProjectMemberModel.user_id.in_(identifiers)))
            .distinct()
        )
        projects = db.scalars(stmt).all()
        return [self._to_project_schema(db, item) for item in projects]

    def get_project_for_user(self, db: Session, project_id: str, user_id: str) -> Project:
        project = self.assert_project_member(db, project_id, user_id)
        return self._to_project_schema(db, project)

    def get_project(self, db: Session, project_id: str) -> ProjectModel:
        project = db.get(ProjectModel, project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        return project

    def assert_project_member(self, db: Session, project_id: str, user_id: str) -> ProjectModel:
        project = self.get_project(db, project_id)
        if user_id == project.owner_id:
            return project
        identifiers = self._member_identifiers(db, user_id)
        member_stmt = select(ProjectMemberModel).where(
            and_(ProjectMemberModel.project_id == project_id, ProjectMemberModel.user_id.in_(identifiers))
        )
        member = db.scalar(member_stmt)
        if not member:
            raise HTTPException(status_code=403, detail="No access to project")
        return project

    def add_member(
        self,
        db: Session,
        project_id: str,
        actor: str,
        new_member: str | None = None,
        account: str | None = None,
    ) -> Project:
        project = self.get_project(db, project_id)
        if actor != project.owner_id and not self._can_add_members(db, project_id, actor):
            raise HTTPException(status_code=403, detail="No permission to add members")

        resolved_member = self._resolve_user_id(db, new_member=new_member, account=account)
        if resolved_member == project.owner_id:
            return self._to_project_schema(db, project)

        member_stmt = select(ProjectMemberModel).where(
            and_(ProjectMemberModel.project_id == project_id, ProjectMemberModel.user_id == resolved_member)
        )
        exists = db.scalar(member_stmt)
        if not exists:
            db.add(ProjectMemberModel(project_id=project_id, user_id=resolved_member))
            project.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(project)
        return self._to_project_schema(db, project)

    def remove_member(self, db: Session, project_id: str, actor: str, target_member: str) -> Project:
        project = self.get_project(db, project_id)
        if actor != project.owner_id:
            raise HTTPException(status_code=403, detail="Only owner can remove members")
        if target_member == project.owner_id:
            raise HTTPException(status_code=400, detail="Owner cannot be removed")

        member_stmt = select(ProjectMemberModel).where(
            and_(ProjectMemberModel.project_id == project_id, ProjectMemberModel.user_id == target_member)
        )
        member = db.scalar(member_stmt)
        if member:
            db.delete(member)
            perm_stmt = select(ProjectMemberPermissionModel).where(
                and_(
                    ProjectMemberPermissionModel.project_id == project_id,
                    ProjectMemberPermissionModel.user_id == target_member,
                )
            )
            permission_row = db.scalar(perm_stmt)
            if permission_row:
                db.delete(permission_row)
            project.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(project)
        return self._to_project_schema(db, project)

    def grant_member_manager(
        self,
        db: Session,
        project_id: str,
        actor: str,
        manager_user_id: str | None = None,
        account: str | None = None,
    ) -> Project:
        project = self.get_project(db, project_id)
        if actor != project.owner_id:
            raise HTTPException(status_code=403, detail="Only owner can grant member manager")

        resolved_member = self._resolve_user_id(db, new_member=manager_user_id, account=account)
        if resolved_member == project.owner_id:
            return self._to_project_schema(db, project)

        permission_stmt = select(ProjectMemberPermissionModel).where(
            and_(
                ProjectMemberPermissionModel.project_id == project_id,
                ProjectMemberPermissionModel.user_id == resolved_member,
            )
        )
        permission_row = db.scalar(permission_stmt)
        if permission_row:
            permission_row.can_add_members = True
        else:
            db.add(
                ProjectMemberPermissionModel(
                    project_id=project_id,
                    user_id=resolved_member,
                    can_add_members=True,
                )
            )

        if not db.scalar(
            select(ProjectMemberModel).where(
                and_(ProjectMemberModel.project_id == project_id, ProjectMemberModel.user_id == resolved_member)
            )
        ):
            db.add(ProjectMemberModel(project_id=project_id, user_id=resolved_member))

        project.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(project)
        return self._to_project_schema(db, project)

    def revoke_member_manager(self, db: Session, project_id: str, actor: str, manager_user_id: str) -> Project:
        project = self.get_project(db, project_id)
        if actor != project.owner_id:
            raise HTTPException(status_code=403, detail="Only owner can revoke member manager")

        permission_stmt = select(ProjectMemberPermissionModel).where(
            and_(
                ProjectMemberPermissionModel.project_id == project_id,
                ProjectMemberPermissionModel.user_id == manager_user_id,
            )
        )
        permission_row = db.scalar(permission_stmt)
        if permission_row:
            db.delete(permission_row)
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
        provider_profile: str | None,
        config: dict,
    ) -> Resource:
        model_provider, model_name, provider_profile, resource_config = self._normalize_resource_payload(
            kind=kind,
            model_provider=model_provider,
            model_name=model_name,
            provider_profile=provider_profile,
            config=config,
        )
        resource = ResourceModel(
            project_id=project_id,
            owner_id=owner_id,
            kind=kind.value,
            name=name,
            description=description,
            visibility=visibility.value,
            model_provider=model_provider,
            model_name=model_name,
            config=resource_config,
        )
        db.add(resource)
        db.commit()
        db.refresh(resource)
        return self._to_resource_schema(resource)

    def update_resource(self, db: Session, resource_id: str, actor: str, payload: ResourceUpdate) -> Resource:
        resource = db.get(ResourceModel, resource_id)
        if not resource:
            raise HTTPException(status_code=404, detail="Resource not found")

        project = self.assert_project_member(db, resource.project_id, actor)
        if actor != project.owner_id and actor != resource.owner_id:
            raise HTTPException(status_code=403, detail="No permission to edit resource")

        if payload.project_id is not None and payload.project_id != resource.project_id:
            new_project = self.assert_project_member(db, payload.project_id, actor)
            resource.project_id = payload.project_id

        if payload.name is not None:
            resource.name = payload.name
        if payload.description is not None:
            resource.description = payload.description
        if payload.visibility is not None:
            resource.visibility = payload.visibility.value
        if payload.model_provider is not None:
            if resource.kind == ResourceKind.AGENT.value:
                resource.model_provider = payload.model_provider
            else:
                resource.model_provider = None
        if payload.model_name is not None:
            if resource.kind == ResourceKind.AGENT.value:
                resource.model_name = payload.model_name
            else:
                resource.model_name = None

        config = dict(resource.config or {})
        if payload.config is not None:
            config = dict(payload.config)

        if resource.kind == ResourceKind.AGENT.value:
            if payload.provider_profile is not None:
                if payload.provider_profile:
                    config["provider_profile"] = payload.provider_profile
                else:
                    config.pop("provider_profile", None)
        else:
            _, _, _, config = self._normalize_resource_payload(
                kind=ResourceKind(resource.kind),
                model_provider=None,
                model_name=None,
                provider_profile=None,
                config=config,
            )
            resource.model_provider = None
            resource.model_name = None
        resource.config = config
        resource.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(resource)
        return self._to_resource_schema(resource)

    def get_resource(self, db: Session, resource_id: str, actor: str) -> Resource:
        resource = self._get_resource_for_actor(db, resource_id, actor)
        return self._to_resource_schema(resource)

    def delete_resource(self, db: Session, resource_id: str, actor: str) -> None:
        resource = db.get(ResourceModel, resource_id)
        if not resource:
            raise HTTPException(status_code=404, detail="Resource not found")

        project = self.assert_project_member(db, resource.project_id, actor)
        if actor != project.owner_id and actor != resource.owner_id:
            raise HTTPException(status_code=403, detail="No permission to delete resource")

        db.delete(resource)
        db.commit()

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

    def list_owned_resources(
        self,
        db: Session,
        user_id: str,
        kind: ResourceKind | None = None,
        keyword: str | None = None,
        project_keyword: str | None = None,
    ) -> list[OwnedResource]:
        stmt = (
            select(ResourceModel, ProjectModel)
            .join(ProjectModel, ProjectModel.id == ResourceModel.project_id)
            .where(ResourceModel.owner_id == user_id)
        )

        if kind is not None:
            stmt = stmt.where(ResourceModel.kind == kind.value)

        normalized_keyword = (keyword or "").strip()
        if normalized_keyword:
            pattern = f"%{normalized_keyword}%"
            stmt = stmt.where(
                or_(
                    ResourceModel.name.ilike(pattern),
                    ResourceModel.id.ilike(pattern),
                    ProjectModel.name.ilike(pattern),
                )
            )

        normalized_project_keyword = (project_keyword or "").strip()
        if normalized_project_keyword:
            project_pattern = f"%{normalized_project_keyword}%"
            stmt = stmt.where(ProjectModel.name.ilike(project_pattern))

        stmt = stmt.order_by(ResourceModel.updated_at.desc())

        rows = db.execute(stmt).all()
        result: list[OwnedResource] = []
        for resource, project in rows:
            base = self._to_resource_schema(resource)
            result.append(
                OwnedResource(
                    **base.model_dump(),
                    project_name=project.name,
                )
            )
        return result

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

    def list_chat_sessions(self, db: Session, project_id: str, user_id: str, limit: int = 50) -> list[dict]:
        self.assert_project_member(db, project_id, user_id)
        stmt = (
            select(ChatSessionModel)
            .where(ChatSessionModel.project_id == project_id)
            .order_by(ChatSessionModel.created_at.desc())
            .limit(limit)
        )
        sessions = db.scalars(stmt).all()
        return [
            {
                "id": item.id,
                "project_id": item.project_id,
                "title": item.title,
                "owner_id": item.owner_id,
                "created_at": item.created_at.isoformat(),
            }
            for item in sessions
        ]

    def append_chat_message(self, db: Session, session_id: str, role: str, text: str) -> None:
        session = db.get(ChatSessionModel, session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Chat session not found")
        db.add(ChatMessageModel(session_id=session_id, role=role, text=text))
        db.commit()

    def create_runtime_run(
        self,
        db: Session,
        session: ChatSessionModel,
        user_id: str,
        input_text: str,
        agent_id: str | None,
    ) -> RuntimeRunModel:
        run = RuntimeRunModel(
            project_id=session.project_id,
            session_id=session.id,
            user_id=user_id,
            agent_id=agent_id,
            status="running",
            input_text=input_text,
            started_at=datetime.utcnow(),
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        return run

    def append_runtime_run_event(
        self,
        db: Session,
        run_id: str,
        stage: str,
        status: str,
        message: str,
        payload: dict | None = None,
    ) -> None:
        event = RuntimeRunEventModel(
            run_id=run_id,
            stage=stage,
            status=status,
            message=message,
            payload=payload or {},
        )
        db.add(event)
        db.commit()

    def finish_runtime_run(
        self,
        db: Session,
        run_id: str,
        status: str,
        output_text: str | None = None,
        error: str | None = None,
    ) -> None:
        run = db.get(RuntimeRunModel, run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Run not found")
        run.status = status
        run.output_text = output_text
        run.error = error
        run.finished_at = datetime.utcnow()
        db.commit()

    def list_runtime_runs_for_session(
        self,
        db: Session,
        session_id: str,
        user_id: str,
        limit: int = 100,
    ) -> list[dict]:
        session = self.get_chat_session_for_user(db, session_id, user_id)
        stmt = (
            select(RuntimeRunModel)
            .where(RuntimeRunModel.session_id == session.id)
            .order_by(RuntimeRunModel.created_at.desc())
            .limit(limit)
        )
        runs = db.scalars(stmt).all()
        return [
            {
                "id": item.id,
                "project_id": item.project_id,
                "session_id": item.session_id,
                "user_id": item.user_id,
                "agent_id": item.agent_id,
                "status": item.status,
                "input_text": item.input_text,
                "output_text": item.output_text,
                "error": item.error,
                "started_at": item.started_at.isoformat(),
                "finished_at": item.finished_at.isoformat() if item.finished_at else None,
                "created_at": item.created_at.isoformat(),
            }
            for item in runs
        ]

    def list_runtime_run_events(
        self,
        db: Session,
        run_id: str,
        user_id: str,
        limit: int = 500,
    ) -> list[dict]:
        run = db.get(RuntimeRunModel, run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Run not found")
        self.assert_project_member(db, run.project_id, user_id)

        stmt = (
            select(RuntimeRunEventModel)
            .where(RuntimeRunEventModel.run_id == run_id)
            .order_by(RuntimeRunEventModel.created_at.asc())
            .limit(limit)
        )
        events = db.scalars(stmt).all()
        return [
            {
                "id": item.id,
                "run_id": item.run_id,
                "stage": item.stage,
                "status": item.status,
                "message": item.message,
                "payload": item.payload,
                "created_at": item.created_at.isoformat(),
            }
            for item in events
        ]

    def list_code_execution_audits(
        self,
        db: Session,
        user_id: str,
        project_id: str | None = None,
        limit: int = 100,
    ) -> list[dict]:
        stmt = (
            select(RuntimeRunEventModel, RuntimeRunModel)
            .join(RuntimeRunModel, RuntimeRunModel.id == RuntimeRunEventModel.run_id)
            .where(RuntimeRunEventModel.stage == "code_execution")
            .order_by(RuntimeRunEventModel.created_at.desc())
            .limit(limit)
        )
        if project_id:
            stmt = stmt.where(RuntimeRunModel.project_id == project_id)

        rows = db.execute(stmt).all()
        result: list[dict] = []
        for event, run in rows:
            self.assert_project_member(db, run.project_id, user_id)
            payload = event.payload or {}
            result.append(
                {
                    "run_id": run.id,
                    "project_id": run.project_id,
                    "session_id": run.session_id,
                    "user_id": run.user_id,
                    "agent_id": run.agent_id,
                    "status": event.status,
                    "duration_ms": payload.get("duration_ms"),
                    "input_preview": payload.get("input_preview"),
                    "error": payload.get("error"),
                    "created_at": event.created_at.isoformat(),
                }
            )
        return result

    def get_chat_session_for_user(self, db: Session, session_id: str, user_id: str) -> ChatSessionModel:
        session = db.get(ChatSessionModel, session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Chat session not found")
        self.assert_project_member(db, session.project_id, user_id)
        return session

    def list_chat_messages_for_user(self, db: Session, session_id: str, user_id: str, limit: int = 200) -> list[dict]:
        session = self.get_chat_session_for_user(db, session_id, user_id)
        stmt = (
            select(ChatMessageModel)
            .where(ChatMessageModel.session_id == session.id)
            .order_by(ChatMessageModel.created_at.asc())
            .limit(limit)
        )
        messages = db.scalars(stmt).all()
        return [
            {
                "id": item.id,
                "session_id": item.session_id,
                "role": item.role,
                "text": item.text,
                "created_at": item.created_at.isoformat(),
            }
            for item in messages
        ]

    def get_agent_resource_for_project(self, db: Session, project_id: str, agent_id: str) -> ResourceModel:
        resource = db.get(ResourceModel, agent_id)
        if not resource or resource.project_id != project_id:
            raise HTTPException(status_code=404, detail="Agent resource not found")
        if resource.kind != ResourceKind.AGENT.value:
            raise HTTPException(status_code=400, detail="Provided agent_id is not an agent resource")
        return resource

    def list_tool_resources_for_project(
        self,
        db: Session,
        project_id: str,
        tool_ids: list[str],
        actor: str,
    ) -> list[dict]:
        if not tool_ids:
            return []

        self.assert_project_member(db, project_id, actor)
        result: list[dict] = []
        for tool_id in tool_ids:
            resource = db.get(ResourceModel, tool_id)
            if not resource or resource.project_id != project_id:
                continue
            if resource.kind != ResourceKind.TOOL.value:
                continue

            visibility = Visibility(resource.visibility)
            if visibility == Visibility.PRIVATE and resource.owner_id != actor:
                continue

            config = dict(resource.config or {})
            result.append(
                {
                    "id": resource.id,
                    "name": resource.name,
                    "runtime": config.get("runtime") or "python",
                    "entrypoint": config.get("entrypoint") or "run",
                    "code": config.get("code") or "",
                    "input_schema": config.get("input_schema") or {},
                    "output_schema": config.get("output_schema") or {},
                }
            )
        return result

    def list_mcp_resources_for_project(
        self,
        db: Session,
        project_id: str,
        mcp_ids: list[str],
        actor: str,
    ) -> list[dict]:
        if not mcp_ids:
            return []

        self.assert_project_member(db, project_id, actor)
        result: list[dict] = []
        for mcp_id in mcp_ids:
            resource = db.get(ResourceModel, mcp_id)
            if not resource or resource.project_id != project_id:
                continue
            if resource.kind != ResourceKind.MCP.value:
                continue

            visibility = Visibility(resource.visibility)
            if visibility == Visibility.PRIVATE and resource.owner_id != actor:
                continue

            config = dict(resource.config or {})
            result.append(
                {
                    "id": resource.id,
                    "name": resource.name,
                    "transport": config.get("transport") or "streamable_http",
                    "endpoint_url": config.get("endpoint_url") or "",
                    "command": config.get("command") or "",
                    "args": config.get("args") or [],
                    "headers": config.get("headers") or {},
                    "env": config.get("env") or {},
                    "timeout_seconds": config.get("timeout_seconds") or 8,
                }
            )
        return result

    def _to_project_schema(self, db: Session, project: ProjectModel) -> Project:
        members_stmt = select(ProjectMemberModel.user_id).where(ProjectMemberModel.project_id == project.id)
        members = list(db.scalars(members_stmt).all())
        manager_stmt = select(ProjectMemberPermissionModel.user_id).where(
            and_(
                ProjectMemberPermissionModel.project_id == project.id,
                ProjectMemberPermissionModel.can_add_members.is_(True),
            )
        )
        member_managers = list(db.scalars(manager_stmt).all())

        identifiers = {project.owner_id, *members, *member_managers}
        users_stmt = select(UserModel).where(or_(UserModel.id.in_(identifiers), UserModel.username.in_(identifiers)))
        users = db.scalars(users_stmt).all()
        username_by_id = {item.id: item.username for item in users}
        username_by_username = {item.username: item.username for item in users}

        def to_name(identifier: str) -> str:
            return username_by_id.get(identifier) or username_by_username.get(identifier) or identifier

        return Project(
            id=project.id,
            created_at=project.created_at,
            updated_at=project.updated_at,
            name=project.name,
            description=project.description,
            owner_id=project.owner_id,
            owner_name=to_name(project.owner_id),
            members=members,
            member_names=[to_name(item) for item in members],
            member_managers=member_managers,
            member_manager_names=[to_name(item) for item in member_managers],
        )

    def _get_resource_for_actor(self, db: Session, resource_id: str, actor: str) -> ResourceModel:
        resource = db.get(ResourceModel, resource_id)
        if not resource:
            raise HTTPException(status_code=404, detail="Resource not found")

        project = self.assert_project_member(db, resource.project_id, actor)
        if actor != project.owner_id and actor != resource.owner_id:
            raise HTTPException(status_code=403, detail="No permission to edit resource")
        return resource

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
            provider_profile=(resource.config or {}).get("provider_profile"),
            config=resource.config,
            source="custom",
            template_id=None,
        )

    def _is_member(self, db: Session, project_id: str, user_id: str) -> bool:
        identifiers = self._member_identifiers(db, user_id)
        stmt = select(ProjectMemberModel.id).where(
            and_(ProjectMemberModel.project_id == project_id, ProjectMemberModel.user_id.in_(identifiers))
        )
        return db.scalar(stmt) is not None

    def _can_add_members(self, db: Session, project_id: str, user_id: str) -> bool:
        identifiers = self._member_identifiers(db, user_id)
        stmt = select(ProjectMemberPermissionModel.id).where(
            and_(
                ProjectMemberPermissionModel.project_id == project_id,
                ProjectMemberPermissionModel.user_id.in_(identifiers),
                ProjectMemberPermissionModel.can_add_members.is_(True),
            )
        )
        return db.scalar(stmt) is not None

    def _resolve_user_id(self, db: Session, new_member: str | None, account: str | None) -> str:
        if new_member:
            user = db.get(UserModel, new_member.strip())
            if user:
                return user.id

        candidate = (account or new_member or "").strip().lower()
        if not candidate:
            raise HTTPException(status_code=400, detail="user_id or account is required")

        stmt = select(UserModel).where(or_(UserModel.username == candidate, UserModel.email == candidate))
        user = db.scalar(stmt)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user.id

    def _member_identifiers(self, db: Session, user_id: str) -> list[str]:
        user = db.get(UserModel, user_id)
        if not user:
            return [user_id]
        return [user.id, user.username]

    def _to_user_profile(self, user: UserModel) -> UserProfile:
        return UserProfile(
            id=user.id,
            username=user.username,
            email=user.email,
            display_name=user.display_name,
            is_active=user.is_active,
            created_at=user.created_at,
        )


store = PostgresStore()
