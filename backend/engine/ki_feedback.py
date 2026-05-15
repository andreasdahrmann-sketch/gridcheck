from __future__ import annotations

import hashlib
import json
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from db.database import SessionLocal
from db.models import KiFeedbackRecord

FEEDBACK_SCHEMA_VERSION = "1.2.0"
_ENTSCHEIDUNGS_MAPPING = {"A": 2, "B": 1, "C": 0}
_MAX_INSERT_RETRIES = 3


def _kanonisiere(daten: dict[str, Any]) -> str:
    return json.dumps(daten, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _hash(daten: dict[str, Any]) -> str:
    return hashlib.sha256(_kanonisiere(daten).encode("utf-8")).hexdigest()


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


def _latest_feedback_record(db: Session) -> KiFeedbackRecord | None:
    return (
        db.query(KiFeedbackRecord)
        .order_by(KiFeedbackRecord.feedback_nummer.desc(), KiFeedbackRecord.id.desc())
        .first()
    )


def _next_feedback_number(db: Session) -> int:
    current = db.query(func.max(KiFeedbackRecord.feedback_nummer)).scalar()
    return int(current or 0) + 1


def _record_to_entry(record: KiFeedbackRecord) -> dict[str, Any]:
    try:
        data = json.loads(record.data_json)
    except json.JSONDecodeError:
        data = {}
    return {
        "feedback_nummer": int(record.feedback_nummer),
        "uuid": record.uuid,
        "timestamp": record.timestamp.isoformat(),
        "schema_version": record.schema_version,
        "previous_hash": record.previous_hash,
        "daten": data,
        "hash": record.hash,
    }


def _normalisiere_entscheidung(value: Any) -> str | None:
    if isinstance(value, dict):
        value = value.get("entscheidung")
    if value is None:
        return None
    v = str(value).strip().upper()
    if v in _ENTSCHEIDUNGS_MAPPING:
        return v
    return None


def _normalisiere_feedback_typ(value: Any) -> str:
    v = str(value or "bestaetigt").strip().lower()
    if v not in {"bestaetigt", "korrigiert"}:
        raise ValueError("feedback_typ muss 'bestaetigt' oder 'korrigiert' sein.")
    return v


def _normalisiere_revision_hash(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip().lower()
    if text == "":
        return None
    if len(text) != 64 or any(ch not in "0123456789abcdef" for ch in text):
        raise ValueError("revision_hash muss ein voller SHA-256 Hash mit 64 hex chars sein.")
    return text


def _normalisiere_score(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("score_gesamt bzw. confidence_snapshot muessen Zahlen sein.") from exc
    if number < 0 or number > 100:
        raise ValueError("Scores muessen im Bereich 0..100 liegen.")
    return round(number, 2)


def _normalisiere_flags(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [str(value).strip()]


def speichere_ki_feedback(
    *,
    ki_entscheidung: Any,
    nb_entscheidung: Any = None,
    kommentar: str | None = None,
    revision_hash: str | None = None,
    score_gesamt: float | None = None,
    quelle: str = "netzbetreiber",
    feedback_typ: str = "bestaetigt",
    confidence_snapshot: float | None = None,
    anomaly_flags: list[str] | None = None,
    dry_run: bool = False,
    actor_user_id: int | None = None,
    db: Session | None = None,
) -> dict[str, Any]:
    ki_norm = _normalisiere_entscheidung(ki_entscheidung)
    typ_norm = _normalisiere_feedback_typ(feedback_typ)
    nb_candidate = nb_entscheidung if nb_entscheidung is not None else ki_norm
    nb_norm = _normalisiere_entscheidung(nb_candidate)
    if ki_norm is None or nb_norm is None:
        raise ValueError("ki_entscheidung und nb_entscheidung muessen A/B/C sein.")
    if typ_norm == "korrigiert" and nb_norm == ki_norm:
        raise ValueError("Bei feedback_typ='korrigiert' muss nb_entscheidung von ki_entscheidung abweichen.")

    revision_hash_norm = _normalisiere_revision_hash(revision_hash)
    score_norm = _normalisiere_score(score_gesamt)
    confidence_norm = _normalisiere_score(confidence_snapshot)
    anomaly_norm = _normalisiere_flags(anomaly_flags)

    data = {
        "feedback_typ": typ_norm,
        "ki_entscheidung": ki_norm,
        "nb_entscheidung": nb_norm,
        "kommentar": kommentar,
        "revision_hash": revision_hash_norm,
        "score_gesamt": score_norm,
        "confidence_snapshot": confidence_norm,
        "anomaly_flags": anomaly_norm,
        "quelle": str(quelle or "netzbetreiber"),
    }

    with _session_scope(db) as (session, owns_session):
        attempt = 0
        while True:
            latest = _latest_feedback_record(session)
            prev = latest.hash if latest else "GENESIS"
            nr = _next_feedback_number(session)
            timestamp = datetime.now(timezone.utc)
            record_uuid = str(uuid.uuid4())
            data_json = _kanonisiere(data)

            if dry_run:
                payload = {
                    "feedback_nummer": nr,
                    "uuid": record_uuid,
                    "timestamp": timestamp.isoformat(),
                    "schema_version": FEEDBACK_SCHEMA_VERSION,
                    "previous_hash": prev,
                    "daten": data,
                }
                payload["hash"] = _hash(payload)
                return {
                    "feedback_nummer": nr,
                    "uuid": record_uuid,
                    "timestamp": payload["timestamp"],
                    "schema_version": FEEDBACK_SCHEMA_VERSION,
                    "previous_hash": prev,
                    "hash": payload["hash"],
                    "dry_run": dry_run,
                    "feedback_typ": typ_norm,
                    "revision_hash": revision_hash_norm,
                    "anomaly_flags": anomaly_norm,
                }

            # Hash must match persisted rows: DB roundtrip can normalize timestamps / JSON,
            # so compute the integrity hash after flush from ORM state (see pruefe_integritaet).
            placeholder_hash = uuid.uuid4().hex + uuid.uuid4().hex
            record = KiFeedbackRecord(
                feedback_nummer=nr,
                uuid=record_uuid,
                timestamp=timestamp,
                schema_version=FEEDBACK_SCHEMA_VERSION,
                previous_hash=prev,
                hash=placeholder_hash,
                actor_user_id=actor_user_id,
                revision_hash=revision_hash_norm,
                data_json=data_json,
            )
            try:
                session.add(record)
                session.flush()
                session.refresh(record)
                daten_norm = json.loads(record.data_json)
                payload = {
                    "feedback_nummer": record.feedback_nummer,
                    "uuid": record.uuid,
                    "timestamp": record.timestamp.isoformat(),
                    "schema_version": record.schema_version,
                    "previous_hash": record.previous_hash,
                    "daten": daten_norm,
                }
                final_hash = _hash(payload)
                record.hash = final_hash
                session.flush()
                meta = {
                    "feedback_nummer": nr,
                    "uuid": record.uuid,
                    "timestamp": record.timestamp.isoformat(),
                    "schema_version": FEEDBACK_SCHEMA_VERSION,
                    "previous_hash": prev,
                    "hash": final_hash,
                    "dry_run": dry_run,
                    "feedback_typ": typ_norm,
                    "revision_hash": revision_hash_norm,
                    "anomaly_flags": anomaly_norm,
                }
                if owns_session:
                    session.commit()
                return meta
            except IntegrityError:
                if owns_session:
                    session.rollback()
                if db is not None or attempt >= _MAX_INSERT_RETRIES:
                    raise
                attempt += 1


def lade_ki_feedback(db: Session | None = None) -> list[dict[str, Any]]:
    with _session_scope(db) as (session, _):
        records = (
            session.query(KiFeedbackRecord)
            .order_by(KiFeedbackRecord.feedback_nummer.asc(), KiFeedbackRecord.id.asc())
            .all()
        )
        return [_record_to_entry(record) for record in records]


def feedback_index_nach_revision(db: Session | None = None) -> dict[str, dict[str, Any]]:
    latest_by_revision: dict[str, dict[str, Any]] = {}
    for entry in lade_ki_feedback(db):
        data = entry.get("daten", {})
        try:
            revision_hash = _normalisiere_revision_hash(data.get("revision_hash"))
        except ValueError:
            continue
        if not revision_hash:
            continue
        latest_by_revision[revision_hash] = entry
    return latest_by_revision


def feedback_fuer_revision_hash(revision_hash: str, db: Session | None = None) -> dict[str, Any] | None:
    revision_hash_norm = _normalisiere_revision_hash(revision_hash)
    if not revision_hash_norm:
        return None
    return feedback_index_nach_revision(db).get(revision_hash_norm)


def berechne_kalibrierung(db: Session | None = None) -> dict[str, Any]:
    eintraege = lade_ki_feedback(db)
    paare: list[tuple[int, int]] = []
    bestaetigt = 0
    for e in eintraege:
        daten = e.get("daten", {})
        ki = _normalisiere_entscheidung(daten.get("ki_entscheidung"))
        nb = _normalisiere_entscheidung(daten.get("nb_entscheidung"))
        if ki is None or nb is None:
            continue
        paare.append((_ENTSCHEIDUNGS_MAPPING[ki], _ENTSCHEIDUNGS_MAPPING[nb]))
        if ki == nb:
            bestaetigt += 1

    if not paare:
        return {
            "samples": 0,
            "trefferquote": 0.0,
            "durchschnittlicher_fehler": 0.0,
            "kalibrierungsfaktor": 1.0,
            "bestaetigungsquote": 0.0,
            "status": "NO_FEEDBACK",
        }

    abs_errors = [abs(ki - nb) for ki, nb in paare]
    signed_errors = [ki - nb for ki, nb in paare]
    exact_hits = sum(1 for e in abs_errors if e == 0)
    disagreement_rate = sum(1 for e in abs_errors if e > 0) / len(abs_errors)
    avg_abs_err = sum(abs_errors) / len(abs_errors)
    avg_signed_err = sum(signed_errors) / len(signed_errors)
    bestaetigungsquote = bestaetigt / len(paare)

    base_penalty = min(0.25, (avg_abs_err * 0.15) + (disagreement_rate * 0.2))
    quality_bonus = min(0.08, bestaetigungsquote * 0.06 + min(len(paare), 20) * 0.001)
    faktor = round(max(0.75, min(1.08, 1.0 - base_penalty + quality_bonus)), 4)

    return {
        "samples": len(paare),
        "trefferquote": round(exact_hits / len(paare), 4),
        "durchschnittlicher_fehler": round(avg_abs_err, 4),
        "bias": round(avg_signed_err, 4),
        "kalibrierungsfaktor": faktor,
        "bestaetigungsquote": round(bestaetigungsquote, 4),
        "status": "CALIBRATED",
    }


def berechne_lernstatus(db: Session | None = None) -> dict[str, Any]:
    eintraege = lade_ki_feedback(db)
    if not eintraege:
        return {
            "samples_total": 0,
            "linked_samples": 0,
            "bestaetigt": 0,
            "korrigiert": 0,
            "bestaetigungsquote": 0.0,
            "coverage_ratio": 0.0,
            "anomaly_feedbacks": 0,
            "status": "NO_FEEDBACK",
            "last_feedback_at": None,
        }

    total = 0
    linked = 0
    bestaetigt = 0
    korrigiert = 0
    anomaly_feedbacks = 0
    last_feedback_at = None
    for entry in eintraege:
        daten = entry.get("daten", {})
        ki = _normalisiere_entscheidung(daten.get("ki_entscheidung"))
        nb = _normalisiere_entscheidung(daten.get("nb_entscheidung"))
        if ki is None or nb is None:
            continue
        total += 1
        if daten.get("revision_hash"):
            linked += 1
        if ki == nb:
            bestaetigt += 1
        else:
            korrigiert += 1
        if _normalisiere_flags(daten.get("anomaly_flags")):
            anomaly_feedbacks += 1
        last_feedback_at = entry.get("timestamp") or last_feedback_at

    if total == 0:
        return {
            "samples_total": 0,
            "linked_samples": 0,
            "bestaetigt": 0,
            "korrigiert": 0,
            "bestaetigungsquote": 0.0,
            "coverage_ratio": 0.0,
            "anomaly_feedbacks": 0,
            "status": "NO_FEEDBACK",
            "last_feedback_at": None,
        }

    if total < 5:
        status = "LOW_SIGNAL"
    elif total < 20:
        status = "LEARNING"
    else:
        status = "MATURE"

    return {
        "samples_total": total,
        "linked_samples": linked,
        "bestaetigt": bestaetigt,
        "korrigiert": korrigiert,
        "bestaetigungsquote": round(bestaetigt / total, 4),
        "coverage_ratio": round(linked / total, 4),
        "anomaly_feedbacks": anomaly_feedbacks,
        "status": status,
        "last_feedback_at": last_feedback_at,
    }


def pruefe_integritaet(db: Session | None = None) -> dict[str, Any]:
    """Verifiziert die Hash-Kette der PostgreSQL-basierten KI-Feedback-Records."""
    fehler: list[str] = []
    anzahl = 0
    prev = "GENESIS"

    for i, eintrag in enumerate(lade_ki_feedback(db), start=1):
        anzahl += 1
        gespeicherter_hash = eintrag.get("hash")
        if eintrag.get("previous_hash") != prev:
            fehler.append(
                f"Zeile {i}: previous_hash-Bruch (erwartet {prev[:12]}, war {str(eintrag.get('previous_hash'))[:12]})"
            )

        ohne_hash = {k: v for k, v in eintrag.items() if k != "hash"}
        recomputed = _hash(ohne_hash)
        if recomputed != gespeicherter_hash:
            fehler.append(f"Zeile {i}: Hash-Mismatch")

        prev = str(gespeicherter_hash or prev)

    return {"ok": len(fehler) == 0, "anzahl": anzahl, "fehler": fehler}
