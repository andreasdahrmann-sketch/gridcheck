"""DSGVO Self-Service: Datenexport (Art. 15/20) und Konto-Loeschung (Art. 17).

Architektur-Notizen
-------------------
- KEIN Hard-Delete. Revisionssicherheit (Rule 05) verbietet stille Loeschung
  von User-Datensaetzen, die in Audit-Hash-Ketten oder Abrechnungsvorgaengen
  referenziert sind. Stattdessen: Soft-Delete (`deleted_at`), E-Mail anonymisiert,
  Passwort-Hash entfernt, `is_active=false`.
- Re-Registrierung wird ueber `deleted_email_hash` (SHA256 der Original-E-Mail)
  gesperrt; Klartext bleibt nach Anonymisierung nicht erhalten.
- Audit-Eintrag pro DSGVO-Aktion ueber `engine.revision.speichere_revision`
  (RevisionRecord, Hash-Chain).
- Export-ZIP wird synchron erzeugt (MVP). Falls Performance leidet, kann das
  spaeter in einen Worker ausgelagert werden (siehe Bericht).
"""

from __future__ import annotations

import hashlib
import io
import json
import zipfile
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from core.auth import verify_password
from core.security_log import log_security_event
from db.models import (
    AnalysisRun,
    AuditLog,
    BillingEntitlement,
    BillingEvent,
    CheckResult,
    PasswordResetToken,
    Project,
    RevisionRecord,
    User,
)
from engine.revision import speichere_revision


EXPORT_SCHEMA_VERSION = "dsgvo-export-1.0"


# -----------------------------------------------------------------------------
# Hilfsfunktionen
# -----------------------------------------------------------------------------


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


def _safe_json_parse(raw: str | None) -> Any:
    if not raw:
        return None
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return raw


def _email_hash(email: str) -> str:
    return hashlib.sha256(email.strip().lower().encode("utf-8")).hexdigest()


# -----------------------------------------------------------------------------
# Datenexport (Art. 15/20)
# -----------------------------------------------------------------------------


def _collect_account(user: User) -> dict[str, Any]:
    return {
        "id": user.id,
        "email": user.email,
        "role": user.role,
        "full_name": user.full_name,
        "is_active": bool(user.is_active),
        "vnb_verification_status": user.vnb_verification_status,
        "plan_tier": user.plan_tier,
        "billing_status": user.billing_status,
        "billing_current_period_end": _iso(user.billing_current_period_end),
        "stripe_customer_id": user.stripe_customer_id,
        "stripe_subscription_id": user.stripe_subscription_id,
        "stripe_price_id": user.stripe_price_id,
        "created_at": _iso(user.created_at),
        "updated_at": _iso(user.updated_at),
        "deleted_at": _iso(user.deleted_at),
    }


def _collect_projects(db: Session, user_id: int) -> list[dict[str, Any]]:
    projects = (
        db.query(Project)
        .filter(Project.owner_user_id == user_id)
        .order_by(Project.id.asc())
        .all()
    )
    items: list[dict[str, Any]] = []
    for project in projects:
        items.append(
            {
                "id": project.id,
                "name": project.name,
                "typ": project.typ,
                "plz": project.plz,
                "ort": project.ort,
                "street": project.street,
                "house_number": project.house_number,
                "city": project.city,
                "latitude": project.latitude,
                "longitude": project.longitude,
                "leistung_kw": project.leistung_kw,
                "spannung_kv": project.spannung_kv,
                "einspeiseart": project.einspeiseart,
                "skv_mva": project.skv_mva,
                "bestehende_einspeisung_kw": project.bestehende_einspeisung_kw,
                "leitungstyp": project.leitungstyp,
                "leitungslaenge_km": project.leitungslaenge_km,
                "role": project.role,
                "role_inputs": _safe_json_parse(project.role_inputs),
                "role_results": _safe_json_parse(project.role_results),
                "description": project.description,
                "created_at": _iso(project.created_at),
                "updated_at": _iso(project.updated_at),
                "deleted_at": _iso(project.deleted_at),
            }
        )
    return items


