from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import FamilyRole


class FamilyCreate(BaseModel):
    name: str


class MemberRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    role: FamilyRole
    user_name: str | None = None
    user_email: str | None = None


class FamilyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    owner_id: int
    members: list[MemberRead] = []


class InviteCreate(BaseModel):
    role: FamilyRole = FamilyRole.member
    max_uses: int = 1
    expires_in_hours: int | None = None


class InviteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    code: str
    role: FamilyRole
    max_uses: int
    uses: int
    expires_at: datetime | None
    revoked: bool


class JoinRequest(BaseModel):
    code: str


class RoleUpdate(BaseModel):
    role: FamilyRole
