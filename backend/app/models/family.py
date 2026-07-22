"""Family groups, memberships and invite codes for shared vehicle access."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import FamilyRole
from app.models.mixins import TimestampMixin
from app.models.types import EnumStr


class Family(Base, TimestampMixin):
    __tablename__ = "families"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))

    memberships = relationship(
        "FamilyMembership", back_populates="family", cascade="all, delete-orphan"
    )
    invites = relationship(
        "FamilyInvite", back_populates="family", cascade="all, delete-orphan"
    )
    vehicles = relationship("Vehicle", back_populates="family")


class FamilyMembership(Base, TimestampMixin):
    __tablename__ = "family_memberships"
    __table_args__ = (UniqueConstraint("family_id", "user_id", name="uq_family_user"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    family_id: Mapped[int] = mapped_column(
        ForeignKey("families.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    role: Mapped[FamilyRole] = mapped_column(EnumStr(FamilyRole), default=FamilyRole.member, nullable=False)

    family = relationship("Family", back_populates="memberships")
    user = relationship("User", back_populates="memberships")


class FamilyInvite(Base, TimestampMixin):
    __tablename__ = "family_invites"

    id: Mapped[int] = mapped_column(primary_key=True)
    family_id: Mapped[int] = mapped_column(
        ForeignKey("families.id", ondelete="CASCADE"), index=True
    )
    code: Mapped[str] = mapped_column(String(12), unique=True, index=True, nullable=False)
    role: Mapped[FamilyRole] = mapped_column(EnumStr(FamilyRole), default=FamilyRole.member, nullable=False)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    max_uses: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    uses: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    family = relationship("Family", back_populates="invites")

    @property
    def is_usable(self) -> bool:
        from app.models.mixins import utcnow

        if self.revoked or self.uses >= self.max_uses:
            return False
        if self.expires_at is not None and self.expires_at < utcnow():
            return False
        return True
