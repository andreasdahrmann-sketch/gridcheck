from __future__ import annotations

import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from core.anonymized_email import is_reserved_anonymized_email
from core.auth import create_token, decode_token, hash_password, password_hash_needs_upgrade, verify_password
from core.security_log import log_security_event
from core.vnb_access import VNB_STATUS_NONE, VNB_STATUS_PENDING, normalize_vnb_verification_status
from db.models import PasswordResetToken, User

ACCESS_TTL_MIN = 60
REFRESH_TTL_MIN = 60 * 24 * 7
PASSWORD_RESET_TTL_MIN = max(15, int(os.getenv("PASSWORD_RESET_TTL_MIN", "60")))


def _password_reset_base_url() -> str:
    explicit = os.getenv("PASSWORD_RESET_BASE_URL", "").strip()
    if explicit:
        return explicit.rstrip("/")
    checkout = os.getenv("STRIPE_CHECKOUT_SUCCESS_URL", "").strip()
    if checkout:
        return checkout.split("?")[0].replace("/settings", "").rstrip("/")
    return "http://localhost:3000"


def _hash_reset_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def validate_password_strength(password: str) -> None:
    # Public auth flows and password changes share one mandatory password policy.
    has_upper = any(ch.isupper() for ch in password)
    has_lower = any(ch.islower() for ch in password)
    has_digit = any(ch.isdigit() for ch in password)
    has_special = any(not ch.isalnum() for ch in password)
    if len(password) < 12 or not (has_upper and has_lower and has_digit and has_special):
        raise HTTPException(
            status_code=400,
            detail={
                "code": "PASSWORD_TOO_WEAK",
                "message": "Passwort erfuellt Sicherheitsanforderungen nicht",
                "hint": "Mindestens 12 Zeichen sowie Gross-/Kleinbuchstaben, Zahl und Sonderzeichen verwenden.",
            },
        )


def register_user(db: Session, *, email: str, password: str, role: str, full_name: str | None) -> User:
    validate_password_strength(password)
    normalized_email = email.strip().lower()
    normalized_role = role.strip().lower()
    if normalized_role == "admin":
        log_security_event("auth_register_admin_rejected", email=normalized_email)
        raise HTTPException(
            status_code=403,
            detail={
                "code": "ADMIN_SELF_REGISTRATION_FORBIDDEN",
                "message": "Admin-Konten duerfen nicht ueber die oeffentliche Registrierung angelegt werden.",
                "hint": "Admin-Nutzer muessen intern vorprovisioniert werden.",
            },
        )
    # DSGVO Soft-Delete nutzt @anonymized.local intern. Oeffentliche Reservierung
    # dieses Namespaces darf die Art.-17-Loeschung nicht per Unique-Constraint
    # auf users.email blockieren koennen.
    if is_reserved_anonymized_email(normalized_email):
        log_security_event("auth_register_reserved_anonymized_email", email=normalized_email)
        raise HTTPException(
            status_code=400,
            detail={
                "code": "EMAIL_RESERVED",
                "message": "Diese E-Mail-Adresse ist nicht zulaessig.",
                "hint": "Bitte eine andere E-Mail-Adresse verwenden.",
            },
        )
    existing = db.query(User).filter(User.email == normalized_email).first()
    if existing:
        log_security_event("auth_register_conflict", email=normalized_email)
        raise HTTPException(
            status_code=409,
            detail={"code": "EMAIL_EXISTS", "message": "E-Mail bereits vorhanden", "hint": "Bitte andere E-Mail nutzen."},
        )
    # DSGVO Art. 17: Re-Registrierung mit einer zuvor geloeschten E-Mail ist gesperrt.
    # Der Klartext der E-Mail ist beim Soft-Delete entfernt worden; verglichen wird
    # gegen den dabei gespeicherten SHA256-Hash (deleted_email_hash).
    email_hash = hashlib.sha256(normalized_email.encode("utf-8")).hexdigest()
    deleted_match = (
        db.query(User)
        .filter(User.deleted_email_hash == email_hash, User.deleted_at.isnot(None))
        .first()
    )
    if deleted_match:
        log_security_event("auth_register_blocked_deleted", email=normalized_email)
        raise HTTPException(
            status_code=409,
            detail={
                "code": "EMAIL_DELETED_BLOCKED",
                "message": "Konto mit dieser E-Mail wurde geloescht und ist gesperrt.",
                "hint": "Bitte eine andere E-Mail-Adresse verwenden oder Support kontaktieren.",
            },
        )
    vnb_status = VNB_STATUS_PENDING if normalized_role == "netzbetreiber" else VNB_STATUS_NONE
    user = User(
        email=normalized_email,
        password_hash=hash_password(password),
        role=normalized_role,
        vnb_verification_status=vnb_status,
        full_name=full_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    log_security_event("auth_register_success", user_id=user.id, email=user.email, role=user.role)
    try:
        from services.email_service import send_welcome_email

        send_welcome_email(to_email=user.email, full_name=user.full_name)
    except Exception:
        pass
    return user


def login_user(db: Session, *, email: str, password: str) -> User:
    normalized_email = email.strip().lower()
    user = db.query(User).filter(User.email == normalized_email).first()
    # DSGVO-geloeschte Konten antworten identisch zu nicht-existenten Konten,
    # um Account-Enumeration zu vermeiden (Soft-Delete: deleted_at gesetzt).
    if not user or user.deleted_at is not None or not verify_password(password, user.password_hash):
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
    upgraded_hash = False
    if password_hash_needs_upgrade(user.password_hash):
        user.password_hash = hash_password(password)
        upgraded_hash = True
    user.updated_at = datetime.now(timezone.utc)
    db.commit()
    if upgraded_hash:
        log_security_event("auth_password_hash_upgraded", user_id=user.id, email=user.email)
    log_security_event("auth_login_success", user_id=user.id, email=user.email, role=user.role)
    return user


def issue_token_pair(user: User) -> dict[str, str]:
    payload = {"sub": str(user.id), "email": user.email, "role": user.role}
    return {
        "access_token": create_token(payload, ACCESS_TTL_MIN, refresh=False),
        "refresh_token": create_token(payload, REFRESH_TTL_MIN, refresh=True),
        "token_type": "bearer",
    }


def refresh_access_token(refresh_token: str) -> dict[str, str]:
    payload = decode_token(refresh_token, refresh=True)
    access_payload = {"sub": str(payload["sub"]), "email": payload["email"], "role": payload["role"]}
    return {
        "access_token": create_token(access_payload, ACCESS_TTL_MIN, refresh=False),
        "token_type": "bearer",
    }


def request_password_reset(db: Session, *, email: str) -> None:
    """Antwortet immer gleich (kein Account-Leak). Versendet Reset-Mail nur wenn Konto existiert."""
    normalized_email = email.strip().lower()
    if not normalized_email:
        return

    user = db.query(User).filter(User.email == normalized_email, User.is_active.is_(True)).first()
    if not user:
        log_security_event("auth_password_reset_unknown", email=normalized_email)
        return

    raw_token = secrets.token_urlsafe(32)
    token_hash = _hash_reset_token(raw_token)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=PASSWORD_RESET_TTL_MIN)

    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id,
        PasswordResetToken.used_at.is_(None),
    ).update({"used_at": datetime.now(timezone.utc)}, synchronize_session=False)

    db.add(
        PasswordResetToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
    )
    db.commit()

    reset_url = f"{_password_reset_base_url()}/login?reset_token={raw_token}"
    log_security_event("auth_password_reset_requested", user_id=user.id, email=user.email)

    from services.email_service import send_password_reset_email

    send_password_reset_email(to_email=user.email, reset_url=reset_url)