def _collect_reports(db: Session, user_id: int) -> dict[str, Any]:
    project_ids = [
        pid
        for (pid,) in db.query(Project.id).filter(Project.owner_user_id == user_id).all()
    ]
    check_results: list[dict[str, Any]] = []
    if project_ids:
        for row in (
            db.query(CheckResult)
            .filter(CheckResult.project_id.in_(project_ids))
            .order_by(CheckResult.id.asc())
            .all()
        ):
            check_results.append(
                {
                    "id": row.id,
                    "project_id": row.project_id,
                    "score": row.score,
                    "spannungsband_ok": row.spannungsband_ok,
                    "thermische_auslastung_ok": row.thermische_auslastung_ok,
                    "kurzschluss_ok": row.kurzschluss_ok,
                    "n1_ok": row.n1_ok,
                    "netzebene": row.netzebene,
                    "empfehlung": row.empfehlung,
                    "details": _safe_json_parse(row.details),
                    "created_at": _iso(row.created_at),
                }
            )

    analysis_runs: list[dict[str, Any]] = []
    for row in (
        db.query(AnalysisRun)
        .filter(AnalysisRun.user_id == user_id)
        .order_by(AnalysisRun.id.asc())
        .all()
    ):
        analysis_runs.append(
            {
                "id": row.id,
                "project_id": row.project_id,
                "source": row.source,
                "status": row.status,
                "score": row.score,
                "decision_code": row.decision_code,
                "package_scope": row.package_scope,
                "usage_bucket": row.usage_bucket,
                "billing_category": row.billing_category,
                "revision_hash": row.revision_hash,
                "result": _safe_json_parse(row.result_json),
                "input": _safe_json_parse(row.input_json),
                "created_at": _iso(row.created_at),
            }
        )

    return {"check_results": check_results, "analysis_runs": analysis_runs}


def _collect_audit(db: Session, user_id: int) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    project_ids = [
        pid
        for (pid,) in db.query(Project.id).filter(Project.owner_user_id == user_id).all()
    ]
    if project_ids:
        for row in (
            db.query(AuditLog)
            .filter(AuditLog.project_id.in_(project_ids))
            .order_by(AuditLog.id.asc())
            .all()
        ):
            items.append(
                {
                    "source": "audit_log",
                    "id": row.id,
                    "project_id": row.project_id,
                    "action": row.action,
                    "detail": _safe_json_parse(row.detail),
                    "checksum": row.checksum,
                    "timestamp": _iso(row.timestamp),
                }
            )
    for row in (
        db.query(RevisionRecord)
        .filter(RevisionRecord.actor_user_id == user_id)
        .order_by(RevisionRecord.id.asc())
        .all()
    ):
        items.append(
            {
                "source": "revision_records",
                "id": row.id,
                "revisionsnummer": int(row.revisionsnummer),
                "uuid": row.uuid,
                "schema_version": row.schema_version,
                "engine_version": row.engine_version,
                "previous_hash": row.previous_hash,
                "hash": row.hash,
                "action_type": row.action_type,
                "project_id": row.project_id,
                "timestamp": _iso(row.timestamp),
                "data": _safe_json_parse(row.data_json),
            }
        )
    return items


def _collect_billing(db: Session, user_id: int) -> dict[str, list[dict[str, Any]]]:
    events: list[dict[str, Any]] = []
    for row in (
        db.query(BillingEvent)
        .filter(BillingEvent.user_id == user_id)
        .order_by(BillingEvent.id.asc())
        .all()
    ):
        events.append(
            {
                "id": row.id,
                "provider": row.provider,
                "event_type": row.event_type,
                "status": row.status,
                "amount_cents": row.amount_cents,
                "currency": row.currency,
                "checkout_session_id": row.checkout_session_id,
                "provider_customer_id": row.provider_customer_id,
                "provider_subscription_id": row.provider_subscription_id,
                "provider_event_id": row.provider_event_id,
                "payload": _safe_json_parse(row.payload_json),
                "created_at": _iso(row.created_at),
            }
        )
    entitlements: list[dict[str, Any]] = []
    for row in (
        db.query(BillingEntitlement)
        .filter(BillingEntitlement.user_id == user_id)
        .order_by(BillingEntitlement.id.asc())
        .all()
    ):
        entitlements.append(
            {
                "id": row.id,
                "offer_id": row.offer_id,
                "offer_category": row.offer_category,
                "package_scope": row.package_scope,
                "source": row.source,
                "status": row.status,
                "total_credits": row.total_credits,
                "used_credits": row.used_credits,
                "valid_from": _iso(row.valid_from),
                "valid_until": _iso(row.valid_until),
                "checkout_session_id": row.checkout_session_id,
                "stripe_price_id": row.stripe_price_id,
                "stripe_payment_intent_id": row.stripe_payment_intent_id,
                "stripe_subscription_id": row.stripe_subscription_id,
                "metadata": _safe_json_parse(row.metadata_json),
                "created_at": _iso(row.created_at),
                "updated_at": _iso(row.updated_at),
            }
        )
    return {"billing_events": events, "billing_entitlements": entitlements}


