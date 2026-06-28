from datetime import datetime

from pydantic import BaseModel, Field


class ProviderConnectionBase(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    provider_type: str = Field(default="openai_compatible", max_length=60)
    base_url: str = Field(min_length=8, max_length=500)
    default_model: str | None = Field(default=None, max_length=120)


class ProviderConnectionCreate(ProviderConnectionBase):
    api_key: str = Field(default="", max_length=4000)
    model_list_cache: list[str] = Field(default_factory=list)


class ProviderConnectionUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    provider_type: str | None = Field(default=None, max_length=60)
    base_url: str | None = Field(default=None, min_length=8, max_length=500)
    api_key: str | None = Field(default=None, max_length=4000)
    default_model: str | None = Field(default=None, max_length=120)
    model_list_cache: list[str] | None = None


class ProviderConnectionRecord(ProviderConnectionBase):
    id: str
    project_id: str
    owner_id: str
    api_key_masked: str
    model_list_cache: list[str] = Field(default_factory=list)
    last_test_status: str | None = None
    last_test_error: str | None = None
    last_test_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class ProviderModelsProbeRequest(BaseModel):
    provider_type: str = Field(default="openai_compatible", max_length=60)
    base_url: str = Field(min_length=8, max_length=500)
    api_key: str = Field(default="", max_length=4000)


class ProviderModelsProbeResponse(BaseModel):
    ok: bool
    models: list[str] = Field(default_factory=list)
    error: str | None = None


class ProviderConnectionTestRequest(ProviderModelsProbeRequest):
    model_name: str = Field(min_length=1, max_length=120)
    text: str = Field(default="ping", max_length=1000)



class SavedProviderConnectionTestRequest(BaseModel):
    model_name: str = Field(min_length=1, max_length=120)
    text: str = Field(default="ping", max_length=1000)

class ProviderConnectionTestResponse(BaseModel):
    ok: bool
    model_name: str
    output_preview: str = ""
    error: str | None = None
