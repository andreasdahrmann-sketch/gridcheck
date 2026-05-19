from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.auth import require_csrf
from core.rate_limit import enforce_scoped_rate_limit
from core.vnb_access import require_verified_netzbetreiber_comms
from db.database import get_db
from db.models import User
from services.vnb_comms_service import (
    VNB_MESSAGE_CATEGORIES,
    append_thread_message,
    create_thread_with_message,
    get_thread_detail,
    list_austausch_threads,
)

router = APIRouter(prefix="/api/v1/vnb/comms", tags=["vnb-comms"])


class VnbThreadSummary(BaseModel):
    id: int
    board_scope: str
    title: str
    category: str
    target_vnb_region: str | None = None
    created_by_user_id: int
    created_at: object
    last_message_at: object | None = None
    message_count: int
    last_message_preview: str | None = None


class VnbMessageItem(BaseModel):
    id: int
    thread_id: int
    sender_user_id: int
    body: str
    created_at: object


class VnbThreadDetail(VnbThreadSummary):
    messages: list[VnbMessageItem]


class CreateThreadRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    category: str = Field(..., description=f"Eine von: {', '.join(sorted(VNB_MESSAGE_CATEGORIES))}")
    body: str = Field(..., min_length=3, max_length=8000)
    target_vnb_region: str | None = Field(default=None, max_length=80)


class CreateMessageRequest(BaseModel):
    body: str = Field(..., min_length=3, max_length=8000)


def _enforce_write_rate_limit(request: Request, current_user: User) -> None:
    enforce_scoped_rate_limit(
        "vnb_comms_write",
        request=request,
        current_user=current_user,
        user_limit=60,
        ip_limit=120,
        window_seconds=3600,
        message="Zu viele NB-Austausch-Nachrichten",
        hint="Bitte die Sendefrequenz reduzieren und spaeter erneut versuchen.",
    )


@router.get("/threads", response_model=list[VnbThreadSummary])
def list_threads(
    limit: int = Query(default=100, ge=1, le=200),
    db: Session = Depends(get_db),
    _: User = Depends(require_verified_netzbetreiber_comms),
) -> list[dict]:
    return list_austausch_threads(db, limit=limit)


@router.post("/threads", response_model=VnbThreadDetail)
def post_thread(
    req: CreateThreadRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_verified_netzbetreiber_comms),
    __csrf: None = Depends(require_csrf),
) -> dict:
    _enforce_write_rate_limit(request, current_user)
    return create_thread_with_message(
        db,
        current_user,
        title=req.title,
        category=req.category,
        body=req.body,
        target_vnb_region=req.target_vnb_region,
    )


@router.get("/threads/{thread_id}", response_model=VnbThreadDetail)
def get_thread(
    thread_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_verified_netzbetreiber_comms),
) -> dict:
    return get_thread_detail(db, thread_id)


@router.post("/threads/{thread_id}/messages", response_model=VnbThreadDetail)
def post_message(
    thread_id: int,
    req: CreateMessageRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_verified_netzbetreiber_comms),
    __csrf: None = Depends(require_csrf),
) -> dict:
    _enforce_write_rate_limit(request, current_user)
    return append_thread_message(db, current_user, thread_id=thread_id, body=req.body)
