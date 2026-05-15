from __future__ import annotations

from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from core.errors import AnalysisError
from db.models import User
from engine.ki_feedback import (
    berechne_kalibrierung,
    berechne_lernstatus,
    feedback_fuer_revision_hash,
    lade_ki_feedback,
    pruefe_integritaet,
    speichere_ki_feedback,
)
from engine.revision import lade_revisionen, speichere_revision
from services import project_service


def _revision_by_hash(hash_value: str | None) -> dict[str, Any] | None:
    if not hash_value:
        return None
    for entry in lade_revisionen():
        if entry.get("hash") == str(hash_value).lower():
            return entry
    return None


def _authorize_feedback_revision(
    db: Session,
    current_user: User,
    linked_revision: dict[str, Any],
) -> None:
    revision_data = linked_revision.get("daten", {})
    if not isinstance(revision_data, dict):
        raise AnalysisError(
            code="KI_FEEDBACK_REVISION_INVALID",
            message="Verknuepfte Analyse-Revision ist ungueltig.",
            hint="Bitte eine aktuelle revisionssichere Analyse als Quelle verwenden.",
            http_status=409,
        )
    meta = revision_data.get("meta", {})
    if not isinstance(meta, dict):
        meta = {}
    project_id = meta.get("project_id")
    actor_user_id = meta.get("actor_user_id")

    if project_id is not None:
        try:
            project_service.get_project_access_context(
                db,
                current_user,
                int(project_id),
                require_write=True,
            )
            return
        except HTTPException as exc:
            if exc.status_code == 404:
                raise AnalysisError(
                    code="KI_FEEDBACK_REVISION_NOT_FOUND",
                    message="Die verknuepfte Projekt-Revision ist nicht mehr verfuegbar.",
                    hint="Bitte eine aktuelle, zugaengliche Analyse-Revision verwenden.",
                    http_status=404,
                ) from exc
            raise AnalysisError(
                code="KI_FEEDBACK_FORBIDDEN",
                message="KI-Feedback darf nur fuer eigene oder bearbeitbare Projekt-Revisionen gespeichert werden.",
                hint="Bitte mit Owner-, Editor- oder Admin-Rechten erneut versuchen.",
                http_status=403,
            ) from exc

    if current_user.role == "admin":
        return
    if actor_user_id == current_user.id:
        return
    raise AnalysisError(
        code="KI_FEEDBACK_FORBIDDEN",
        message="KI-Feedback darf nur fuer eigene oder bearbeitbare Revisionen gespeichert werden.",
        hint="Bitte eine eigene Analyse-Revision verwenden oder einen berechtigten Bearbeiter hinzuziehen.",
        http_status=403,
    )


def create_feedback(
    payload: dict[str, Any],
    *,
    db: Session,
    current_user: User,
    actor_user_id: int | None = None,
) -> dict[str, Any]:
    if not payload.get("revision_hash"):
        raise AnalysisError(
            code="KI_FEEDBACK_REVISION_REQUIRED",
            message="KI-Feedback erfordert einen verknuepften revisionssicheren Analyse-Hash.",
            hint="Bitte revision_hash aus einer berechtigten Analyse mitgeben.",
            http_status=422,
        )
    linked_revision = _revision_by_hash(payload.get("revision_hash"))
    if linked_revision is None:
        raise AnalysisError(
            code="KI_FEEDBACK_REVISION_NOT_FOUND",
            message="Angegebene Analyse-Revision wurde nicht gefunden",
            hint="Bitte den revisionssicheren Analyse-Hash aus dem Ergebnis verwenden.",
            http_status=404,
        )
    _authorize_feedback_revision(db, current_user, linked_revision)
    try:
        meta = speichere_ki_feedback(**payload, actor_user_id=actor_user_id)
    except ValueError as e:
        raise AnalysisError(
            code="KI_FEEDBACK_INVALID",
            message=str(e),
            hint="Erlaubte Entscheidungen sind A, B oder C.",
            http_status=422,
        )
    kalibrierung = berechne_kalibrierung()
    lernstatus = berechne_lernstatus()
    audit_revision = speichere_revision(
        {
            "eingabe": {
                "revision_hash": payload.get("revision_hash"),
                "feedback_hash": meta.get("hash"),
                "feedback_typ": meta.get("feedback_typ"),
                "quelle": payload.get("quelle"),
            },
            "fazit": {"status": "KI_FEEDBACK_RECORDED"},
            "ki": {
                "kalibrierung": kalibrierung,
                "lernstatus": lernstatus,
                "feedback_hash": meta.get("hash"),
            },
        },
        actor_user_id=actor_user_id,
        action_type="KI_FEEDBACK_RECORDED",
        project_id=((linked_revision or {}).get("daten", {}).get("meta", {}) or {}).get("project_id"),
    )
    return {
        "status": "OK",
        "feedback": meta,
        "kalibrierung": kalibrierung,
        "lernstatus": lernstatus,
        "audit_revision": audit_revision,
    }


def get_calibration() -> dict[str, Any]:
    return berechne_kalibrierung()


def get_learning_status() -> dict[str, Any]:
    return berechne_lernstatus()


def verify_feedback_chain() -> dict[str, Any]:
    return pruefe_integritaet()


def count_feedback() -> dict[str, Any]:
    eintraege = lade_ki_feedback()
    if not eintraege:
        return {"anzahl": 0, "letzte_feedback_nummer": None, "letzter_hash": None}
    last = eintraege[-1]
    return {
        "anzahl": len(eintraege),
        "letzte_feedback_nummer": last.get("feedback_nummer"),
        "letzter_hash": last.get("hash"),
    }


def get_feedback_by_hash(hash_value: str) -> dict[str, Any]:
    if len(hash_value) != 64 or not all(c in "0123456789abcdef" for c in hash_value.lower()):
        raise AnalysisError(
            code="KI_FEEDBACK_HASH_INVALID",
            message="Ungueltiger SHA-256 Hash (64 hex chars erforderlich)",
            hint="Beispiel: 64-stelliger hexadezimaler Hash in Kleinbuchstaben.",
            http_status=400,
        )

    eintraege = lade_ki_feedback()
    for e in eintraege:
        if e.get("hash") == hash_value.lower():
            return e

    raise AnalysisError(
        code="KI_FEEDBACK_NOT_FOUND",
        message="Feedback-Eintrag nicht gefunden",
        hint="Pruefen Sie den Hash oder nutzen Sie /api/v1/ki/count.",
        http_status=404,
    )


def get_feedback_for_revision(hash_value: str) -> dict[str, Any]:
    if len(hash_value) != 64 or not all(c in "0123456789abcdef" for c in hash_value.lower()):
        raise AnalysisError(
            code="KI_FEEDBACK_HASH_INVALID",
            message="Ungueltiger SHA-256 Hash (64 hex chars erforderlich)",
            hint="Beispiel: 64-stelliger hexadezimaler Hash in Kleinbuchstaben.",
            http_status=400,
        )
    found = feedback_fuer_revision_hash(hash_value)
    if found is None:
        raise AnalysisError(
            code="KI_FEEDBACK_NOT_FOUND",
            message="Noch kein Feedback fuer diese Revision gespeichert",
            hint="Netzbetreiber-Feedback kann nach der Ergebnispruefung nachgereicht werden.",
            http_status=404,
        )
    return found
