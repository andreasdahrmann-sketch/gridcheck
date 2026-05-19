from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.auth import get_current_user, require_csrf
from core.vnb_access import user_to_vnb_access_fields
from db.database import get_db
from db.models import User
from services.user_service import change_password, update_me

router = APIRouter(prefix="/api/v1/users", tags=["users"])


class MeResponse(BaseModel):
    id: int
    email: str
    role: str
    full_name: str | None
    vnb_verification_status: str = "none"
    netzbetreiber_verified: bool = False


def _me_response(user: User) -> MeResponse:
    fields = user_to_vnb_access_fields(user)
    return MeResponse(
        id=user.id,
        email=user.email,
        role=user.role,
        full_name=user.full_name,
        vnb_verification_status=str(fields["vnb_verification_status"]),
        netzbetreiber_verified=bool(fields["netzbetreiber_verified"]),
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
