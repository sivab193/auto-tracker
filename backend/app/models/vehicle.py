"""Vehicle — the central entity everything else hangs off of."""
from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import FuelType
from app.models.mixins import TimestampMixin
from app.models.types import EnumStr


class Vehicle(Base, TimestampMixin):
    __tablename__ = "vehicles"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    # A vehicle may be shared into a family group (nullable = private to owner).
    family_id: Mapped[int | None] = mapped_column(
        ForeignKey("families.id", ondelete="SET NULL"), index=True, nullable=True
    )

    registration_number: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    nickname: Mapped[str | None] = mapped_column(String(80), nullable=True)
    make: Mapped[str | None] = mapped_column(String(60), nullable=True)
    model: Mapped[str | None] = mapped_column(String(60), nullable=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    color: Mapped[str | None] = mapped_column(String(30), nullable=True)
    vin: Mapped[str | None] = mapped_column(String(40), nullable=True)
    fuel_type: Mapped[FuelType | None] = mapped_column(EnumStr(FuelType), nullable=True)
    engine_number: Mapped[str | None] = mapped_column(String(40), nullable=True)
    odometer: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    owner = relationship("User", back_populates="vehicles")
    family = relationship("Family", back_populates="vehicles")
    documents = relationship(
        "Document", back_populates="vehicle", cascade="all, delete-orphan"
    )
    services = relationship(
        "ServiceRecord", back_populates="vehicle", cascade="all, delete-orphan"
    )
    fuel_logs = relationship("FuelLog", back_populates="vehicle", cascade="all, delete-orphan")
    accidents = relationship(
        "AccidentRecord", back_populates="vehicle", cascade="all, delete-orphan"
    )

    @property
    def display_name(self) -> str:
        if self.nickname:
            return self.nickname
        parts = [str(p) for p in (self.make, self.model) if p]
        return " ".join(parts) or self.registration_number

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Vehicle {self.id} {self.registration_number}>"
