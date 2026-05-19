from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.auth import get_current_user, issue_csrf_token, require_csrf
from core.config import settings
from core.rate_limit import enforce_rate_limit
from db.database import get_db
from db.models import User
from services.auth_service import (
    complete_password_reset,
    issue_token_pair,
    login_user,
    refresh_access_token,
    register_user,
    request_password_reset,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=254)
    password: str = Field(..., min_length=12, max_length=128)
    full_name: str | None = Field(default=None, max_length=120)
    role: Literal["projektierer", "netzbetreiber", "endkunde"] = "endkunde"


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=254)
    password: str = Field(..., min_length=8, max_length=128)


class RefreshRequest(BaseModel):
    refresh_token: str | None = Field(default=None, min_length=20)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    email: str
    role: str
    full_name: str | None


class ForgotPasswordRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=254)


class ResetPasswordRequest(BaseModel):
    token: str = Field(..., min_length=20, max_length=512)
    password: str = Field(..., min_length=12, max_length=128)


@router.post("/register", response_model=UserResponse)
def register(req: RegisterRequest, db: Session = Depends(get_db)) -> UserResponse:
    enforce_rate_limit(f"auth:register:{req.email.strip().lower()}", limit=10, window_seconds=300)
    user = register_user(db, email=req.email, password=req.password, role=req.role, full_name=req.full_name)
    return UserResponse(id=user.id, email=user.email, role=user.role, full_name=user.full_name)


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, response: Response, db: Session = Depends(get_db)) -> TokenResponse:
    enforce_rate_limit(f"auth:login:{req.email.strip().lower()}", limit=10, window_seconds=300)
    user = login_user(db, email=req.email, password=req.password)
    tokens = issue_token_pair(user)
    secure_cookie = settings.app_env in {"staging", "prod", "production"}
    response.set_cookie(
        key=settings.auth_access_cookie,
        value=tokens["access_token"],
        httponly=True,
        secure=secure_cookie,
        samesite="lax",
        max_age=60 * 60,
        path="/",
    )
    response.set_cookie(
        key=settings.auth_refresh_cookie,
        value=tokens["refresh_token"],
        httponly=True,
        secure=secure_cookie,
        samesite="lax",
        max_age=60 * 60 * 24 * 7,
        path="/",
    )
    response.set_cookie(
        key=settings.auth_csrf_cookie,
        value=issue_csrf_token(),
        httponly=False,
        secure=secure_cookie,
        samesite="lax",
        max_age=60 * 60 * 24 * 7,
        path="/",
    )
    return TokenResponse(**tokens)


@router.post("/refresh", response_model=TokenResponse)
def refresh(
    req: RefreshRequest,
    response: Response,
    refresh_cookie: str | None = Cookie(default=None, alias=settings.auth_refresh_cookie),
    _: None = Depends(require_csrf),
) -> TokenResponse:
    refresh_token = req.refresh_token or refresh_cookie
    if not refresh_token:
        raise HTTPException(
            status_code=401,
            detail={"code": "AUTH_REFRESH_REQUIRED", "message": "Refresh-Token fehlt", "hint": "Bitte erneut einloggen."},
        )
    token = refresh_access_token(refresh_token)
    secure_cookie = settings.app_env in {"staging", "prod", "production"}
    response.set_cookie(
        key=settings.auth_access_cookie,
        value=token["access_token"],
        httponly=True,
        secure=secure_cookie,
        samesite="lax",
        max_age=60 * 60,
        path="/",
    )
    response.set_cookie(
        key=settings.auth_csrf_cookie,
        value=issue_csrf_token(),
        httponly=False,
        secure=secure_cookie,
        samesite="lax",
        max_age=60 * 60 * 24 * 7,
        path="/",
    )
    return TokenResponse(access_token=token["access_token"], token_type=token["token_type"])


@router.post("/logout")
def logout(response: Response, _: None = Depends(require_csrf)) -> dict[str, str]:
    response.delete_cookie(settings.auth_access_cookie, path="/")
    response.delete_cookie(settings.auth_refresh_cookie, path="/")
    response.delete_cookie(settings.auth_csrf_cookie, path="/")
    return {"status": "ok"}


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        role=current_user.role,
        full_name=current_user.full_name,
    )


@router.post("/forgot-password")
def forgot_password(req: ForgotPasswordRequest, db: Session = Depends(get_db)) -> dict[str, str]:
    """Startet Passwort-Reset (antwortet immer gleich, kein Account-Leak)."""
    enforce_rate_limit(f"auth:forgot:{req.email.strip().lower()}", limit=5, window_seconds=300)
    request_password_reset(db, email=req.email)
    return {
        "status": "ok",
        "message": "Falls ein Konto existiert, wurde eine E-Mail mit weiteren Schritten versendet.",
    }


@router.post("/reset-password")
def reset_password(req: ResetPasswordRequest, db: Session = Depends(get_db)) -> dict[str, str]:
    enforce_rate_limit(f"auth:reset:{req.token[:16]}", limit=10, window_seconds=300)
    complete_password_reset(db, token=req.token, password=req.password)
    return {"status": "ok", "message": "Passwort wurde aktualisiert. Sie koennen sich jetzt anmelden."}
