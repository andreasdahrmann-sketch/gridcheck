from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from core.auth import create_token, decode_token, hash_password, verify_password
from core.security_log import log_security_event
from db.models import User

ACCESS_TTL_MIN = 60
REFRESH_TTL_MIN = 60 * 24 * 7


def _validate_password_strength(password: str) -> None:
    # Minimum hardening to reduce weak credential usage.
    has_upper = any(ch.isupper() for ch in password)
    has_lower = any(ch.islower() for ch in password)
    has_digit = any(ch.isdigit() for ch in password)
    if len(password) < 10 or not (has_upper and has_lower and has_digit):
        raise HTTPException(
            status_code=400,
            detail={
                "code": "PASSWORD_TOO_WEAK",
                "message": "Passwort erfuellt Sicherheitsanforderungen nicht",
                "hint": "Mindestens 10 Zeichen sowie Gross-/Kleinbuchstaben und Zahl verwenden.",
            },
        )


def register_user(db: Session, *, email: str, password: str, role: str, full_name: str | None) -> User:
    _validate_password_strength(password)
    normalized_email = email.strip().lower()
    existing = db.query(User).filter(User.email == normalized_email).first()
    if existing:
        log_security_event("auth_register_conflict", email=normalized_email)
        raise HTTPException(
            status_code=409,
            detail={"code": "EMAIL_EXISTS", "message": "E-Mail bereits vorhanden", "hint": "Bitte andere E-Mail nutzen."},
        )
    user = User(
        email=normalized_email,
        password_hash=hash_password(password),
        role=role,
        full_name=full_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    log_security_event("auth_register_success", user_id=user.id, email=user.email, role=user.role)
    return user


def login_user(db: Session, *, email: str, password: str) -> User:
    normalized_email = email.strip().lower()
    user = db.query(User).filter(User.email == normalized_email).first()
    if not user or not verify_password(password, user.password_hash):
        log_security_event("auth_login_failed", email=normalized_email)
        raise HTTPException(
            status_code=401,
            detail={"code": "LOGIN_INVALID", "message": "Login fehlgeschlagen", "hint": "E-Mail/Passwort pruefen."},
        )
    if not user.is_active:
        log_security_event("auth_login_inactive", user_id=user.id, email=user.email)
        raise HTTPException(
            status_code=403,
            detail={"code": "USER_INACTIVE", "message": "Benutzer ist deaktiviert", "hint": "Bitte Admin kontaktieren."},
        )
    user.updated_at = datetime.now(timezone.utc)
    db.commit()
    log_security_event("auth_login_success", user_id=user.id, email=user.email, role=user.role)
    return user


def issue_token_pair(user: User) -> dict[str, str]:
    payload = {"sub": user.id, "email": user.email, "role": user.role}
    return {
        "access_token": create_token(payload, ACCESS_TTL_MIN, refresh=False),
        "refresh_token": create_token(payload, REFRESH_TTL_MIN, refresh=True),
        "token_type": "bearer",
    }


def refresh_access_token(refresh_token: str) -> dict[str, str]:
    payload = decode_token(refresh_token, refresh=True)
    access_payload = {"sub": payload["sub"], "email": payload["email"], "role": payload["role"]}
    return {
        "access_token": create_token(access_payload, ACCESS_TTL_MIN, refresh=False),
        "token_type": "bearer",
    }