def _readme_text(user_id: int, generated_at: str) -> str:
    return (
        "# GridCheck DSGVO-Datenexport\n\n"
        f"User-ID: {user_id}\n"
        f"Erzeugt: {generated_at} (UTC)\n"
        f"Export-Schema: {EXPORT_SCHEMA_VERSION}\n\n"
        "## Inhalt\n\n"
        "- `account.json` — Konto-Stammdaten (ohne Passwort-Hash).\n"
        "- `projects.json` — alle Projekte (auch soft-geloeschte), Stammdaten und Geo-Inputs.\n"
        "- `reports.json` — Check-Ergebnisse und Analyseläufe.\n"
        "- `audit_log.json` — Audit-/Revisionseintraege mit Hash-Chain-Verweisen.\n"
        "- `billing.json` — Billing-Events und Berechtigungen (sofern vorhanden).\n\n"
        "## Rechtliche Hinweise\n\n"
        "Dieser Export erfuellt das Auskunftsrecht (Art. 15 DSGVO) und das Recht auf\n"
        "Datenuebertragbarkeit (Art. 20 DSGVO).\n\n"
        "Eine Konto-Loeschung erfolgt aus Gruenden der Revisionssicherheit (Aufbewahrungs-\n"
        "pflichten nach HGB/AO 6-10 Jahre fuer abrechnungs- und buchhaltungsrelevante Daten)\n"
        "als Soft-Delete: das Konto wird anonymisiert und deaktiviert, der Datensatz selbst\n"
        "bleibt jedoch fuer Audit-Trail und Hash-Chain bestehen. Das ist DSGVO-konform,\n"
        "weil ein berechtigtes Interesse an Nachvollziehbarkeit (Art. 6 Abs. 1 lit. c/f DSGVO\n"
        "i.V.m. § 257 HGB / § 147 AO) besteht.\n"
    )


def build_user_export_zip(user_id: int, db: Session) -> bytes:
    """Erzeugt ein ZIP mit den DSGVO-relevanten Daten des Nutzers.

    Wirft `HTTPException(404)` falls der Nutzer nicht existiert oder bereits
    DSGVO-geloescht ist (Soft-Delete sperrt ihn).
    """
    user = db.query(User).filter(User.id == user_id).first()
    if user is None or user.deleted_at is not None:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "USER_NOT_FOUND",
                "message": "Benutzer nicht gefunden",
                "hint": "Bitte erneut anmelden oder Support kontaktieren.",
            },
        )

    generated_at = datetime.now(timezone.utc).isoformat()
    payload_account = _collect_account(user)
    payload_projects = _collect_projects(db, user_id)
    payload_reports = _collect_reports(db, user_id)
    payload_audit = _collect_audit(db, user_id)
    payload_billing = _collect_billing(db, user_id)

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("README.md", _readme_text(user_id, generated_at))
        zf.writestr(
            "account.json",
            json.dumps(
                {"schema": EXPORT_SCHEMA_VERSION, "generated_at": generated_at, "account": payload_account},
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            ),
        )
        zf.writestr(
            "projects.json",
            json.dumps(
                {"schema": EXPORT_SCHEMA_VERSION, "generated_at": generated_at, "projects": payload_projects},
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            ),
        )
        zf.writestr(
            "reports.json",
            json.dumps(
                {"schema": EXPORT_SCHEMA_VERSION, "generated_at": generated_at, **payload_reports},
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            ),
        )
        zf.writestr(
            "audit_log.json",
            json.dumps(
                {"schema": EXPORT_SCHEMA_VERSION, "generated_at": generated_at, "entries": payload_audit},
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            ),
        )
        zf.writestr(
            "billing.json",
            json.dumps(
                {"schema": EXPORT_SCHEMA_VERSION, "generated_at": generated_at, **payload_billing},
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            ),
        )

    return buffer.getvalue()


