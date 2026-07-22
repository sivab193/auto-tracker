"""In-app alerts: list, acknowledge, dismiss, and a manual sweep trigger."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models.alert import Alert
from app.models.enums import AlertStatus
from app.models.user import User
from app.schemas.alert import AlertRead
from app.services.alerts import run_sweep

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=list[AlertRead])
def list_alerts(
    status_filter: AlertStatus | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[AlertRead]:
    stmt = select(Alert).where(Alert.user_id == user.id)
    if status_filter:
        stmt = stmt.where(Alert.status == status_filter)
    stmt = stmt.order_by(Alert.due_date.is_(None), Alert.due_date, Alert.created_at.desc())
    return [AlertRead.model_validate(a) for a in db.scalars(stmt).all()]


def _load_own_alert(db: Session, user: User, alert_id: int) -> Alert:
    alert = db.get(Alert, alert_id)
    if not alert or alert.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Alert not found")
    return alert


@router.post("/{alert_id}/acknowledge", response_model=AlertRead)
def acknowledge(
    alert_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AlertRead:
    alert = _load_own_alert(db, user, alert_id)
    alert.status = AlertStatus.acknowledged
    db.commit()
    db.refresh(alert)
    return AlertRead.model_validate(alert)


@router.post("/{alert_id}/dismiss", response_model=AlertRead)
def dismiss(
    alert_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AlertRead:
    alert = _load_own_alert(db, user, alert_id)
    alert.status = AlertStatus.dismissed
    db.commit()
    db.refresh(alert)
    return AlertRead.model_validate(alert)


@router.post("/sweep")
def trigger_sweep(
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> dict:
    """Manually run the expiry sweep (also runs daily via the scheduler)."""
    return run_sweep(db)
