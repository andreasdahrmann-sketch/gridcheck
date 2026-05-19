from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from db.models import User, VnbMessage, VnbMessageAudit, VnbThread, make_checksum

VNB_COMMS_BOARD_AUSTAUSCH = "austausch"

VNB_MESSAGE_CATEGORIES = frozenset(
    {
        "kapazitaetshinweis",
        "redispatch",
        "infrastruktur",
        "sonstiges",
    }
)

_CAPACITY_CLAIM_PATTERNS = re.compile(
    r"(freie\s+kapazit|kapazit[aä]t\s+verf[uü]gbar|garantiert\s+anschluss|anschluss\s+zugesagt|"
    r"netzanschluss\s+gesichert|unbegrenzt\s+verf[uü]gbar)",
    re.IGNORECASE,
)
_EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
_PHONE_PATTERN = re.compile(r"(?:\+49|0)\s*\d[\d\s/-]{8,}")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def validate_message_body(body: str) -> str:
    cleaned = body.strip()
    if len(cleaned) < 3:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "VNB_MESSAGE_TOO_SHORT",
                "message": "Nachricht ist zu kurz.",
                "hint": "Mindestens 3 Zeichen eingeben.",
            },
        )
    if len(cleaned) > 8000:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "VNB_MESSAGE_TOO_LONG",
                "message": "Nachricht ist zu lang.",
                "hint": "Maximal 8000 Zeichen.",
            },
        )
    if _EMAIL_PATTERN.search(cleaned) or _PHONE_PATTERN.search(cleaned):
        raise HTTPException(
            status_code=422,
            detail={
                "code": "VNB_MESSAGE_PII",
                "message": "Nachricht enthaelt offenbar personenbezogene Kontaktdaten.",
                "hint": "Keine E-Mail- oder Telefonnummern von Endkunden ohne dokumentierte Rechtsgrundlage.",
            },
        )
    if _CAPACITY_CLAIM_PATTERNS.search(cleaned):
        raise HTTPException(
            status_code=422,
            detail={
                "code": "VNB_MESSAGE_CAPACITY_CLAIM",
                "message": "Nachricht darf keine Kapazitaets- oder Anschlusszusage enthalten.",
                "hint": "Nur Hinweise und fachlichen Austausch ohne verbindliche Kapazitaetsaussagen.",
            },
        )
    return cleaned


def _normalize_category(category: str) -> str:
    key = str(category or "").strip().lower()
    if key not in VNB_MESSAGE_CATEGORIES:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "VNB_CATEGORY_INVALID",
                "message": "Ungueltige Kategorie.",
                "hint": "Erlaubt: kapazitaetshinweis, redispatch, infrastruktur, sonstiges.",
            },
        )
    return key


def _append_message_audit(
    db: Session,
    *,
    message: VnbMessage,
    actor: User,
    event_type: str = "message_created",
) -> VnbMessageAudit:
    payload: dict[str, Any] = {
        "message_id": message.id,
        "thread_id": message.thread_id,
        "sender_user_id": message.sender_user_id,
        "body": message.body,
        "created_at": message.created_at.isoformat() if message.created_at else None,
        "event_type": event_type,
    }
    audit = VnbMessageAudit(
        message_id=message.id,
        event_type=event_type,
        actor_user_id=actor.id,
        payload_json=json.dumps(payload, ensure_ascii=False, default=str),
        checksum=make_checksum(payload),
        created_at=_utcnow(),
    )
    db.add(audit)
    return audit


def _thread_to_dict(thread: VnbThread, *, message_count: int, last_preview: str | None) -> dict[str, Any]:
    return {
        "id": thread.id,
        "board_scope": thread.board_scope,
        "title": thread.title,
        "category": thread.category,
        "target_vnb_region": thread.target_vnb_region,
        "created_by_user_id": thread.created_by_user_id,
        "created_at": thread.created_at,
        "last_message_at": thread.last_message_at,
        "message_count": message_count,
        "last_message_preview": last_preview,
    }


