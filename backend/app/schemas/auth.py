from datetime import datetime

from pydantic import BaseModel, Field


class UserRegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=60)
    password: str = Field(min_length=6, max_length=128)
    email: str | None = Field(default=None, max_length=200)
    display_name: str | None = Field(default=None, max_length=120)


class UserLoginRequest(BaseModel):
    account: str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=1, max_length=128)


class UserProfile(BaseModel):
    id: str
    username: str
    email: str | None = None
    display_name: str
    is_active: bool
    created_at: datetime


class UserSearchItem(BaseModel):
    id: str
    username: str
    display_name: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserProfile
