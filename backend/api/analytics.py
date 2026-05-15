from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from core.auth import get_current_user, require_admin_user
from db.database import get_db
from db.models import User
from services.conversion_tracking_service import (
    KNOWN_CONVERSION_EVENTS,
    conversion_summary_last_days,
    record_conversion_event,
)

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


class ConversionEventRequest(BaseModel):
    event_name: str = Field(..., min_length=1, max_length=128)
    properties: dict[str, Any] = Field(default_factory=dict)
    session_id: str | None = Field(default=None, max_length=128)

    @field_validator("event_name")
    @classmethod
    def validate_event_name(cls, value: str) -> str:
        normalized = value.strip()
        if normalized not in KNOWN_CONVERSION_EVENTS:
            raise ValueError(f"Unbekanntes Event. Erlaubt: {', '.join(sorted(KNOWN_CONVERSION_EVENTS))}")
        return normalized


class ConversionEventResponse(BaseModel):
    id: int
    event_name: str
    session_id: str | None
    created_at: str


class ConversionSummaryResponse(BaseModel):
    window_days: int
    counts: dict[str, int]


@router.post("/events", response_model=ConversionEventResponse)
def post_conversion_event(
    req: ConversionEventRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ConversionEventResponse:
    record = record_conversion_event(
        db,
        user_id=current_user.id,
        event_name=req.event_name,
        session_id=req.session_id,
        properties=req.properties,
    )
    db.commit()
    db.refresh(record)
    return ConversionEventResponse(
        id=record.id,
        event_name=record.event_name,
        session_id=record.session_id,
        created_at=record.created_at.isoformat() if record.created_at else "",
    )


@router.get("/summary", response_model=ConversionSummaryResponse)
def conversion_summary(
    days: int = 7,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin_user),
) -> ConversionSummaryResponse:
    window = max(1, min(days, 90))
    return ConversionSummaryResponse(
        window_days=window,
        counts=conversion_summary_last_days(db, days=window),
    )
