from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict

from app.models.enums import ServiceType


class ServiceBase(BaseModel):
    service_type: ServiceType = ServiceType.routine
    service_date: date
    odometer: int | None = None
    cost: float = 0.0
    currency: str = "USD"
    vendor: str | None = None
    description: str | None = None
    next_service_date: date | None = None
    next_service_odometer: int | None = None


class ServiceCreate(ServiceBase):
    pass


class ServiceUpdate(BaseModel):
    service_type: ServiceType | None = None
    service_date: date | None = None
    odometer: int | None = None
    cost: float | None = None
    currency: str | None = None
    vendor: str | None = None
    description: str | None = None
    next_service_date: date | None = None
    next_service_odometer: int | None = None


class ServiceRead(ServiceBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    vehicle_id: int


class AccidentBase(BaseModel):
    accident_date: date
    location: str | None = None
    description: str | None = None
    claim_number: str | None = None
    claim_amount: float | None = None
    at_fault: bool | None = None


class AccidentCreate(AccidentBase):
    pass


class AccidentRead(AccidentBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    vehicle_id: int
