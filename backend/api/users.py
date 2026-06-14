from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import Response as RawResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.auth import get_current_user, require_csrf
from core.config import settings
from core.rate_limit import enforce_rate_limit, get_client_ip
from core.vnb_access import user_to_vnb_access_fields
from db.database import get_db
from db.models import User
from services.dsgvo_service import (
    build_user_export_zip,
    delete_user_account,
    record_export_audit,
)
from services.user_service import change_password, update_me

router = APIRouter(prefix="/api/v1/users", tags=["users"])


class MeResponse(BaseModel):
    id: int
    email: str
    role: str
    full_name: str | None
    vnb_verification_status: str = "none"
    netzbetreiber_verified: bool = False
    vnb_dashboard_access: bool = False


def _me_response(user: User) -> MeResponse:
    fields = user_to_vnb_access_fields(user)
    return MeResponse(
        id=user.id,
        email=user.email,
        role=user.role,
        full_name=user.full_name,
        vnb_verification_status=str(fields["vnb_verification_status"]),
        netzbetreiber_verified=bool(fields["netzbetreiber_verified"]),
        vnb_dashboard_access=bool(fields["vnb_dashboard_access"]),
    )


class UpdateMeRequest(BaseModel):
    full_name: str | None = Field(default=None, max_length=120)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=8, max_length=128)
    new_password: str = Field(..., min_length=12, max_length=128)


@router.get("/me", response_model=MeResponse)
def me(current_user: User = Depends(get_current_user)) -> MeResponse:
    return _me_response(current_user)


@router.patch("/me", response_model=MeResponse)
def patch_me(
    req: UpdateMeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_csrf),
) -> MeResponse:
    updated = update_me(db, current_user, full_name=req.full_name, role=None)
    return _me_response(updated)


@router.patch("/me/password")
def patch_password(
    req: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_csrf),
) -> dict[str, str]:
    change_password(db, current_user, current_password=req.current_password, new_password=req.new_password)
    return {"status": "ok"}


# -----------------------------------------------------------------------------
# DSGVO Self-Service (Art. 15/20 Datenexport, Art. 17 Konto-Loeschung)
# -----------------------------------------------------------------------------


class DeleteAccountRequest(BaseModel):
    confirm_password: str = Field(..., min_length=1, max_length=128)


@router.post("/me/data-export")
def post_data_export(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_csrf),
) -> RawResponse:
    """DSGVO Art. 15/20: Synchroner Datenexport als ZIP.

    Rate-Limit: 1 Export pro 24h pro User (Admins ausgenommen).
    Audit-Eintrag: `dsgvo_export_requested` ueber RevisionRecord-Hash-Chain.
    """
    if (current_user.role or "").strip().lower() != "admin":
        enforce_rate_limit(
            f"dsgvo:export:user:{current_user.id}",
            limit=1,
            window_seconds=24 * 60 * 60,
            message="Datenexport bereits angefordert",
            hint="Pro Konto ist nur ein Export je 24 Stunden vorgesehen. Bitte spaeter erneut versuchen.",
        )
    payload = build_user_export_zip(current_user.id, db)
    record_export_audit(db, current_user, request_ip=get_client_ip(request))
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    filename = f"gridcheck_export_{current_user.id}_{timestamp}.zip"
    return RawResponse(
        content=payload,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(payload)),
            "Cache-Control": "no-store",
        },
    )


@router.post("/me/delete-account")
def post_delete_account(
    req: DeleteAccountRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_csrf),
) -> Response:
    """DSGVO Art. 17: Soft-Delete + Anonymisierung + Audit.

    Kein Hard-Delete (Rule 05 Revisionssicherheit). Cookies/Tokens werden
    serverseitig durch `is_active=False` + `deleted_at` ungueltig; zusaetzlich
    werden die Auth-Cookies hier sofort geloescht.
    """
    enforce_rate_limit(
        f"dsgvo:delete:user:{current_user.id}",
        limit=5,
        window_seconds=60 * 60,
        message="Zu viele Loeschversuche",
        hint="Bitte spaeter erneut versuchen.",
    )
    delete_user_account(
        current_user.id,
        req.confirm_password,
        db,
        request_ip=get_client_ip(request),
    )
    raw_response = Response(status_code=204)
    for cookie_name in (
        settings.auth_access_cookie,
        settings.auth_refresh_cookie,
        settings.auth_csrf_cookie,
    ):
        raw_response.delete_cookie(cookie_name, path="/")
    return raw_response
