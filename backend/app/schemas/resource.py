from pydantic import BaseModel, Field

from app.models.enums import ResourceKind, Visibility
from app.schemas.common import TimeStampedModel


class ResourceCreate(BaseModel):
    kind: ResourceKind
    name: str = Field(min_length=2, max_length=120)
    description: str = Field(default="", max_length=1000)
    visibility: Visibility = Visibility.PROJECT
    model_provider: str | None = Field(default=None, max_length=60)
    model_name: str | None = Field(default=None, max_length=120)
    config: dict = Field(default_factory=dict)


class Resource(TimeStampedModel):
    project_id: str
    owner_id: str
    kind: ResourceKind
    name: str
    description: str
    visibility: Visibility
    model_provider: str | None = None
    model_name: str | None = None
    config: dict = Field(default_factory=dict)


class ChatSessionCreate(BaseModel):
    title: str = Field(min_length=1, max_length=120)


class ChatMessageRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    agent_id: str | None = None


class ChatMessageResponse(BaseModel):
    session_id: str
    role: str
    text: str
    run_id: str | None = None


class ChatSessionRecord(BaseModel):
    id: str
    project_id: str
    title: str
    owner_id: str
    created_at: str


class ChatMessageRecord(BaseModel):
    id: str
    session_id: str
    role: str
    text: str
    created_at: str


class RuntimeRunRecord(BaseModel):
    id: str
    project_id: str
    session_id: str
    user_id: str
    agent_id: str | None = None
    status: str
    input_text: str
    output_text: str | None = None
    error: str | None = None
    started_at: str
    finished_at: str | None = None
    created_at: str


class RuntimeRunEventRecord(BaseModel):
    id: str
    run_id: str
    stage: str
    status: str
    message: str
    payload: dict = Field(default_factory=dict)
    created_at: str
