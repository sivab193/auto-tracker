"""Vehicle CRUD. Lists owned + family-shared vehicles."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_accessible_vehicle, get_current_user, require_vehicle_write
from app.database import get_db
from app.models.family import FamilyMembership
from app.models.user import User
from app.models.vehicle import Vehicle
from app.schemas.vehicle import (
    VehicleCreate,
    VehicleDetail,
    VehicleRead,
    VehicleUpdate,
)
from app.services import audit

router = APIRouter(prefix="/vehicles", tags=["vehicles"])


def _family_ids(db: Session, user_id: int) -> list[int]:
    rows = db.scalars(
        select(FamilyMembership.family_id).where(FamilyMembership.user_id == user_id)
    ).all()
    return list(rows)


@router.get("", response_model=list[VehicleRead])
def list_vehicles(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[VehicleRead]:
    fam_ids = _family_ids(db, user.id)
    conditions = [Vehicle.owner_id == user.id]
    if fam_ids:
        conditions.append(Vehicle.family_id.in_(fam_ids))
    vehicles = db.scalars(
        select(Vehicle).where(or_(*conditions)).order_by(Vehicle.created_at.desc())
    ).all()
    return [VehicleRead.model_validate(v) for v in vehicles]


@router.post("", response_model=VehicleRead, status_code=status.HTTP_201_CREATED)
def create_vehicle(
    body: VehicleCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> VehicleRead:
    if body.family_id is not None and body.family_id not in _family_ids(db, user.id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not a member of that family")
    vehicle = Vehicle(owner_id=user.id, **body.model_dump())
    db.add(vehicle)
    db.commit()
    db.refresh(vehicle)
    audit.record(
        db, action="vehicle.create", actor_id=user.id, family_id=vehicle.family_id,
        entity_type="vehicle", entity_id=vehicle.id, detail=vehicle.registration_number,
    )
    return VehicleRead.model_validate(vehicle)


@router.get("/{vehicle_id}", response_model=VehicleDetail)
def get_vehicle(vehicle: Vehicle = Depends(get_accessible_vehicle)) -> VehicleDetail:
    detail = VehicleDetail.model_validate(vehicle)
    detail.documents = [
        d for d in vehicle.documents if d.is_current  # type: ignore[attr-defined]
    ]
    return detail


@router.patch("/{vehicle_id}", response_model=VehicleRead)
def update_vehicle(
    body: VehicleUpdate,
    db: Session = Depends(get_db),
    vehicle: Vehicle = Depends(require_vehicle_write),
    user: User = Depends(get_current_user),
) -> VehicleRead:
    data = body.model_dump(exclude_unset=True)
    if "family_id" in data and data["family_id"] is not None:
        if data["family_id"] not in _family_ids(db, user.id):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Not a member of that family")
    for k, v in data.items():
        setattr(vehicle, k, v)
    db.commit()
    db.refresh(vehicle)
    audit.record(
        db, action="vehicle.update", actor_id=user.id, family_id=vehicle.family_id,
        entity_type="vehicle", entity_id=vehicle.id,
    )
    return VehicleRead.model_validate(vehicle)


@router.delete("/{vehicle_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_vehicle(
    db: Session = Depends(get_db),
    vehicle: Vehicle = Depends(get_accessible_vehicle),
    user: User = Depends(get_current_user),
):
    # Only the owner may delete outright.
    if vehicle.owner_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the owner can delete this vehicle")
    audit.record(
        db, action="vehicle.delete", actor_id=user.id, family_id=vehicle.family_id,
        entity_type="vehicle", entity_id=vehicle.id, detail=vehicle.registration_number,
        commit=False,
    )
    db.delete(vehicle)
    db.commit()
