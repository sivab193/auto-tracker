"""Service records and accident history."""
from __future__ import annotations

from datetime import date

from sqlalchemy import Date, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import ServiceType
from app.models.mixins import TimestampMixin
from app.models.types import EnumStr


class ServiceRecord(Base, TimestampMixin):
    __tablename__ = "service_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    vehicle_id: Mapped[int] = mapped_column(
        ForeignKey("vehicles.id", ondelete="CASCADE"), index=True
    )

    service_type: Mapped[ServiceType] = mapped_column(
        EnumStr(ServiceType), default=ServiceType.routine, nullable=False
    )
    service_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    odometer: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    vendor: Mapped[str | None] = mapped_column(String(160), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Optional reminder for the next service.
    next_service_date: Mapped[date | None] = mapped_column(Date, index=True, nullable=True)
    next_service_odometer: Mapped[int | None] = mapped_column(Integer, nullable=True)

    vehicle = relationship("Vehicle", back_populates="services")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<ServiceRecord {self.id} {self.service_type} {self.service_date}>"


class AccidentRecord(Base, TimestampMixin):
    __tablename__ = "accident_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    vehicle_id: Mapped[int] = mapped_column(
        ForeignKey("vehicles.id", ondelete="CASCADE"), index=True
    )

    accident_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    location: Mapped[str | None] = mapped_column(String(200), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    claim_number: Mapped[str | None] = mapped_column(String(120), nullable=True)
    claim_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    at_fault: Mapped[bool | None] = mapped_column(default=None, nullable=True)

    vehicle = relationship("Vehicle", back_populates="accidents")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<AccidentRecord {self.id} {self.accident_date}>"
