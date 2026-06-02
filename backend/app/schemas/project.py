from pydantic import BaseModel, Field

from app.schemas.common import TimeStampedModel


class ProjectCreate(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    description: str = Field(default="", max_length=500)


class MemberAddRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=120)


class Project(TimeStampedModel):
    name: str
    description: str
    owner_id: str
    members: list[str] = Field(default_factory=list)
