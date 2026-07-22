from __future__ import annotations

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserBase(BaseModel):
    email: EmailStr
    name: str = ""
    preferred_language: str = "en"


class UserCreate(UserBase):
    password: str = Field(min_length=6, max_length=128)


class UserRead(UserBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    is_active: bool
    is_superuser: bool
    telegram_chat_id: str | None = None


class UserUpdate(BaseModel):
    name: str | None = None
    preferred_language: str | None = None
    password: str | None = Field(default=None, min_length=6, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead
