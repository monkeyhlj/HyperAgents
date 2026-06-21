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
    provider_profile: str | None = Field(default=None, max_length=60)
    config: dict = Field(default_factory=dict)


class ResourceUpdate(BaseModel):
    project_id: str | None = Field(default=None, max_length=60)
    name: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=1000)
    visibility: Visibility | None = None
    model_provider: str | None = Field(default=None, max_length=60)
    model_name: str | None = Field(default=None, max_length=120)
    provider_profile: str | None = Field(default=None, max_length=60)
    config: dict | None = None


class Resource(TimeStampedModel):
    project_id: str
    owner_id: str
    kind: ResourceKind
    name: str
    description: str
    visibility: Visibility
    model_provider: str | None = None
    model_name: str | None = None
    provider_profile: str | None = None
    config: dict = Field(default_factory=dict)
    source: str = "custom"
    template_id: str | None = None


class OwnedResource(Resource):
    project_name: str


class ResourceTemplate(BaseModel):
    template_id: str
    kind: ResourceKind
    name: str
    description: str
    visibility: Visibility
    model_provider: str | None = None
    model_name: str | None = None
    provider_profile: str | None = None
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
    used_tools: list[str] = []
    used_mcps: list[dict[str, str]] = []


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


class CodeExecutionAuditRecord(BaseModel):
    run_id: str
    project_id: str
    session_id: str
    user_id: str
    agent_id: str | None = None
    status: str
    duration_ms: int | None = None
    input_preview: str | None = None
    error: str | None = None
    created_at: str


class ResourcePreviewChatRequest(BaseModel):
    project_id: str = Field(min_length=1, max_length=36)
    text: str = Field(min_length=1, max_length=4000)
    run_mode: str | None = Field(default=None, max_length=30)
    model_provider: str | None = Field(default=None, max_length=60)
    model_name: str | None = Field(default=None, max_length=120)
    provider_profile: str | None = Field(default=None, max_length=60)
    system_prompt: str | None = Field(default=None, max_length=8000)
    custom_code: str | None = None
    config: dict = Field(default_factory=dict)


class ResourcePreviewChatResponse(BaseModel):
    text: str
