from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from db.models import ConversionEvent, User

KNOWN_CONVERSION_EVENTS = frozenset(
    {
        "page_view_product",
        "checkout_started",
        "checkout_completed",
        "analysis_completed",
        "report_exported",
    }
)


def _json_text(payload: dict[str, Any] | None) -> str:
    return json.dumps(payload or {}, sort_keys=True, default=str)


def record_conversion_event(
    db: Session,
    *,
    event_name: str,
    user_id: int | None = None,
    session_id: str | None = None,
    properties: dict[str, Any] | None = None,
) -> ConversionEvent:
    record = ConversionEvent(
        user_id=user_id,
        event_name=event_name,
        session_id=session_id,
        properties_json=_json_text(properties),
    )
    db.add(record)
    return record


def conversion_summary_last_days(db: Session, *, days: int = 7) -> dict[str, int]:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    rows = (
        db.query(ConversionEvent.event_name, func.count(ConversionEvent.id))
        .filter(ConversionEvent.created_at >= since)
        .group_by(ConversionEvent.event_name)
        .all()
    )
    summary = {name: 0 for name in KNOWN_CONVERSION_EVENTS}
    for event_name, count in rows:
        summary[str(event_name)] = int(count)
    return summary


def track_checkout_started(
    db: Session,
    user: User,
    *,
    offer_id: str,
    checkout_session_id: str | None,
) -> None:
    record_conversion_event(
        db,
        user_id=user.id,
        event_name="checkout_started",
        session_id=checkout_session_id,
        properties={"offer_id": offer_id},
    )


def track_checkout_completed(
    db: Session,
    user: User,
    *,
    offer_id: str | None,
    checkout_session_id: str | None,
    payment_status: str | None = None,
) -> None:
    record_conversion_event(
        db,
        user_id=user.id,
        event_name="checkout_completed",
        session_id=checkout_session_id,
        properties={
            "offer_id": offer_id,
            "payment_status": payment_status,
        },
    )


def track_analysis_completed(
    db: Session,
    user: User,
    *,
    analysis_run_id: int,
    project_id: int | None,
    offer_id: str | None,
    source: str,
) -> None:
    record_conversion_event(
        db,
        user_id=user.id,
        event_name="analysis_completed",
        properties={
            "analysis_run_id": analysis_run_id,
            "project_id": project_id,
            "offer_id": offer_id,
            "source": source,
        },
    )


def track_report_exported(
    db: Session,
    user: User,
    *,
    report_type: str,
    output_format: str,
    report_revision_uuid: str | None,
    analysis_run_id: Any = None,
) -> None:
    record_conversion_event(
        db,
        user_id=user.id,
        event_name="report_exported",
        properties={
            "report_type": report_type,
            "output_format": output_format,
            "report_revision_uuid": report_revision_uuid,
            "analysis_run_id": analysis_run_id,
        },
    )
