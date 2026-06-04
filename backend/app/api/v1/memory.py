from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id, get_db
from app.db.session import SessionLocal
from app.models.enums import MemoryScope, MemoryType
from app.schemas.memory import (
    MemoryCreate,
    MemoryRecord,
    MemoryRetryResponse,
    MemorySearchResponse,
    MemorySemanticSearchRequest,
    MemorySemanticSearchResponse,
)
from app.services.memory_store import memory_store
from app.workers.dispatcher import enqueue_embedding_retry


router = APIRouter()


def _run_background_embedding_retry(limit: int = 5) -> None:
    with SessionLocal() as session:
        memory_store.process_pending_embedding_jobs(session, limit=limit)


@router.post("", response_model=MemoryRecord)
def create_memory(
    payload: MemoryCreate,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> MemoryRecord:
    memory = memory_store.create_memory(db, payload, user_id)
    if payload.auto_embedding and payload.retry_on_embedding_failure and memory.embedding_status.value == "failed":
        dispatch = enqueue_embedding_retry(limit=1)
        if not dispatch.queued:
            background_tasks.add_task(_run_background_embedding_retry, 1)
    return memory


@router.get("", response_model=MemorySearchResponse)
def search_memory(
    project_id: str | None = Query(default=None),
    memory_scope: MemoryScope | None = Query(default=None),
    memory_type: MemoryType | None = Query(default=None),
    min_importance: float = Query(default=0.0, ge=0.0, le=1.0),
    limit: int = Query(default=20, ge=1, le=200),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> MemorySearchResponse:
    items = memory_store.search_memories(
        db=db,
        user_id=user_id,
        project_id=project_id,
        memory_scope=memory_scope,
        memory_type=memory_type,
        min_importance=min_importance,
        limit=limit,
    )
    return MemorySearchResponse(items=items, total=len(items))


@router.post("/semantic-search", response_model=MemorySemanticSearchResponse)
def semantic_search_memory(
    payload: MemorySemanticSearchRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> MemorySemanticSearchResponse:
    items = memory_store.semantic_search_memories(
        db=db,
        user_id=user_id,
        query_embedding=payload.query_embedding,
        top_k=payload.top_k,
        project_id=payload.project_id,
        memory_scope=payload.memory_scope,
        memory_type=payload.memory_type,
        min_importance=payload.min_importance,
        similarity_weight=payload.similarity_weight,
    )
    return MemorySemanticSearchResponse(items=items, total=len(items))


@router.post("/retry-embeddings", response_model=MemoryRetryResponse)
def retry_embeddings(
    limit: int = Query(default=20, ge=1, le=200),
    enqueue: bool = Query(default=False),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> MemoryRetryResponse:
    _ = user_id
    if enqueue:
        dispatch = enqueue_embedding_retry(limit=limit)
        if dispatch.queued:
            return MemoryRetryResponse(
                processed=0,
                succeeded=0,
                failed=0,
                queued=True,
                task_id=dispatch.task_id,
                message="Embedding retry task enqueued",
            )
    result = memory_store.process_pending_embedding_jobs(db, limit=limit)
    return MemoryRetryResponse(**result, queued=False, message="Embedding retry executed in API process")
