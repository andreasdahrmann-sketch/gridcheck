from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from fastapi import Cookie, Depends, Header, HTTPException
import jwt
from jwt import InvalidTokenError
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from core.config import settings
from db.database import get_db
from db.models import User

security = HTTPBearer(auto_error=False)
_BCRYPT_ROUNDS = 12
_LEGACY_PBKDF2_ITERATIONS = 120_000


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def _is_bcrypt_hash(hashed_password: str) -> bool:
    return hashed_password.startswith(("$2a$", "$2b$", "$2y$"))


def _verify_legacy_pbkdf2_password(password: str, hashed_password: str) -> bool:
    try:
        salt_b64, digest_b64 = hashed_password.split(".", 1)
        salt = _b64url_decode(salt_b64)
        expected = _b64url_decode(digest_b64)
    except Exception:
        return False
    actual = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        _LEGACY_PBKDF2_ITERATIONS,
    )
    return hmac.compare_digest(expected, actual)


def hash_password(password: str) -> str:
    hashed = bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt(rounds=_BCRYPT_ROUNDS),
    )
    return hashed.decode("utf-8")


def verify_password(password: str, hashed_password: str) -> bool:
    if not hashed_password:
        return False
    if _is_bcrypt_hash(hashed_password):
        try:
            return bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))
        except ValueError:
            return False
    return _verify_legacy_pbkdf2_password(password, hashed_password)


def password_hash_needs_upgrade(hashed_password: str) -> bool:
    if not _is_bcrypt_hash(hashed_password):
        return True
    try:
        rounds = int(hashed_password.split("$", 3)[2])
    except (IndexError, ValueError):
        return True
    return rounds < _BCRYPT_ROUNDS


def _jwt_secret(is_refresh: bool = False) -> str:
    raw = settings.jwt_refresh_secret if is_refresh else settings.jwt_secret
    if not raw:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "AUTH_JWT_NOT_CONFIGURED",
                "message": "JWT-Signatur ist nicht konfiguriert",
                "hint": "JWT_SECRET und JWT_REFRESH_SECRET setzen (je min. 32 Zeichen, unterschiedliche Werte).",
            },
        )
    return raw


def create_token(payload: dict[str, Any], expires_minutes: int, *, refresh: bool = False) -> str:
    exp = int((datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)).timestamp())
    body = {
        **payload,
        "exp": exp,
        "iat": int(datetime.now(timezone.utc).timestamp()),
        "typ": "refresh" if refresh else "access",
        "iss": "gridcheck-api",
    }
    return jwt.encode(body, _jwt_secret(is_refresh=refresh), algorithm="HS256")


def decode_token(token: str, *, refresh: bool = False) -> dict[str, Any]:
    try:
        payload = jwt.decode(
            token,
            _jwt_secret(is_refresh=refresh),
            algorithms=["HS256"],
            options={"require": ["exp", "iat", "typ", "iss"]},
            issuer="gridcheck-api",
        )
    except InvalidTokenError as exc:
        raise HTTPException(
            status_code=401,
            detail={"code": "AUTH_TOKEN_INVALID", "message": "Token ist ungueltig", "hint": "Bitte erneut einloggen."},
        ) from exc
    if payload.get("typ") != ("refresh" if refresh else "access"):
        raise HTTPException(
            status_code=401,
            detail={"code": "AUTH_TOKEN_TYPE_INVALID", "message": "Token-Typ ungueltig", "hint": "Bitte erneut einloggen."},
        )
    return payload


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(security),
    access_cookie: str | None = Cookie(default=None, alias=settings.auth_access_cookie),
    db: Session = Depends(get_db),
) -> User:
    token = None
    if creds is not None:
        token = creds.credentials
    elif access_cookie:
        token = access_cookie
    if token is None:
        raise HTTPException(
            status_code=401,
            detail={"code": "AUTH_REQUIRED", "message": "Login erforderlich", "hint": "Bitte zuerst anmelden."},
        )
    payload = decode_token(token, refresh=False)
    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == user_id).first()
    if not user or user.deleted_at is not None or not user.is_active:
        raise HTTPException(
            status_code=401,
            detail={"code": "AUTH_USER_INVALID", "message": "Benutzer ungueltig", "hint": "Bitte erneut anmelden."},
        )
    return user


def require_admin_user(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail={
                "code": "AUTH_FORBIDDEN",
                "message": "Diese Funktion ist nur fuer interne Admin-Nutzer freigeschaltet.",
                "hint": "Bitte mit einem Admin-Konto anmelden.",
            },
        )
    return current_user


def issue_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def require_csrf(
    creds: HTTPAuthorizationCredentials | None = Depends(security),
    csrf_header: str | None = Header(default=None, alias="X-CSRF-Token"),
    csrf_cookie: str | None = Cookie(default=None, alias=settings.auth_csrf_cookie),
) -> None:
    # Bearer clients (e.g. scripts/tests) are not cookie-authenticated and are not CSRF targets.
    if creds is not None:
        return
    if not csrf_header or not csrf_cookie or not hmac.compare_digest(csrf_header, csrf_cookie):
        raise HTTPException(
            status_code=403,
            detail={"code": "CSRF_INVALID", "message": "CSRF-Pruefung fehlgeschlagen", "hint": "Bitte Seite neu laden und erneut versuchen."},
        )
