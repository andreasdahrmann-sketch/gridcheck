from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from core.auth import hash_password, verify_password
from db.models import User


def update_me(db: Session, user: User, *, full_name: str | None, role: str | None) -> User:
    if full_name is not None:
        user.full_name = full_name
    if role is not None and user.role == "admin":
        user.role = role
    user.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user)
    return user


def change_password(db: Session, user: User, *, current_password: str, new_password: str) -> None:
    if not verify_password(current_password, user.password_hash):
        raise HTTPException(
            status_code=401,
            detail={"code": "PASSWORD_INVALID", "message": "Aktuelles Passwort ist falsch", "hint": "Bitte erneut versuchen."},
        )
    user.password_hash = hash_password(new_password)
    user.updated_at = datetime.now(timezone.utc)
    db.commit()
