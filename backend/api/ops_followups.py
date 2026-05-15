from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.auth import require_admin_user, require_csrf
from db.database import get_db
from db.models import User
from services.billing_service import claim_ops_followup, list_ops_followups_admin, update_ops_followup_status

router = APIRouter(prefix="/api/v1/ops-followups", tags=["ops-followups"])


class OpsFollowupResponse(BaseModel):
    entitlement_id: int
    offer_id: str
    package_scope: str
    status: str
    ops_status: str
    express_requested: bool
    checkout_session_id: str | None = None
    remaining_credits: int | None = None
    customer_user_id: int
    customer_email: str | None = None
    customer_name: str | None = None
    project_name: str | None = None
    analysis_run_id: int | None = None
    analysis_created_at: datetime | None = None
    ops_assignee_user_id: int | None = None
    ops_assignee_email: str | None = None
    ops_assignee_name: str | None = None
    ops_assigned_at: datetime | None = None
    ops_started_at: datetime | None = None
    ops_completed_at: datetime | None = None
    ops_last_comment: str | None = None
    updated_at: datetime | None = None
    next_action: str


class OpsClaimRequest(BaseModel):
    comment: str | None = Field(default=None, max_length=2000)


class OpsStatusUpdateRequest(BaseModel):
    status: str = Field(..., pattern="^(in_progress|completed)$")
    comment: str | None = Field(default=None, max_length=2000)


@router.get("", response_model=list[OpsFollowupResponse])
def list_followups(
    include_completed: bool = Query(default=False),
    assigned_to_me: bool = Query(default=False),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin_user),
) -> list[dict]:
    return list_ops_followups_admin(
        db,
        include_completed=include_completed,
        assigned_to_me_user_id=admin_user.id if assigned_to_me else None,
        limit=limit,
    )


@router.post("/{entitlement_id}/claim", response_model=OpsFollowupResponse)
def claim_followup(
    entitlement_id: int,
    req: OpsClaimRequest,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin_user),
    _: None = Depends(require_csrf),
) -> dict:
    return claim_ops_followup(db, admin_user, entitlement_id=entitlement_id, comment=req.comment)


@router.patch("/{entitlement_id}", response_model=OpsFollowupResponse)
def update_followup(
    entitlement_id: int,
    req: OpsStatusUpdateRequest,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin_user),
    _: None = Depends(require_csrf),
) -> dict:
    return update_ops_followup_status(
        db,
        admin_user,
        entitlement_id=entitlement_id,
        new_status=req.status,
        comment=req.comment,
    )
