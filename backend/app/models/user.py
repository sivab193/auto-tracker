"""User account and Telegram link."""
from __future__ import annotations

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.mixins import TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Telegram linkage: a per-user code the bot uses to bind a chat.
    telegram_chat_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    telegram_link_code: Mapped[str | None] = mapped_column(String(16), index=True, nullable=True)

    preferred_language: Mapped[str] = mapped_column(String(8), default="en", nullable=False)

    vehicles = relationship("Vehicle", back_populates="owner", cascade="all, delete-orphan")
    memberships = relationship(
        "FamilyMembership", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<User {self.id} {self.email}>"
