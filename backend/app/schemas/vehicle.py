from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import FuelType


class VehicleBase(BaseModel):
    registration_number: str = Field(min_length=1, max_length=32)
    nickname: str | None = None
    make: str | None = None
    model: str | None = None
    year: int | None = Field(default=None, ge=1900, le=2100)
    color: str | None = None
    vin: str | None = None
    fuel_type: FuelType | None = None
    engine_number: str | None = None
    odometer: int = 0
    notes: str | None = None


class VehicleCreate(VehicleBase):
    family_id: int | None = None


class VehicleUpdate(BaseModel):
    registration_number: str | None = None
    nickname: str | None = None
    make: str | None = None
    model: str | None = None
    year: int | None = Field(default=None, ge=1900, le=2100)
    color: str | None = None
    vin: str | None = None
    fuel_type: FuelType | None = None
    engine_number: str | None = None
    odometer: int | None = None
    notes: str | None = None
    family_id: int | None = None


class DocumentSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    doc_type: str
    title: str | None
    expiry_date: date | None


class VehicleRead(VehicleBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    owner_id: int
    family_id: int | None
    display_name: str


class VehicleDetail(VehicleRead):
    documents: list[DocumentSummary] = []
