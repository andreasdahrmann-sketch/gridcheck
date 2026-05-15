from __future__ import annotations

from typing import Any

from core.errors import AnalysisError
from engine.ki_feedback import (
    berechne_kalibrierung,
    lade_ki_feedback,
    pruefe_integritaet,
    speichere_ki_feedback,
)


def create_feedback(payload: dict[str, Any]) -> dict[str, Any]:
    try:
        meta = speichere_ki_feedback(**payload)
    except ValueError as e:
        raise AnalysisError(
            code="KI_FEEDBACK_INVALID",
            message=str(e),
            hint="Erlaubte Entscheidungen sind A, B oder C.",
            http_status=422,
        )
    return {
        "status": "OK",
        "feedback": meta,
        "kalibrierung": berechne_kalibrierung(),
    }


def get_calibration() -> dict[str, Any]:
    return berechne_kalibrierung()


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
