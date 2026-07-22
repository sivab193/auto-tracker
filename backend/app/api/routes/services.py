"""Service records and accident history for a vehicle."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_accessible_vehicle, get_current_user, require_vehicle_write
from app.database import get_db
from app.models.service import AccidentRecord, ServiceRecord
from app.models.user import User
from app.models.vehicle import Vehicle
from app.schemas.service import (
    AccidentCreate,
    AccidentRead,
    ServiceCreate,
    ServiceRead,
    ServiceUpdate,
)
from app.services import audit

router = APIRouter(tags=["services"])


# --- Service records --------------------------------------------------------
@router.get("/vehicles/{vehicle_id}/services", response_model=list[ServiceRead])
def list_services(
    db: Session = Depends(get_db),
    vehicle: Vehicle = Depends(get_accessible_vehicle),
) -> list[ServiceRead]:
    rows = db.scalars(
        select(ServiceRecord)
        .where(ServiceRecord.vehicle_id == vehicle.id)
        .order_by(ServiceRecord.service_date.desc())
    ).all()
    return [ServiceRead.model_validate(r) for r in rows]


@router.post(
    "/vehicles/{vehicle_id}/services",
    response_model=ServiceRead,
    status_code=status.HTTP_201_CREATED,
)
def create_service(
    body: ServiceCreate,
    db: Session = Depends(get_db),
    vehicle: Vehicle = Depends(require_vehicle_write),
    user: User = Depends(get_current_user),
) -> ServiceRead:
    record = ServiceRecord(vehicle_id=vehicle.id, **body.model_dump())
    db.add(record)
    # Keep the vehicle odometer moving forward.
    if record.odometer and record.odometer > vehicle.odometer:
        vehicle.odometer = record.odometer
    db.commit()
    db.refresh(record)
    audit.record(
        db, action="service.create", actor_id=user.id, family_id=vehicle.family_id,
        entity_type="service", entity_id=record.id,
    )
    return ServiceRead.model_validate(record)


@router.patch("/services/{service_id}", response_model=ServiceRead)
def update_service(
    service_id: int,
    body: ServiceUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ServiceRead:
    record = db.get(ServiceRecord, service_id)
    if not record:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Service record not found")
    require_vehicle_write(record.vehicle_id, db=db, user=user)
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(record, k, v)
    db.commit()
    db.refresh(record)
    return ServiceRead.model_validate(record)


@router.delete("/services/{service_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_service(
    service_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    record = db.get(ServiceRecord, service_id)
    if not record:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Service record not found")
    require_vehicle_write(record.vehicle_id, db=db, user=user)
    db.delete(record)
    db.commit()


# --- Accident history -------------------------------------------------------
@router.get("/vehicles/{vehicle_id}/accidents", response_model=list[AccidentRead])
def list_accidents(
    db: Session = Depends(get_db),
    vehicle: Vehicle = Depends(get_accessible_vehicle),
) -> list[AccidentRead]:
    rows = db.scalars(
        select(AccidentRecord)
        .where(AccidentRecord.vehicle_id == vehicle.id)
        .order_by(AccidentRecord.accident_date.desc())
    ).all()
    return [AccidentRead.model_validate(r) for r in rows]


@router.post(
    "/vehicles/{vehicle_id}/accidents",
    response_model=AccidentRead,
    status_code=status.HTTP_201_CREATED,
)
def create_accident(
    body: AccidentCreate,
    db: Session = Depends(get_db),
    vehicle: Vehicle = Depends(require_vehicle_write),
    user: User = Depends(get_current_user),
) -> AccidentRead:
    record = AccidentRecord(vehicle_id=vehicle.id, **body.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    audit.record(
        db, action="accident.create", actor_id=user.id, family_id=vehicle.family_id,
        entity_type="accident", entity_id=record.id,
    )
    return AccidentRead.model_validate(record)


@router.delete("/accidents/{accident_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_accident(
    accident_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    record = db.get(AccidentRecord, accident_id)
    if not record:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Accident record not found")
    require_vehicle_write(record.vehicle_id, db=db, user=user)
    db.delete(record)
    db.commit()
