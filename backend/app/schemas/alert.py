from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import AlertChannel, AlertStatus


class AlertRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    vehicle_id: int | None
    document_id: int | None
    title: str
    message: str
    due_date: date | None
    lead_days: int | None
    channel: AlertChannel
    status: AlertStatus
    sent_at: datetime | None
    created_at: datetime


class AuditRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    actor_id: int | None
    action: str
    entity_type: str | None
    entity_id: int | None
    detail: str | None
    created_at: datetime
