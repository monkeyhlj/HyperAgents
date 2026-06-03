from datetime import datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import and_, desc, or_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import (
    MemoryEmbeddingJobModel,
    MemoryRecordModel,
    ProjectMemberModel,
    ProjectModel,
)
from app.models.enums import EmbeddingStatus, MemoryScope, MemoryType, Visibility
from app.runtime.embeddings import EmbeddingRequest, embedding_factory, serialize_memory_content
from app.schemas.memory import MemoryCreate, MemoryRecord, MemoryScoredRecord


class MemoryStore:
    def create_memory(self, db: Session, payload: MemoryCreate, user_id: str) -> MemoryRecord:
        self._validate_scope_access(db, payload, user_id)

        generated_embedding: list[float] | None = None
        embedding_status = EmbeddingStatus.SKIPPED
        embedding_provider: str | None = None
        embedding_model: str | None = None
        embedding_error: str | None = None

        if payload.auto_embedding:
            embedding_status = EmbeddingStatus.PENDING
            provider_name = payload.embedding_provider or settings.embedding_provider
            model_name = embedding_factory.resolve_model(provider_name, payload.embedding_model)
            embedding_provider = provider_name
            embedding_model = model_name
            embedding_input = payload.embedding_input or serialize_memory_content(payload.content)

            try:
                provider = embedding_factory.get_provider(provider_name)
                generated_embedding = provider.generate_embedding(
                    EmbeddingRequest(
                        text=embedding_input,
                        provider=provider_name,
                        model=model_name,
                    )
                )
                if len(generated_embedding) != settings.memory_embedding_dimensions:
                    raise ValueError(
                        f"embedding dimension must be {settings.memory_embedding_dimensions}, "
                        f"got {len(generated_embedding)}"
                    )
                embedding_status = EmbeddingStatus.SUCCEEDED
            except Exception as exc:
                embedding_status = EmbeddingStatus.FAILED
                embedding_error = str(exc)

        record = MemoryRecordModel(
            project_id=payload.project_id,
            agent_id=payload.agent_id,
            session_id=payload.session_id,
            workflow_run_id=payload.workflow_run_id,
            memory_scope=payload.memory_scope.value,
            memory_type=payload.memory_type.value,
            visibility=payload.visibility.value,
            importance_score=payload.importance_score,
            content=payload.content,
            embedding=generated_embedding,
            embedding_status=embedding_status.value,
            embedding_provider=embedding_provider,
            embedding_model=embedding_model,
            embedding_error=embedding_error,
            last_embedding_attempt_at=datetime.utcnow() if payload.auto_embedding else None,
            created_by=user_id,
        )
        db.add(record)
        db.commit()
        db.refresh(record)

        if (
            payload.auto_embedding
            and payload.retry_on_embedding_failure
            and embedding_status == EmbeddingStatus.FAILED
        ):
            self._enqueue_retry_job(db, record.id)

        return self._to_schema(record)

    def search_memories(
        self,
        db: Session,
        user_id: str,
        project_id: str | None,
        memory_scope: MemoryScope | None,
        memory_type: MemoryType | None,
        min_importance: float,
        limit: int,
    ) -> list[MemoryRecord]:
        stmt = select(MemoryRecordModel).where(MemoryRecordModel.importance_score >= min_importance)

        if project_id:
            if not self._is_project_member(db, project_id, user_id):
                raise HTTPException(status_code=403, detail="No access to project")
            stmt = stmt.where(MemoryRecordModel.project_id == project_id)

        if memory_scope is not None:
            stmt = stmt.where(MemoryRecordModel.memory_scope == memory_scope.value)
        if memory_type is not None:
            stmt = stmt.where(MemoryRecordModel.memory_type == memory_type.value)

        visibility_filter = or_(
            MemoryRecordModel.visibility == Visibility.PUBLIC.value,
            MemoryRecordModel.created_by == user_id,
        )

        if project_id:
            visibility_filter = or_(
                visibility_filter,
                and_(
                    MemoryRecordModel.project_id == project_id,
                    MemoryRecordModel.visibility == Visibility.PROJECT.value,
                ),
            )

        stmt = stmt.where(visibility_filter).order_by(desc(MemoryRecordModel.importance_score)).limit(limit)
        return [self._to_schema(item) for item in db.scalars(stmt).all()]

    def semantic_search_memories(
        self,
        db: Session,
        user_id: str,
        query_embedding: list[float],
        top_k: int,
        project_id: str | None,
        memory_scope: MemoryScope | None,
        memory_type: MemoryType | None,
        min_importance: float,
        similarity_weight: float,
    ) -> list[MemoryScoredRecord]:
        if len(query_embedding) != settings.memory_embedding_dimensions:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"query_embedding dimension must be {settings.memory_embedding_dimensions}, "
                    f"got {len(query_embedding)}"
                ),
            )

        filters = [
            MemoryRecordModel.importance_score >= min_importance,
            MemoryRecordModel.embedding.is_not(None),
        ]

        if project_id:
            if not self._is_project_member(db, project_id, user_id):
                raise HTTPException(status_code=403, detail="No access to project")
            filters.append(MemoryRecordModel.project_id == project_id)

        if memory_scope is not None:
            filters.append(MemoryRecordModel.memory_scope == memory_scope.value)
        if memory_type is not None:
            filters.append(MemoryRecordModel.memory_type == memory_type.value)

        visibility_filter = or_(
            MemoryRecordModel.visibility == Visibility.PUBLIC.value,
            MemoryRecordModel.created_by == user_id,
        )
        if project_id:
            visibility_filter = or_(
                visibility_filter,
                and_(
                    MemoryRecordModel.project_id == project_id,
                    MemoryRecordModel.visibility == Visibility.PROJECT.value,
                ),
            )

        distance = MemoryRecordModel.embedding.cosine_distance(query_embedding)
        similarity_score_expr = 1 - distance
        hybrid_score_expr = (
            similarity_weight * similarity_score_expr
            + (1 - similarity_weight) * MemoryRecordModel.importance_score
        )

        stmt = (
            select(
                MemoryRecordModel,
                similarity_score_expr.label("similarity_score"),
                hybrid_score_expr.label("hybrid_score"),
            )
            .where(*filters)
            .where(visibility_filter)
            .order_by(hybrid_score_expr.desc())
            .limit(top_k)
        )
        rows = db.execute(stmt).all()

        result: list[MemoryScoredRecord] = []
        for item, similarity_score, hybrid_score in rows:
            result.append(
                MemoryScoredRecord(
                    record=self._to_schema(item),
                    score=float(hybrid_score or 0.0),
                    similarity_score=float(similarity_score or 0.0),
                    importance_score=float(item.importance_score),
                )
            )
        return result

    def process_pending_embedding_jobs(self, db: Session, limit: int = 20) -> dict[str, int]:
        now = datetime.utcnow()
        stmt = (
            select(MemoryEmbeddingJobModel)
            .where(
                MemoryEmbeddingJobModel.status == EmbeddingStatus.PENDING.value,
                MemoryEmbeddingJobModel.next_retry_at <= now,
            )
            .order_by(MemoryEmbeddingJobModel.created_at.asc())
            .limit(limit)
        )
        jobs = db.scalars(stmt).all()

        succeeded = 0
        failed = 0
        for job in jobs:
            memory_record = db.get(MemoryRecordModel, job.memory_id)
            if not memory_record:
                job.status = EmbeddingStatus.FAILED.value
                job.last_error = "memory record not found"
                failed += 1
                continue

            try:
                embedding_input = serialize_memory_content(memory_record.content)
                provider_name = memory_record.embedding_provider or settings.embedding_provider
                model_name = memory_record.embedding_model or embedding_factory.resolve_model(provider_name, None)
                provider = embedding_factory.get_provider(provider_name)
                vector = provider.generate_embedding(
                    EmbeddingRequest(text=embedding_input, provider=provider_name, model=model_name)
                )
                if len(vector) != settings.memory_embedding_dimensions:
                    raise ValueError(
                        f"embedding dimension must be {settings.memory_embedding_dimensions}, got {len(vector)}"
                    )

                memory_record.embedding = vector
                memory_record.embedding_status = EmbeddingStatus.SUCCEEDED.value
                memory_record.embedding_error = None
                memory_record.last_embedding_attempt_at = datetime.utcnow()

                job.status = EmbeddingStatus.SUCCEEDED.value
                job.attempts += 1
                job.last_error = None
                succeeded += 1
            except Exception as exc:
                job.attempts += 1
                memory_record.embedding_status = EmbeddingStatus.FAILED.value
                memory_record.embedding_error = str(exc)
                memory_record.last_embedding_attempt_at = datetime.utcnow()
                job.last_error = str(exc)

                if job.attempts >= job.max_attempts:
                    job.status = EmbeddingStatus.FAILED.value
                else:
                    backoff = settings.embedding_retry_backoff_seconds * (2 ** max(job.attempts - 1, 0))
                    job.next_retry_at = datetime.utcnow() + timedelta(seconds=backoff)
                    job.status = EmbeddingStatus.PENDING.value
                failed += 1

        db.commit()
        return {
            "processed": len(jobs),
            "succeeded": succeeded,
            "failed": failed,
        }

    def _validate_scope_access(self, db: Session, payload: MemoryCreate, user_id: str) -> None:
        scope = payload.memory_scope
        if scope in {MemoryScope.PROJECT, MemoryScope.AGENT, MemoryScope.CONVERSATION, MemoryScope.EXECUTION}:
            if not payload.project_id:
                raise HTTPException(status_code=400, detail="project_id is required for this memory scope")
            if not self._is_project_member(db, payload.project_id, user_id):
                raise HTTPException(status_code=403, detail="No access to project")

        if scope == MemoryScope.CONVERSATION and not payload.session_id:
            raise HTTPException(status_code=400, detail="session_id is required for conversation scope")
        if scope == MemoryScope.AGENT and not payload.agent_id:
            raise HTTPException(status_code=400, detail="agent_id is required for agent scope")
        if scope == MemoryScope.EXECUTION and not payload.workflow_run_id:
            raise HTTPException(status_code=400, detail="workflow_run_id is required for execution scope")

    def _is_project_member(self, db: Session, project_id: str, user_id: str) -> bool:
        project = db.get(ProjectModel, project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        if project.owner_id == user_id:
            return True
        stmt = select(ProjectMemberModel.id).where(
            and_(ProjectMemberModel.project_id == project_id, ProjectMemberModel.user_id == user_id)
        )
        return db.scalar(stmt) is not None

    def _to_schema(self, record: MemoryRecordModel) -> MemoryRecord:
        return MemoryRecord(
            id=record.id,
            memory_scope=MemoryScope(record.memory_scope),
            memory_type=MemoryType(record.memory_type),
            visibility=Visibility(record.visibility),
            project_id=record.project_id,
            agent_id=record.agent_id,
            session_id=record.session_id,
            workflow_run_id=record.workflow_run_id,
            importance_score=record.importance_score,
            content=record.content,
            embedding=record.embedding,
            embedding_status=EmbeddingStatus(record.embedding_status),
            embedding_provider=record.embedding_provider,
            embedding_model=record.embedding_model,
            embedding_error=record.embedding_error,
            created_by=record.created_by,
            created_at=record.created_at,
        )

    def _enqueue_retry_job(self, db: Session, memory_id: str) -> None:
        job = MemoryEmbeddingJobModel(
            memory_id=memory_id,
            status=EmbeddingStatus.PENDING.value,
            attempts=0,
            max_attempts=settings.embedding_retry_max_attempts,
            next_retry_at=datetime.utcnow() + timedelta(seconds=settings.embedding_retry_backoff_seconds),
        )
        db.add(job)
        db.commit()


memory_store = MemoryStore()