def record_export_audit(db: Session, user: User, *, request_ip: str | None) -> None:
    """Schreibt einen revisionssicheren Audit-Eintrag fuer den Datenexport."""
    payload = {
        "eingabe": {
            "actor_user_id": user.id,
            "request_ip": request_ip or "unknown",
            "schema": EXPORT_SCHEMA_VERSION,
        },
        "fazit": {"action": "dsgvo_export_requested"},
    }
    try:
        speichere_revision(
            payload,
            actor_user_id=user.id,
            action_type="dsgvo_export_requested",
            db=db,
        )
        # speichere_revision committed nur, wenn es eine eigene Session besitzt.
        # Hier wurde die FastAPI-Session uebergeben, daher manuell committen.
        db.commit()
    except Exception:
        # Audit-Schreibfehler darf den Export nicht blockieren; Security-Log greift.
        db.rollback()
        log_security_event(
            "dsgvo_export_audit_failed",
            user_id=user.id,
        )
    log_security_event("dsgvo_export_requested", user_id=user.id, request_ip=request_ip or "unknown")


# -----------------------------------------------------------------------------
# Konto-Loeschung (Art. 17) — Soft-Delete + Anonymisierung
# -----------------------------------------------------------------------------


def delete_user_account(
    user_id: int,
    password_plain: str,
    db: Session,
    request_ip: str | None,
) -> None:
    """Fuehrt die Konto-Loeschung als Soft-Delete + Anonymisierung durch.

    Schritte:
    1. Passwort verifizieren.
    2. Alle aktiven Reset-Tokens invalidieren (used_at).
    3. Alle eigenen Projekte soft-loeschen (Project.deleted_at), falls noch offen.
    4. User soft-loeschen: deleted_at, deleted_email_hash, anonymisierte Email,
       password_hash="", is_active=False.
    5. Revisions-Audit + Security-Log.

    Tokens (JWT) sind kurzlebig (max. 60 min Access). Da der User nach diesem
    Schritt `is_active=False` hat und `deleted_at` gesetzt ist, akzeptiert
    `get_current_user` keinen Token mehr (siehe core/auth.py).
    """
    user = db.query(User).filter(User.id == user_id).first()
    if user is None or user.deleted_at is not None:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "USER_NOT_FOUND",
                "message": "Benutzer nicht gefunden",
                "hint": "Bitte erneut anmelden oder Support kontaktieren.",
            },
        )
    if not password_plain or not verify_password(password_plain, user.password_hash or ""):
        log_security_event("dsgvo_account_delete_password_invalid", user_id=user.id)
        raise HTTPException(
            status_code=401,
            detail={
                "code": "PASSWORD_INVALID",
                "message": "Passwort-Bestaetigung fehlgeschlagen",
                "hint": "Bitte das aktuelle Passwort eingeben.",
            },
        )

    now = datetime.now(timezone.utc)
    original_email = (user.email or "").strip().lower()
    email_hash = _email_hash(original_email) if original_email else None

    # Aktive Passwort-Reset-Tokens invalidieren.
    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id,
        PasswordResetToken.used_at.is_(None),
    ).update({"used_at": now}, synchronize_session=False)

    # Eigene Projekte soft-loeschen (Audit-Trail bleibt erhalten).
    db.query(Project).filter(
        Project.owner_user_id == user.id,
        Project.deleted_at.is_(None),
    ).update({"deleted_at": now}, synchronize_session=False)

    user.deleted_at = now
    user.deleted_email_hash = email_hash
    user.email = f"deleted_user_{user.id}@anonymized.local"
    user.password_hash = ""
    user.is_active = False
    user.full_name = None
    user.stripe_customer_id = None
    user.stripe_subscription_id = None
    user.stripe_price_id = None
    user.updated_at = now

    db.commit()

    # Revisionssicheres Audit (Hash-Chain).
    payload = {
        "eingabe": {
            "actor_user_id": user.id,
            "request_ip": request_ip or "unknown",
            "confirmation_method": "password",
        },
        "fazit": {
            "action": "dsgvo_account_deleted",
            "soft_delete": True,
            "deleted_email_hash": email_hash,
        },
    }
    try:
        speichere_revision(
            payload,
            actor_user_id=user.id,
            action_type="dsgvo_account_deleted",
            db=db,
        )
        db.commit()
    except Exception:
        db.rollback()
        log_security_event("dsgvo_account_delete_audit_failed", user_id=user.id)

    log_security_event(
        "dsgvo_account_deleted",
        user_id=user.id,
        request_ip=request_ip or "unknown",
    )
