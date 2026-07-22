"""Shared FastAPI dependencies: DB session, current user, access control."""
from __future__ import annotations

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.core.security import decode_access_token, hash_password
from app.database import get_db
from app.models.enums import FamilyRole
from app.models.family import FamilyMembership
from app.models.user import User
from app.models.vehicle import Vehicle

CREDENTIALS_EXC = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Not authenticated",
    headers={"WWW-Authenticate": "Bearer"},
)


def _single_user(db: Session) -> User:
    """Return (creating on first use) the built-in single-user owner."""
    user = db.scalar(select(User).where(User.email == settings.single_user_email))
    if user is None:
        user = User(
            email=settings.single_user_email,
            name=settings.single_user_name,
            hashed_password=hash_password("single-user-mode"),
            is_superuser=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    if settings.single_user:
        return _single_user(db)

    if not authorization or not authorization.lower().startswith("bearer "):
        raise CREDENTIALS_EXC
    token = authorization.split(" ", 1)[1].strip()
    payload = decode_access_token(token)
    if not payload or payload.get("scope") == "download":
        raise CREDENTIALS_EXC
    sub = payload.get("sub")
    if sub is None:
        raise CREDENTIALS_EXC
    try:
        user = db.get(User, int(sub))
    except (TypeError, ValueError):
        raise CREDENTIALS_EXC from None
    if user is None or not user.is_active:
        raise CREDENTIALS_EXC
    return user


def get_optional_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User | None:
    try:
        return get_current_user(authorization=authorization, db=db)
    except HTTPException:
        return None


# --------------------------------------------------------------------------- #
# Access control
# --------------------------------------------------------------------------- #
def _family_role(db: Session, user_id: int, family_id: int) -> FamilyRole | None:
    membership = db.scalar(
        select(FamilyMembership).where(
            FamilyMembership.user_id == user_id,
            FamilyMembership.family_id == family_id,
        )
    )
    return membership.role if membership else None


def get_accessible_vehicle(
    vehicle_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Vehicle:
    """Return the vehicle if the user owns it or shares its family. 404 otherwise."""
    vehicle = db.get(Vehicle, vehicle_id)
    if vehicle is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Vehicle not found")
    if vehicle.owner_id == user.id:
        return vehicle
    if vehicle.family_id and _family_role(db, user.id, vehicle.family_id) is not None:
        return vehicle
    raise HTTPException(status.HTTP_404_NOT_FOUND, "Vehicle not found")


def require_vehicle_write(
    vehicle_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Vehicle:
    """Like get_accessible_vehicle but forbids family 'viewer' role from writing."""
    vehicle = get_accessible_vehicle(vehicle_id, db=db, user=user)
    if vehicle.owner_id == user.id:
        return vehicle
    role = _family_role(db, user.id, vehicle.family_id) if vehicle.family_id else None
    if role == FamilyRole.viewer:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Viewers cannot modify shared vehicles")
    return vehicle
