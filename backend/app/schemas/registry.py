from pydantic import BaseModel, Field

from app.schemas.resource import Resource
from app.models.enums import Visibility


class RegistryItemCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str = Field(default="", max_length=1000)
    visibility: Visibility = Visibility.PROJECT
    model_provider: str | None = Field(default=None, max_length=60)
    model_name: str | None = Field(default=None, max_length=120)
    config: dict = Field(default_factory=dict)


class RegistryListResponse(BaseModel):
    items: list[Resource]
    total: int


class MCPProbeRequest(BaseModel):
    project_id: str = Field(min_length=1, max_length=60)
    config: dict = Field(default_factory=dict)


class MCPProbeResponse(BaseModel):
    ok: bool
    transport: str
    endpoint_url: str | None = None
    health_ok: bool = False
    tools_ok: bool = False
    tools: list[str] = Field(default_factory=list)
    error: str | None = None
