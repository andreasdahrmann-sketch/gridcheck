from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from core.auth import hash_password, verify_password
from core.security_log import log_security_event
from db.models import PasswordResetToken, User
from services.auth_service import validate_password_strength


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
        log_security_event("auth_password_change_failed", user_id=user.id, reason="current_password_invalid")
        raise HTTPException(
            status_code=401,
            detail={"code": "PASSWORD_INVALID", "message": "Aktuelles Passwort ist falsch", "hint": "Bitte erneut versuchen."},
        )
    validate_password_strength(new_password)
    if verify_password(new_password, user.password_hash):
        log_security_event("auth_password_change_failed", user_id=user.id, reason="password_reuse")
        raise HTTPException(
            status_code=400,
            detail={
                "code": "PASSWORD_REUSE_FORBIDDEN",
                "message": "Neues Passwort muss sich vom bisherigen Passwort unterscheiden",
                "hint": "Bitte ein neues starkes Passwort vergeben.",
            },
        )
    now = datetime.now(timezone.utc)
    user.password_hash = hash_password(new_password)
    user.updated_at = now
    # Outstanding reset links must not survive a voluntary password change
    # (same invalidation pattern as request_password_reset / DSGVO delete).
    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id,
        PasswordResetToken.used_at.is_(None),
    ).update({"used_at": now}, synchronize_session=False)
    db.commit()
    log_security_event("auth_password_change_success", user_id=user.id)