def list_austausch_threads(db: Session, *, limit: int = 100) -> list[dict[str, Any]]:
    threads = (
        db.query(VnbThread)
        .filter(VnbThread.board_scope == VNB_COMMS_BOARD_AUSTAUSCH)
        .order_by(VnbThread.last_message_at.desc().nullslast(), VnbThread.created_at.desc())
        .limit(limit)
        .all()
    )
    out: list[dict[str, Any]] = []
    for thread in threads:
        messages = (
            db.query(VnbMessage)
            .filter(VnbMessage.thread_id == thread.id)
            .order_by(VnbMessage.created_at.desc())
            .limit(1)
            .all()
        )
        preview = None
        if messages:
            body = messages[0].body or ""
            preview = body[:160] + ("…" if len(body) > 160 else "")
        count = db.query(VnbMessage).filter(VnbMessage.thread_id == thread.id).count()
        out.append(_thread_to_dict(thread, message_count=count, last_preview=preview))
    return out


def get_thread_detail(db: Session, thread_id: int) -> dict[str, Any]:
    thread = (
        db.query(VnbThread)
        .filter(VnbThread.id == thread_id, VnbThread.board_scope == VNB_COMMS_BOARD_AUSTAUSCH)
        .first()
    )
    if not thread:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "VNB_THREAD_NOT_FOUND",
                "message": "Thread nicht gefunden.",
                "hint": "Nur Threads im NB-Austausch-Board sind sichtbar.",
            },
        )
    messages = (
        db.query(VnbMessage)
        .filter(VnbMessage.thread_id == thread.id)
        .order_by(VnbMessage.created_at.asc())
        .all()
    )
    count = len(messages)
    preview = messages[-1].body[:160] if messages else None
    return {
        **_thread_to_dict(thread, message_count=count, last_preview=preview),
        "messages": [
            {
                "id": m.id,
                "thread_id": m.thread_id,
                "sender_user_id": m.sender_user_id,
                "body": m.body,
                "created_at": m.created_at,
            }
            for m in messages
        ],
    }


def create_thread_with_message(
    db: Session,
    actor: User,
    *,
    title: str,
    category: str,
    body: str,
    target_vnb_region: str | None = None,
) -> dict[str, Any]:
    cleaned_title = title.strip()
    if len(cleaned_title) < 3:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "VNB_THREAD_TITLE_INVALID",
                "message": "Betreff ist zu kurz.",
                "hint": "Mindestens 3 Zeichen.",
            },
        )
    if len(cleaned_title) > 200:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "VNB_THREAD_TITLE_INVALID",
                "message": "Betreff ist zu lang.",
                "hint": "Maximal 200 Zeichen.",
            },
        )

    now = _utcnow()
    thread = VnbThread(
        board_scope=VNB_COMMS_BOARD_AUSTAUSCH,
        title=cleaned_title,
        category=_normalize_category(category),
        target_vnb_region=(target_vnb_region.strip()[:80] if target_vnb_region and target_vnb_region.strip() else None),
        created_by_user_id=actor.id,
        created_at=now,
        last_message_at=now,
    )
    db.add(thread)
    db.flush()

    message = VnbMessage(
        thread_id=thread.id,
        sender_user_id=actor.id,
        body=validate_message_body(body),
        created_at=now,
    )
    db.add(message)
    db.flush()
    _append_message_audit(db, message=message, actor=actor)
    db.commit()
    db.refresh(thread)
    return get_thread_detail(db, thread.id)


def append_thread_message(db: Session, actor: User, *, thread_id: int, body: str) -> dict[str, Any]:
    thread = (
        db.query(VnbThread)
        .filter(VnbThread.id == thread_id, VnbThread.board_scope == VNB_COMMS_BOARD_AUSTAUSCH)
        .first()
    )
    if not thread:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "VNB_THREAD_NOT_FOUND",
                "message": "Thread nicht gefunden.",
                "hint": "Thread existiert nicht im Austausch-Board.",
            },
        )

    now = _utcnow()
    message = VnbMessage(
        thread_id=thread.id,
        sender_user_id=actor.id,
        body=validate_message_body(body),
        created_at=now,
    )
    db.add(message)
    thread.last_message_at = now
    db.flush()
    _append_message_audit(db, message=message, actor=actor)
    db.commit()
    return get_thread_detail(db, thread.id)
