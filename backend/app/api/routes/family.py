"""Family groups: invite codes, role-based membership, shared-access audit log."""
from __future__ import annotations

import secrets
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models.alert import AuditLog
from app.models.enums import FamilyRole
from app.models.family import Family, FamilyInvite, FamilyMembership
from app.models.mixins import utcnow
from app.models.user import User
from app.schemas.alert import AuditRead
from app.schemas.family import (
    FamilyCreate,
    FamilyRead,
    InviteCreate,
    InviteRead,
    JoinRequest,
    MemberRead,
    RoleUpdate,
)
from app.services import audit

router = APIRouter(prefix="/families", tags=["family"])


def _membership(db: Session, family_id: int, user_id: int) -> FamilyMembership | None:
    return db.scalar(
        select(FamilyMembership).where(
            FamilyMembership.family_id == family_id,
            FamilyMembership.user_id == user_id,
        )
    )


def _require_member(db: Session, family_id: int, user: User) -> FamilyMembership:
    m = _membership(db, family_id, user.id)
    if not m:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Family not found")
    return m


def _require_admin(db: Session, family_id: int, user: User) -> FamilyMembership:
    m = _require_member(db, family_id, user)
    if m.role != FamilyRole.admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin role required")
    return m


def _to_family_read(db: Session, family: Family) -> FamilyRead:
    members = []
    for m in family.memberships:
        u = db.get(User, m.user_id)
        members.append(
            MemberRead(
                id=m.id, user_id=m.user_id, role=m.role,
                user_name=u.name if u else None, user_email=u.email if u else None,
            )
        )
    return FamilyRead(id=family.id, name=family.name, owner_id=family.owner_id, members=members)


@router.get("", response_model=list[FamilyRead])
def list_families(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[FamilyRead]:
    fam_ids = db.scalars(
        select(FamilyMembership.family_id).where(FamilyMembership.user_id == user.id)
    ).all()
    families = db.scalars(select(Family).where(Family.id.in_(fam_ids))).all() if fam_ids else []
    return [_to_family_read(db, f) for f in families]


@router.post("", response_model=FamilyRead, status_code=status.HTTP_201_CREATED)
def create_family(
    body: FamilyCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> FamilyRead:
    family = Family(name=body.name, owner_id=user.id)
    db.add(family)
    db.flush()
    db.add(FamilyMembership(family_id=family.id, user_id=user.id, role=FamilyRole.admin))
    db.commit()
    db.refresh(family)
    audit.record(
        db, action="family.create", actor_id=user.id, family_id=family.id,
        entity_type="family", entity_id=family.id, detail=family.name,
    )
    return _to_family_read(db, family)


@router.get("/{family_id}", response_model=FamilyRead)
def get_family(
    family_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> FamilyRead:
    _require_member(db, family_id, user)
    family = db.get(Family, family_id)
    return _to_family_read(db, family)


@router.post("/{family_id}/invites", response_model=InviteRead, status_code=status.HTTP_201_CREATED)
def create_invite(
    family_id: int,
    body: InviteCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> InviteRead:
    _require_admin(db, family_id, user)
    expires_at = None
    if body.expires_in_hours:
        expires_at = utcnow() + timedelta(hours=body.expires_in_hours)
    invite = FamilyInvite(
        family_id=family_id,
        code=secrets.token_urlsafe(6)[:8].upper(),
        role=body.role,
        created_by_id=user.id,
        max_uses=max(1, body.max_uses),
        expires_at=expires_at,
    )
    db.add(invite)
    db.commit()
    db.refresh(invite)
    audit.record(
        db, action="invite.create", actor_id=user.id, family_id=family_id,
        entity_type="invite", entity_id=invite.id, detail=f"role={body.role.value}",
    )
    return InviteRead.model_validate(invite)


@router.get("/{family_id}/invites", response_model=list[InviteRead])
def list_invites(
    family_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[InviteRead]:
    _require_admin(db, family_id, user)
    rows = db.scalars(
        select(FamilyInvite).where(FamilyInvite.family_id == family_id)
    ).all()
    return [InviteRead.model_validate(r) for r in rows]


@router.delete("/{family_id}/invites/{invite_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_invite(
    family_id: int,
    invite_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_admin(db, family_id, user)
    invite = db.get(FamilyInvite, invite_id)
    if not invite or invite.family_id != family_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Invite not found")
    invite.revoked = True
    db.commit()


@router.post("/join", response_model=FamilyRead)
def join_family(
    body: JoinRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> FamilyRead:
    invite = db.scalar(select(FamilyInvite).where(FamilyInvite.code == body.code.strip().upper()))
    if not invite or not invite.is_usable:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or expired invite code")
    if _membership(db, invite.family_id, user.id):
        raise HTTPException(status.HTTP_409_CONFLICT, "Already a member of this family")
    db.add(FamilyMembership(family_id=invite.family_id, user_id=user.id, role=invite.role))
    invite.uses += 1
    db.commit()
    audit.record(
        db, action="family.join", actor_id=user.id, family_id=invite.family_id,
        entity_type="membership", detail=f"role={invite.role.value}",
    )
    family = db.get(Family, invite.family_id)
    return _to_family_read(db, family)


@router.patch("/{family_id}/members/{membership_id}", response_model=MemberRead)
def update_member_role(
    family_id: int,
    membership_id: int,
    body: RoleUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> MemberRead:
    _require_admin(db, family_id, user)
    m = db.get(FamilyMembership, membership_id)
    if not m or m.family_id != family_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Member not found")
    family = db.get(Family, family_id)
    if m.user_id == family.owner_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot change the owner's role")
    m.role = body.role
    db.commit()
    db.refresh(m)
    audit.record(
        db, action="member.role_change", actor_id=user.id, family_id=family_id,
        entity_type="membership", entity_id=m.id, detail=f"role={body.role.value}",
    )
    u = db.get(User, m.user_id)
    return MemberRead(
        id=m.id, user_id=m.user_id, role=m.role,
        user_name=u.name if u else None, user_email=u.email if u else None,
    )


@router.delete("/{family_id}/members/{membership_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(
    family_id: int,
    membership_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    m = db.get(FamilyMembership, membership_id)
    if not m or m.family_id != family_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Member not found")
    family = db.get(Family, family_id)
    # Admins can remove others; anyone can remove themselves (leave).
    is_self = m.user_id == user.id
    if not is_self:
        _require_admin(db, family_id, user)
    if m.user_id == family.owner_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "The owner cannot be removed")
    db.delete(m)
    db.commit()
    audit.record(
        db, action="member.remove", actor_id=user.id, family_id=family_id,
        entity_type="membership", detail="left" if is_self else "removed",
    )


@router.get("/{family_id}/audit", response_model=list[AuditRead])
def family_audit(
    family_id: int,
    limit: int = 100,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[AuditRead]:
    _require_admin(db, family_id, user)
    rows = db.scalars(
        select(AuditLog)
        .where(AuditLog.family_id == family_id)
        .order_by(AuditLog.created_at.desc())
        .limit(min(limit, 500))
    ).all()
    return [AuditRead.model_validate(r) for r in rows]
