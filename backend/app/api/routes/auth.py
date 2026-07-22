"""Authentication: register, login, profile, Telegram link code."""
from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.config import settings
from app.core.security import create_access_token, hash_password, verify_password
from app.database import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, Token, UserCreate, UserRead, UserUpdate

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/config")
def auth_config() -> dict:
    """Public flags the frontend needs before login."""
    return {"single_user": settings.single_user, "app_name": settings.app_name}


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register(body: UserCreate, db: Session = Depends(get_db)) -> Token:
    if settings.single_user:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Registration disabled in single-user mode")
    existing = db.scalar(select(User).where(User.email == body.email))
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    user = User(
        email=body.email,
        name=body.name,
        preferred_language=body.preferred_language,
        hashed_password=hash_password(body.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token(user.id)
    return Token(access_token=token, user=UserRead.model_validate(user))


@router.post("/login", response_model=Token)
def login(body: LoginRequest, db: Session = Depends(get_db)) -> Token:
    user = db.scalar(select(User).where(User.email == body.email))
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account disabled")
    token = create_access_token(user.id)
    return Token(access_token=token, user=UserRead.model_validate(user))


@router.get("/me", response_model=UserRead)
def me(user: User = Depends(get_current_user)) -> UserRead:
    return UserRead.model_validate(user)


@router.patch("/me", response_model=UserRead)
def update_me(
    body: UserUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> UserRead:
    if body.name is not None:
        user.name = body.name
    if body.preferred_language is not None:
        user.preferred_language = body.preferred_language
    if body.password:
        user.hashed_password = hash_password(body.password)
    db.commit()
    db.refresh(user)
    return UserRead.model_validate(user)


@router.post("/telegram/link-code")
def create_telegram_link_code(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Generate a one-time code to bind a Telegram chat via `/link <code>`."""
    code = secrets.token_hex(4)
    user.telegram_link_code = code
    db.commit()
    return {"code": code, "instructions": f"Send `/link {code}` to the AutoTracker bot on Telegram."}


@router.delete("/telegram/link")
def unlink_telegram(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    user.telegram_chat_id = None
    user.telegram_link_code = None
    db.commit()
    return {"ok": True}
