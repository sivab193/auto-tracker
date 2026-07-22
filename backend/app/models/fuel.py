"""Fuel logs. Mileage/efficiency is derived from consecutive fill-ups."""
from __future__ import annotations

from datetime import date

from sqlalchemy import Boolean, Date, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.mixins import TimestampMixin


class FuelLog(Base, TimestampMixin):
    __tablename__ = "fuel_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    vehicle_id: Mapped[int] = mapped_column(
        ForeignKey("vehicles.id", ondelete="CASCADE"), index=True
    )

    fill_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    odometer: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)  # litres / gallons / kWh
    price_per_unit: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_cost: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)

    # A partial fill breaks the mileage chain until the next full tank.
    is_full_tank: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    station: Mapped[str | None] = mapped_column(String(160), nullable=True)

    # Computed on save: distance since previous full-tank fill / quantity.
    distance: Mapped[int | None] = mapped_column(Integer, nullable=True)
    efficiency: Mapped[float | None] = mapped_column(Float, nullable=True)  # distance per unit

    vehicle = relationship("Vehicle", back_populates="fuel_logs")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<FuelLog {self.id} {self.fill_date} {self.odometer}km>"
