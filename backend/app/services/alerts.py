"""Expiry-alert generation and delivery.

The sweep looks at every current document that has an ``expiry_date`` and, for
each configured lead threshold (e.g. 30/14/7/1 days out), ensures an Alert row
exists for the vehicle's owner. A ``dedupe_key`` prevents duplicates across
repeated sweeps. Newly created / still-pending alerts are then delivered.
"""
from __future__ import annotations

import logging
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models.alert import Alert
from app.models.document import Document
from app.models.enums import AlertChannel, AlertStatus
from app.models.mixins import utcnow
from app.models.user import User
from app.models.vehicle import Vehicle
from app.services.notifications import notify

logger = logging.getLogger("autotracker.alerts")


def _dedupe_key(document_id: int, threshold: int) -> str:
    return f"doc:{document_id}:lead:{threshold}"


def generate_alerts(db: Session, today: date | None = None) -> list[Alert]:
    """Create any missing alert rows. Returns the list of newly created ones."""
    today = today or date.today()
    lead_days = settings.alert_lead_day_list or [30, 14, 7, 1]
    max_lead = max(lead_days)

    horizon = today + timedelta(days=max_lead)
    stmt = (
        select(Document, Vehicle)
        .join(Vehicle, Document.vehicle_id == Vehicle.id)
        .where(
            Document.is_current.is_(True),
            Document.expiry_date.is_not(None),
            Document.expiry_date <= horizon,
        )
    )
    created: list[Alert] = []
    for doc, vehicle in db.execute(stmt).all():
        days_left = (doc.expiry_date - today).days
        # Choose the tightest threshold that has been reached.
        reached = [t for t in lead_days if days_left <= t]
        if not reached:
            continue
        threshold = min(reached)
        key = _dedupe_key(doc.id, threshold)
        exists = db.scalar(select(Alert.id).where(Alert.dedupe_key == key))
        if exists:
            continue

        label = doc.title or doc.doc_type.value.replace("_", " ").title()
        if days_left < 0:
            msg = f"{label} for {vehicle.display_name} expired {abs(days_left)} day(s) ago."
        elif days_left == 0:
            msg = f"{label} for {vehicle.display_name} expires today."
        else:
            on = doc.expiry_date.isoformat()
            msg = f"{label} for {vehicle.display_name} expires in {days_left} day(s) (on {on})."

        alert = Alert(
            user_id=vehicle.owner_id,
            vehicle_id=vehicle.id,
            document_id=doc.id,
            title=f"{label} expiring",
            message=msg,
            due_date=doc.expiry_date,
            lead_days=threshold,
            channel=AlertChannel.in_app,
            status=AlertStatus.pending,
            dedupe_key=key,
        )
        db.add(alert)
        created.append(alert)

    if created:
        db.commit()
        for a in created:
            db.refresh(a)
    return created


def deliver_pending(db: Session) -> int:
    """Deliver pending alerts to their channel (Telegram if the user linked one)."""
    pending = db.scalars(
        select(Alert).where(Alert.status == AlertStatus.pending)
    ).all()
    delivered = 0
    for alert in pending:
        user = db.get(User, alert.user_id)
        chat_id = user.telegram_chat_id if user else None
        channel = AlertChannel.telegram if chat_id else AlertChannel.in_app
        ok = notify(channel, chat_id=chat_id, text=f"🔔 {alert.title}\n{alert.message}")
        if ok:
            alert.status = AlertStatus.sent
            alert.channel = channel
            alert.sent_at = utcnow()
            delivered += 1
    if delivered:
        db.commit()
    return delivered


def run_sweep(db: Session) -> dict[str, int]:
    created = generate_alerts(db)
    delivered = deliver_pending(db)
    logger.info("alert sweep: %d created, %d delivered", len(created), delivered)
    return {"created": len(created), "delivered": delivered}
