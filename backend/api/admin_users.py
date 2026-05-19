from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core.auth import require_admin_user, require_csrf
from core.vnb_access import user_to_vnb_access_fields
from db.database import get_db
from db.models import User
from services.auth_service import approve_netzbetreiber

router = APIRouter(prefix="/api/v1/admin/users", tags=["admin-users"])


class AdminUserVnbResponse(BaseModel):
    id: int
    email: str
    role: str
    full_name: str | None
    vnb_verification_status: str
    netzbetreiber_verified: bool


@router.post("/{user_id}/approve-netzbetreiber", response_model=AdminUserVnbResponse)
def approve_netzbetreiber_user(
    user_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin_user),
    __: None = Depends(require_csrf),
) -> AdminUserVnbResponse:
    user = approve_netzbetreiber(db, user_id=user_id)
    fields = user_to_vnb_access_fields(user)
    return AdminUserVnbResponse(
        id=user.id,
        email=user.email,
        role=user.role,
        full_name=user.full_name,
        vnb_verification_status=str(fields["vnb_verification_status"]),
        netzbetreiber_verified=bool(fields["netzbetreiber_verified"]),
    )
