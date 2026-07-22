"""Cost & efficiency analytics for the dashboard and per-vehicle views."""
from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_accessible_vehicle, get_current_user
from app.database import get_db
from app.models.alert import Alert
from app.models.document import Document
from app.models.enums import AlertStatus
from app.models.family import FamilyMembership
from app.models.fuel import FuelLog
from app.models.service import ServiceRecord
from app.models.user import User
from app.models.vehicle import Vehicle
from app.schemas.analytics import DashboardSummary, MonthlyCost, VehicleAnalytics

router = APIRouter(prefix="/analytics", tags=["analytics"])


def _accessible_vehicle_ids(db: Session, user: User) -> list[int]:
    fam_ids = db.scalars(
        select(FamilyMembership.family_id).where(FamilyMembership.user_id == user.id)
    ).all()
    conditions = [Vehicle.owner_id == user.id]
    if fam_ids:
        conditions.append(Vehicle.family_id.in_(fam_ids))
    return list(db.scalars(select(Vehicle.id).where(or_(*conditions))).all())


@router.get("/dashboard", response_model=DashboardSummary)
def dashboard(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DashboardSummary:
    vehicle_ids = _accessible_vehicle_ids(db, user)
    summary = DashboardSummary(vehicles=len(vehicle_ids))
    if not vehicle_ids:
        return summary

    soon = date.today() + timedelta(days=30)
    docs = db.scalars(
        select(Document).where(
            Document.vehicle_id.in_(vehicle_ids), Document.is_current.is_(True)
        )
    ).all()
    summary.documents = len(docs)
    summary.expiring_soon = sum(
        1 for d in docs if d.expiry_date is not None and d.expiry_date <= soon
    )

    summary.pending_alerts = len(
        db.scalars(
            select(Alert.id).where(
                Alert.user_id == user.id, Alert.status == AlertStatus.pending
            )
        ).all()
    )

    fuel_cost = sum(
        f.total_cost or 0.0
        for f in db.scalars(select(FuelLog).where(FuelLog.vehicle_id.in_(vehicle_ids))).all()
    )
    svc_cost = sum(
        s.cost or 0.0
        for s in db.scalars(select(ServiceRecord).where(ServiceRecord.vehicle_id.in_(vehicle_ids))).all()
    )
    summary.total_spend = round(fuel_cost + svc_cost, 2)
    return summary


@router.get("/vehicles/{vehicle_id}", response_model=VehicleAnalytics)
def vehicle_analytics(
    db: Session = Depends(get_db),
    vehicle: Vehicle = Depends(get_accessible_vehicle),
) -> VehicleAnalytics:
    fuel = db.scalars(select(FuelLog).where(FuelLog.vehicle_id == vehicle.id)).all()
    services = db.scalars(
        select(ServiceRecord).where(ServiceRecord.vehicle_id == vehicle.id)
    ).all()

    total_fuel = round(sum(f.total_cost or 0.0 for f in fuel), 2)
    total_service = round(sum(s.cost or 0.0 for s in services), 2)

    effs = [f.efficiency for f in fuel if f.efficiency]
    distance = sum(f.distance or 0 for f in fuel if f.efficiency)

    monthly: dict[str, MonthlyCost] = defaultdict(lambda: MonthlyCost(month="", fuel=0.0, service=0.0, total=0.0))
    for f in fuel:
        key = f.fill_date.strftime("%Y-%m")
        m = monthly[key]
        m.month = key
        m.fuel = round(m.fuel + (f.total_cost or 0.0), 2)
    for s in services:
        key = s.service_date.strftime("%Y-%m")
        m = monthly[key]
        m.month = key
        m.service = round(m.service + (s.cost or 0.0), 2)
    for m in monthly.values():
        m.total = round(m.fuel + m.service, 2)

    return VehicleAnalytics(
        vehicle_id=vehicle.id,
        total_fuel_cost=total_fuel,
        total_service_cost=total_service,
        total_cost=round(total_fuel + total_service, 2),
        fuel_events=len(fuel),
        service_events=len(services),
        avg_efficiency=round(sum(effs) / len(effs), 2) if effs else None,
        best_efficiency=round(max(effs), 2) if effs else None,
        worst_efficiency=round(min(effs), 2) if effs else None,
        cost_per_distance=round(total_fuel / distance, 3) if distance else None,
        distance_tracked=distance,
        monthly=sorted(monthly.values(), key=lambda x: x.month),
    )
