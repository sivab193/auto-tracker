from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class FuelBase(BaseModel):
    fill_date: date
    odometer: int = Field(ge=0)
    quantity: float = Field(gt=0)
    price_per_unit: float | None = None
    total_cost: float = 0.0
    currency: str = "USD"
    is_full_tank: bool = True
    station: str | None = None


class FuelCreate(FuelBase):
    pass


class FuelUpdate(BaseModel):
    fill_date: date | None = None
    odometer: int | None = None
    quantity: float | None = None
    price_per_unit: float | None = None
    total_cost: float | None = None
    currency: str | None = None
    is_full_tank: bool | None = None
    station: str | None = None


class FuelRead(FuelBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    vehicle_id: int
    distance: int | None = None
    efficiency: float | None = None
