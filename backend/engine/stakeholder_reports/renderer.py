from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Callable
from contextlib import contextmanager
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from db.database import SessionLocal
from db.models import ReportRevisionRecord

REPORT_SCHEMA_VERSION = "1.1.0"
_MAX_INSERT_RETRIES = 3
_REPORT_VERIFY_PATH_PREFIX = "/api/v2/reports/revisions"
_SOURCE_VERIFY_PATH_PREFIX = "/api/v1/revisions"
_SELF_REFERENTIAL_REPORT_KEYS = {
    "audit_hash",
    "report_generated_at",
    "report_revision",
    "report_revision_number",
    "report_revision_uuid",
    "report_verify_path",
}


def _canonical(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256(obj: Any) -> str:
    return hashlib.sha256(_canonical(obj).encode("utf-8")).hexdigest()


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


@lru_cache(maxsize=1)
def _template_env() -> Environment:
    """Cached Jinja Environment.

    perf: Environment-Erzeugung lud bisher pro Request die Templates frisch
    vom Filesystem; Jinja's eigener Cache wirkt erst, wenn die Env-Instanz
    wiederverwendet wird. Templates aendern sich nicht zur Laufzeit.
    """
    base_dir = Path(__file__).resolve().parent / "templates"
    return Environment(
        loader=FileSystemLoader(str(base_dir)),
        autoescape=select_autoescape(["html", "xml"]),
    )


def render_from_template(template_filename: str, report_data: dict[str, Any]) -> str:
    env = _template_env()
    tpl = env.get_template(template_filename)
    return tpl.render(report=report_data)


def render_projektierer_html(report_data: dict[str, Any]) -> str:
    return render_from_template("projektierer.html.j2", report_data)


def render_vnb_html(report_data: dict[str, Any]) -> str:
    return render_from_template("vnb.html.j2", report_data)


def render_invest_html(report_data: dict[str, Any]) -> str:
    return render_from_template("invest.html.j2", report_data)


def build_source_verify_path(hash_value: str | None) -> str | None:
    token = str(hash_value or "").strip().lower()
    if len(token) != 64:
        return None
    return f"{_SOURCE_VERIFY_PATH_PREFIX}/{token}"


def build_report_verify_path(hash_value: str) -> str:
    return f"{_REPORT_VERIFY_PATH_PREFIX}/{hash_value}"


def compute_report_checksum(report_data: dict[str, Any]) -> str:
    # perf: shallow copy reicht — nur Top-Level-Keys werden gepoppt,
    # _sha256/json.dumps liest die Nested-Daten anschliessend nur.
    normalized = dict(report_data)
    for key in _SELF_REFERENTIAL_REPORT_KEYS:
        normalized.pop(key, None)
    return _sha256(normalized)


def compute_html_checksum(html: str) -> str:
    return _sha256_text(html)


def compute_report_revision_hash(
    *,
    revisionsnummer: int,
    uuid_value: str,
    timestamp_iso: str,
    report_type: str,
    previous_hash: str,
    engine_revision_hash: str,
    report_checksum: str,
) -> str:
    payload = {
        "revisionsnummer": revisionsnummer,
        "uuid": uuid_value,
        "timestamp": timestamp_iso,
        "schema_version": REPORT_SCHEMA_VERSION,
        "report_type": report_type,
        "previous_hash": previous_hash,
        "engine_revision_hash": engine_revision_hash,
        "report_checksum": report_checksum,
    }
    return _sha256(payload)


def enrich_report_with_revision_metadata(
    report_data: dict[str, Any],
    *,
    revisionsnummer: int,
    uuid_value: str,
    timestamp_iso: str,
    report_hash: str,
    engine_revision_hash: str,
    report_checksum: str,
    html_checksum: str | None = None,
) -> dict[str, Any]:
    # perf: shallow copy reicht — wir setzen ausschliesslich Top-Level-Keys
    # (audit_hash, report_generated_at, report_revision, ...) und mutieren
    # keine verschachtelten Strukturen aus report_data.
    enriched = dict(report_data)
    source_revision_hash = (
        str(
            enriched.get("source_revision_hash")
            or enriched.get("engine_revision_hash")
            or ""
        ).strip()
        or None
    )
    report_verify_path = build_report_verify_path(report_hash)

    report_revision: dict[str, Any] = {
        "revisionsnummer": revisionsnummer,
        "uuid": uuid_value,
        "hash": report_hash,
        "timestamp": timestamp_iso,
        "engine_revision_hash": engine_revision_hash,
        "verify_path": report_verify_path,
        "report_checksum": report_checksum,
    }
    if html_checksum is not None:
        report_revision["html_checksum"] = html_checksum

    enriched["report_generated_at"] = timestamp_iso
    enriched["audit_hash"] = report_hash
    enriched["report_revision_number"] = revisionsnummer
    enriched["report_revision_uuid"] = uuid_value
    enriched["report_verify_path"] = report_verify_path
    enriched["report_revision"] = report_revision

    if source_revision_hash is not None:
        enriched["source_revision_hash"] = source_revision_hash
        source_verify_path = build_source_verify_path(source_revision_hash)
        if source_verify_path is not None:
            enriched["source_verify_path"] = source_verify_path

    return enriched


def verify_report_revision_record(record: ReportRevisionRecord) -> dict[str, Any]:
    try:
        report_data = json.loads(record.report_json)
    except json.JSONDecodeError:
        return {
            "ok": False,
            "report_hash_matches": False,
            "report_checksum_matches": False,
            "html_checksum_matches": False,
            "report_data": None,
        }

    if not isinstance(report_data, dict):
        return {
            "ok": False,
            "report_hash_matches": False,
            "report_checksum_matches": False,
            "html_checksum_matches": False,
            "report_data": report_data,
        }

    revision_meta = report_data.get("report_revision")
    timestamp_iso = record.timestamp.isoformat()
    if isinstance(revision_meta, dict):
        embedded_ts = revision_meta.get("timestamp")
        if isinstance(embedded_ts, str) and embedded_ts.strip():
            # Persistenz nutzt diesen String fuer den Report-Hash; bei TIMESTAMP ohne TZ
            # weicht record.timestamp.isoformat() nach DB-Roundtrip davon ab.
            timestamp_iso = embedded_ts.strip()

    report_checksum = compute_report_checksum(report_data)
    expected_hash = compute_report_revision_hash(
        revisionsnummer=int(record.revisionsnummer),
        uuid_value=record.uuid,
        timestamp_iso=timestamp_iso,
        report_type=record.report_type,
        previous_hash=record.previous_hash,
        engine_revision_hash=record.engine_revision_hash,
        report_checksum=report_checksum,
    )

    stored_report_checksum = (
        revision_meta.get("report_checksum")
        if isinstance(revision_meta, dict)
        else None
    )
    stored_html_checksum = (
        revision_meta.get("html_checksum") if isinstance(revision_meta, dict) else None
    )
    actual_html_checksum = compute_html_checksum(record.html_content)
    report_hash_matches = expected_hash == record.hash
    report_checksum_matches = stored_report_checksum in {None, report_checksum}
    html_checksum_matches = stored_html_checksum in {None, actual_html_checksum}

    return {
        "ok": report_hash_matches and report_checksum_matches and html_checksum_matches,
        "report_hash_matches": report_hash_matches,
        "report_checksum_matches": report_checksum_matches,
        "html_checksum_matches": html_checksum_matches,
        "report_checksum": report_checksum,
        "html_checksum": actual_html_checksum,
        "report_data": report_data,
    }


@contextmanager
def _session_scope(db: Session | None):
    if db is not None:
        yield db, False
        return
    session = SessionLocal()
    try:
        yield session, True
    finally:
        session.close()


def persist_report_revision(
    report_data: dict[str, Any],
    html: str | Callable[[dict[str, Any]], str],
    engine_revision_hash: str,
    report_type: str = "projektierer",
    db: Session | None = None,
    *,
    revision_uuid: str | None = None,
) -> dict[str, Any]:
    if not engine_revision_hash or not engine_revision_hash.strip():
        raise ValueError(
            "engine_revision_hash is required for revision-safe reports "
            "(siehe REPORT_GENERATOR_SPEC.md: Pflichtprinzipien)"
        )
    with _session_scope(db) as (session, owns_session):
        attempt = 0
        while True:
            latest = (
                session.query(ReportRevisionRecord)
                .order_by(
                    ReportRevisionRecord.revisionsnummer.desc(),
                    ReportRevisionRecord.id.desc(),
                )
                .first()
            )
            previous = latest.hash if latest else "GENESIS"
            next_number = (
                int(
                    session.query(
                        func.coalesce(func.max(ReportRevisionRecord.revisionsnummer), 0)
                    ).scalar()
                    or 0
                )
                + 1
            )
            timestamp = datetime.now(timezone.utc)
            timestamp_iso = timestamp.isoformat()
            revision_uuid_value = (
                str(revision_uuid).strip() if revision_uuid else str(uuid.uuid4())
            )
            if not revision_uuid_value:
                revision_uuid_value = str(uuid.uuid4())
            report_checksum = compute_report_checksum(report_data)
            payload_hash = compute_report_revision_hash(
                revisionsnummer=next_number,
                uuid_value=revision_uuid_value,
                timestamp_iso=timestamp_iso,
                report_type=report_type,
                previous_hash=previous,
                engine_revision_hash=engine_revision_hash,
                report_checksum=report_checksum,
            )
            enriched_report = enrich_report_with_revision_metadata(
                report_data,
                revisionsnummer=next_number,
                uuid_value=revision_uuid_value,
                timestamp_iso=timestamp_iso,
                report_hash=payload_hash,
                engine_revision_hash=engine_revision_hash,
                report_checksum=report_checksum,
            )
            final_html = html(enriched_report) if callable(html) else html
            html_checksum = compute_html_checksum(final_html)
            enriched_report = enrich_report_with_revision_metadata(
                report_data,
                revisionsnummer=next_number,
                uuid_value=revision_uuid_value,
                timestamp_iso=timestamp_iso,
                report_hash=payload_hash,
                engine_revision_hash=engine_revision_hash,
                report_checksum=report_checksum,
                html_checksum=html_checksum,
            )

            record = ReportRevisionRecord(
                revisionsnummer=next_number,
                uuid=revision_uuid_value,
                timestamp=timestamp,
                schema_version=REPORT_SCHEMA_VERSION,
                report_type=report_type,
                previous_hash=previous,
                hash=payload_hash,
                engine_revision_hash=engine_revision_hash,
                report_json=_canonical(enriched_report),
                html_content=final_html,
            )
            try:
                session.add(record)
                session.flush()
                if owns_session:
                    session.commit()
                return {
                    "revisionsnummer": next_number,
                    "hash": payload_hash,
                    "uuid": revision_uuid_value,
                    "timestamp": timestamp_iso,
                    "engine_revision_hash": engine_revision_hash,
                    "verify_path": build_report_verify_path(payload_hash),
                    "report_checksum": report_checksum,
                    "html_checksum": html_checksum,
                    "report_data": enriched_report,
                    "html": final_html,
                }
            except IntegrityError:
                if owns_session:
                    session.rollback()
                if db is not None or attempt >= _MAX_INSERT_RETRIES:
                    raise
                attempt += 1
