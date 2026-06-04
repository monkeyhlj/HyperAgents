from pydantic import BaseModel, Field

from app.schemas.common import TimeStampedModel


class ProjectCreate(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    description: str = Field(default="", max_length=500)


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=80)
    description: str | None = Field(default=None, max_length=500)


class MemberAddRequest(BaseModel):
    user_id: str | None = Field(default=None, min_length=1, max_length=120)
    account: str | None = Field(default=None, min_length=1, max_length=200)


class MemberManagerGrantRequest(BaseModel):
    user_id: str | None = Field(default=None, min_length=1, max_length=120)
    account: str | None = Field(default=None, min_length=1, max_length=200)


class Project(TimeStampedModel):
    name: str
    description: str
    owner_id: str
    owner_name: str
    members: list[str] = Field(default_factory=list)
    member_names: list[str] = Field(default_factory=list)
    member_managers: list[str] = Field(default_factory=list)
    member_manager_names: list[str] = Field(default_factory=list)
