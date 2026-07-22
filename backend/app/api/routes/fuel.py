"""Fuel logs with automatic mileage/efficiency calculation."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_accessible_vehicle, get_current_user, require_vehicle_write
from app.database import get_db
from app.models.fuel import FuelLog
from app.models.user import User
from app.models.vehicle import Vehicle
from app.schemas.fuel import FuelCreate, FuelRead, FuelUpdate
from app.services import audit
from app.services.fuel_stats import recompute

router = APIRouter(tags=["fuel"])


@router.get("/vehicles/{vehicle_id}/fuel", response_model=list[FuelRead])
def list_fuel(
    db: Session = Depends(get_db),
    vehicle: Vehicle = Depends(get_accessible_vehicle),
) -> list[FuelRead]:
    rows = db.scalars(
        select(FuelLog)
        .where(FuelLog.vehicle_id == vehicle.id)
        .order_by(FuelLog.fill_date.desc(), FuelLog.odometer.desc())
    ).all()
    return [FuelRead.model_validate(r) for r in rows]


@router.post(
    "/vehicles/{vehicle_id}/fuel",
    response_model=FuelRead,
    status_code=status.HTTP_201_CREATED,
)
def create_fuel(
    body: FuelCreate,
    db: Session = Depends(get_db),
    vehicle: Vehicle = Depends(require_vehicle_write),
    user: User = Depends(get_current_user),
) -> FuelRead:
    data = body.model_dump()
    # Derive total cost if only unit price was provided.
    if not data.get("total_cost") and data.get("price_per_unit"):
        data["total_cost"] = round(data["price_per_unit"] * data["quantity"], 2)
    log = FuelLog(vehicle_id=vehicle.id, **data)
    db.add(log)
    if log.odometer and log.odometer > vehicle.odometer:
        vehicle.odometer = log.odometer
    db.commit()
    recompute(db, vehicle.id)
    db.refresh(log)
    audit.record(
        db, action="fuel.create", actor_id=user.id, family_id=vehicle.family_id,
        entity_type="fuel", entity_id=log.id,
    )
    return FuelRead.model_validate(log)


@router.patch("/fuel/{fuel_id}", response_model=FuelRead)
def update_fuel(
    fuel_id: int,
    body: FuelUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> FuelRead:
    log = db.get(FuelLog, fuel_id)
    if not log:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Fuel log not found")
    require_vehicle_write(log.vehicle_id, db=db, user=user)
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(log, k, v)
    db.commit()
    recompute(db, log.vehicle_id)
    db.refresh(log)
    return FuelRead.model_validate(log)


@router.delete("/fuel/{fuel_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_fuel(
    fuel_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    log = db.get(FuelLog, fuel_id)
    if not log:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Fuel log not found")
    require_vehicle_write(log.vehicle_id, db=db, user=user)
    vehicle_id = log.vehicle_id
    db.delete(log)
    db.commit()
    recompute(db, vehicle_id)
