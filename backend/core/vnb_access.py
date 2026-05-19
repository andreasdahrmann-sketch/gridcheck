from __future__ import annotations

from fastapi import Depends, HTTPException
from sqlalchemy import inspect
from sqlalchemy.orm import Session

from core.auth import get_current_user
from db.database import get_db
from db.models import User

VNB_STATUS_NONE = "none"
VNB_STATUS_PENDING = "pending"
VNB_STATUS_APPROVED = "approved"
_VNB_STATUSES = {VNB_STATUS_NONE, VNB_STATUS_PENDING, VNB_STATUS_APPROVED}


def normalize_vnb_verification_status(raw: str | None) -> str:
    value = str(raw or VNB_STATUS_NONE).strip().lower()
    if value not in _VNB_STATUSES:
        return VNB_STATUS_NONE
    return value


def _read_status(user: User, *, db: Session | None = None) -> str:
    if db is not None:
        try:
            columns = {col["name"] for col in inspect(db.get_bind()).get_columns("users")}
        except Exception:
            columns = set()
        if "vnb_verification_status" not in columns:
            return VNB_STATUS_NONE
    if hasattr(user, "vnb_verification_status"):
        return normalize_vnb_verification_status(user.vnb_verification_status)
    return VNB_STATUS_NONE


def user_is_verified_netzbetreiber(user: User, *, db: Session | None = None) -> bool:
    role = str(getattr(user, "role", "") or "").strip().lower()
    if role != "netzbetreiber":
        return False
    return _read_status(user, db=db) == VNB_STATUS_APPROVED


def user_to_vnb_access_fields(user: User, *, db: Session | None = None) -> dict[str, str | bool]:
    status = _read_status(user, db=db)
    return {
        "vnb_verification_status": status,
        "netzbetreiber_verified": user_is_verified_netzbetreiber(user, db=db),
    }


def assert_verified_netzbetreiber(user: User, *, db: Session | None = None) -> User:
    role = str(getattr(user, "role", "") or "").strip().lower()
    if role == "admin":
        return user
    if user_is_verified_netzbetreiber(user, db=db):
        return user

    status = _read_status(user, db=db)
    if role != "netzbetreiber":
        message = (
            "Dieses Dashboard ist nur fuer Netzbetreiber. "
            "Registrieren Sie sich mit Rolle Netzbetreiber und lassen Sie sich freischalten."
        )
        hint = "Registrierung mit Rolle Netzbetreiber und anschliessende Freischaltung durch GridCheck erforderlich."
    elif status == VNB_STATUS_PENDING:
        message = (
            "Ihre Identitaet als Netzbetreiber wird geprueft. "
            "Der Zugang wird nach Freischaltung freigegeben."
        )
        hint = "Kontaktieren Sie uns unter Kontakt oder in den Einstellungen, falls die Pruefung laenger dauert."
    else:
        message = (
            "Dieses Dashboard ist nur fuer freigeschaltete Netzbetreiber. "
            "Registrieren Sie sich mit Rolle Netzbetreiber und lassen Sie sich freischalten."
        )
        hint = "Freischaltung erfolgt manuell nach Identitaetspruefung durch einen Administrator."

    raise HTTPException(
        status_code=403,
        detail={
            "code": "VNB_ACCESS_DENIED",
            "message": message,
            "hint": hint,
            "vnb_verification_status": status,
        },
    )


def require_verified_netzbetreiber(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    return assert_verified_netzbetreiber(current_user, db=db)


def require_verified_netzbetreiber_comms(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    """NB-Austausch: nur freigeschaltete Netzbetreiber, kein Admin-Bypass."""
    if user_is_verified_netzbetreiber(current_user, db=db):
        return current_user

    status = _read_status(current_user, db=db)
    role = str(getattr(current_user, "role", "") or "").strip().lower()
    if role == "netzbetreiber" and status == VNB_STATUS_PENDING:
        code = "VNB_VERIFICATION_PENDING"
        message = "Netzbetreiber-Verifizierung ist noch ausstehend."
        hint = "Bitte die Freischaltung durch GridCheck abwarten."
    else:
        code = "VNB_COMMS_FORBIDDEN"
        message = "Der NB-Austausch ist nur fuer verifizierte Netzbetreiber freigeschaltet."
        hint = "Bitte VNB-Verifizierung anfordern oder mit einem freigeschalteten NB-Konto anmelden."

    raise HTTPException(
        status_code=403,
        detail={"code": code, "message": message, "hint": hint, "vnb_verification_status": status},
    )
