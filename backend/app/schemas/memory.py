from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import EmbeddingStatus, MemoryScope, MemoryType, Visibility


class MemoryCreate(BaseModel):
    memory_scope: MemoryScope
    memory_type: MemoryType
    visibility: Visibility = Visibility.PRIVATE
    project_id: str | None = None
    agent_id: str | None = None
    session_id: str | None = None
    workflow_run_id: str | None = None
    importance_score: float = Field(default=0.5, ge=0.0, le=1.0)
    content: dict = Field(default_factory=dict)
    auto_embedding: bool = True
    retry_on_embedding_failure: bool = True
    embedding_provider: str | None = None
    embedding_model: str | None = None
    embedding_input: str | None = None


class MemoryRecord(BaseModel):
    id: str
    memory_scope: MemoryScope
    memory_type: MemoryType
    visibility: Visibility
    project_id: str | None = None
    agent_id: str | None = None
    session_id: str | None = None
    workflow_run_id: str | None = None
    importance_score: float
    content: dict
    embedding: list[float] | None = None
    embedding_status: EmbeddingStatus
    embedding_provider: str | None = None
    embedding_model: str | None = None
    embedding_error: str | None = None
    created_by: str
    created_at: datetime


class MemorySearchResponse(BaseModel):
    items: list[MemoryRecord]
    total: int


class MemorySemanticSearchRequest(BaseModel):
    query_embedding: list[float] = Field(min_length=1)
    top_k: int = Field(default=10, ge=1, le=200)
    project_id: str | None = None
    memory_scope: MemoryScope | None = None
    memory_type: MemoryType | None = None
    min_importance: float = Field(default=0.0, ge=0.0, le=1.0)
    similarity_weight: float = Field(default=0.7, ge=0.0, le=1.0)


class MemoryScoredRecord(BaseModel):
    record: MemoryRecord
    score: float
    similarity_score: float
    importance_score: float


class MemorySemanticSearchResponse(BaseModel):
    items: list[MemoryScoredRecord]
    total: int


class MemoryRetryResponse(BaseModel):
    processed: int
    succeeded: int
    failed: int
    queued: bool = False
    task_id: str | None = None
    message: str | None = None