def complete_password_reset(db: Session, *, token: str, password: str) -> None:
    validate_password_strength(password)
    token_hash = _hash_reset_token(token.strip())
    now = datetime.now(timezone.utc)

    reset_row = (
        db.query(PasswordResetToken)
        .filter(
            PasswordResetToken.token_hash == token_hash,
            PasswordResetToken.used_at.is_(None),
            PasswordResetToken.expires_at > now,
        )
        .first()
    )
    if not reset_row:
        log_security_event("auth_password_reset_invalid_token")
        raise HTTPException(
            status_code=400,
            detail={
                "code": "PASSWORD_RESET_INVALID",
                "message": "Reset-Link ungueltig oder abgelaufen",
                "hint": "Bitte erneut „Passwort vergessen“ anfordern.",
            },
        )

    user = db.query(User).filter(User.id == reset_row.user_id, User.is_active.is_(True)).first()
    if not user:
        log_security_event("auth_password_reset_inactive_user", user_id=reset_row.user_id)
        raise HTTPException(
            status_code=400,
            detail={
                "code": "PASSWORD_RESET_INVALID",
                "message": "Reset-Link ungueltig oder abgelaufen",
                "hint": "Bitte erneut „Passwort vergessen“ anfordern.",
            },
        )

    user.password_hash = hash_password(password)
    user.updated_at = now
    reset_row.used_at = now
    db.commit()
    log_security_event("auth_password_reset_completed", user_id=user.id, email=user.email)


def approve_netzbetreiber(db: Session, *, user_id: int) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "USER_NOT_FOUND",
                "message": "Benutzer nicht gefunden",
                "hint": "user_id pruefen.",
            },
        )
    role = str(user.role or "").strip().lower()
    if role != "netzbetreiber":
        raise HTTPException(
            status_code=400,
            detail={
                "code": "VNB_APPROVE_ROLE_INVALID",
                "message": "Freischaltung ist nur fuer Konten mit Rolle netzbetreiber moeglich.",
                "hint": "Rolle des Benutzers pruefen oder Rolle zuerst anpassen.",
            },
        )
    from core.vnb_access import VNB_STATUS_APPROVED

    user.vnb_verification_status = VNB_STATUS_APPROVED
    user.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user)
    log_security_event(
        "vnb_operator_approved",
        user_id=user.id,
        email=user.email,
        vnb_verification_status=normalize_vnb_verification_status(user.vnb_verification_status),
    )
    return user

