"""Tiny helper to append audit-log entries for family accountability."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.alert import AuditLog


def record(
    db: Session,
    *,
    action: str,
    actor_id: int | None = None,
    family_id: int | None = None,
    entity_type: str | None = None,
    entity_id: int | None = None,
    detail: str | None = None,
    commit: bool = True,
) -> AuditLog:
    entry = AuditLog(
        action=action,
        actor_id=actor_id,
        family_id=family_id,
        entity_type=entity_type,
        entity_id=entity_id,
        detail=detail,
    )
    db.add(entry)
    if commit:
        db.commit()
    return entry
