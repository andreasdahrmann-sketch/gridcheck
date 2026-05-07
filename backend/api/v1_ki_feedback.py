"""V1-Endpoints fuer KI-Feedback und Score-Kalibrierung."""
from __future__ import annotations

from typing import Literal, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from core.errors import AnalysisError
from services.ki_feedback_service import (
    count_feedback as svc_count_feedback,
    create_feedback,
    get_calibration as svc_get_calibration,
    get_feedback_by_hash as svc_get_feedback_by_hash,
    verify_feedback_chain as svc_verify_feedback_chain,
)

router = APIRouter(prefix="/api/v1/ki", tags=["v1-ki"])


class KiFeedbackRequest(BaseModel):
    ki_entscheidung: Literal["A", "B", "C"] = Field(
        ...,
        description="KI-Fazit A/B/C",
        examples=["A"],
    )
    nb_entscheidung: Literal["A", "B", "C"] = Field(
        ...,
        description="Finales VNB-Feedback A/B/C",
        examples=["B"],
    )
    kommentar: Optional[str] = Field(
        default=None,
        max_length=2000,
        examples=["VNB fordert Blindleistungsnachweis und Auflagen im Schutzkonzept."],
    )
    revision_hash: Optional[str] = Field(
        default=None,
        min_length=64,
        max_length=64,
        examples=["5a1f8e5b2f4bd8627d6c9f9d6f9ec8f564df41a91e2f55cf2ca0a9f1f6c947b0"],
    )
    score_gesamt: Optional[float] = Field(default=None, ge=0, le=100, examples=[78.0])
    quelle: Literal["netzbetreiber", "audit", "manuell"] = Field(
        default="netzbetreiber",
        examples=["netzbetreiber"],
    )


@router.post(
    "/feedback",
    summary="Persistiert Netzbetreiber-Feedback revisionssicher",
    responses={
        200: {
            "description": "Feedback gespeichert, Kalibrierung aktualisiert.",
            "content": {
                "application/json": {
                    "example": {
                        "status": "OK",
                        "feedback": {
                            "feedback_nummer": 12,
                            "uuid": "f35f2ca2-003a-4d1a-8955-f9e72e8d93f2",
                            "timestamp": "2026-05-06T20:21:03.120000+00:00",
                            "schema_version": "1.0.0",
                            "previous_hash": "c8ef...f93a",
                            "hash": "e13d...2a7b",
                            "dry_run": False,
                        },
                        "kalibrierung": {
                            "samples": 12,
                            "trefferquote": 0.75,
                            "durchschnittlicher_fehler": 0.25,
                            "bias": 0.08,
                            "kalibrierungsfaktor": 0.89,
                            "status": "CALIBRATED",
                        },
                    }
                }
            },
        }
    },
)
def post_feedback(req: KiFeedbackRequest):
    try:
        return create_feedback(
            {
                "ki_entscheidung": req.ki_entscheidung,
                "nb_entscheidung": req.nb_entscheidung,
                "kommentar": req.kommentar,
                "revision_hash": req.revision_hash,
                "score_gesamt": req.score_gesamt,
                "quelle": req.quelle,
            }
        )
    except AnalysisError as e:
        raise HTTPException(status_code=e.http_status, detail=e.to_dict())
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "INTERNAL_ERROR",
                "message": str(e),
                "hint": None,
            },
        )


@router.get(
    "/calibration",
    summary="Liefert aktuellen Kalibrierungsstatus der KI-Scores",
    responses={
        200: {
            "description": "Kalibrierungsstatus auf Basis gespeicherter NB-Feedbacks.",
            "content": {
                "application/json": {
                    "examples": {
                        "no_feedback": {
                            "summary": "Noch kein Feedback vorhanden",
                            "value": {
                                "samples": 0,
                                "trefferquote": 0.0,
                                "durchschnittlicher_fehler": 0.0,
                                "kalibrierungsfaktor": 1.0,
                                "status": "NO_FEEDBACK",
                            },
                        },
                        "calibrated": {
                            "summary": "Kalibrierung aktiv",
                            "value": {
                                "samples": 24,
                                "trefferquote": 0.7917,
                                "durchschnittlicher_fehler": 0.2083,
                                "bias": 0.0417,
                                "kalibrierungsfaktor": 0.9012,
                                "status": "CALIBRATED",
                            },
                        },
                    }
                }
            },
        }
    },
)
def get_calibration():
    return svc_get_calibration()


@router.get(
    "/verify",
    summary="Prueft die Integritaet der KI-Feedback-Hash-Kette",
    responses={
        200: {
            "description": "Ergebnis der Integritaetspruefung fuer ki_feedback.jsonl.",
            "content": {
                "application/json": {
                    "examples": {
                        "ok": {
                            "summary": "Kette ist intakt",
                            "value": {"ok": True, "anzahl": 24, "fehler": []},
                        },
                        "broken": {
                            "summary": "Kette mit Fehlern",
                            "value": {
                                "ok": False,
                                "anzahl": 24,
                                "fehler": [
                                    "Zeile 8: previous_hash-Bruch (erwartet a1b2c3d4e5f6, war 000000000000)",
                                    "Zeile 8: Hash-Mismatch",
                                ],
                            },
                        },
                    }
                }
            },
        }
    },
)
def verify_feedback_chain():
    return svc_verify_feedback_chain()


@router.get(
    "/count",
    summary="Liefert Anzahl und letzten Hash der KI-Feedback-Eintraege",
    responses={
        200: {
            "description": "Schneller Zaehler fuer Auditoren und Monitoring.",
            "content": {
                "application/json": {
                    "examples": {
                        "empty": {
                            "summary": "Noch keine Eintraege",
                            "value": {
                                "anzahl": 0,
                                "letzte_feedback_nummer": None,
                                "letzter_hash": None,
                            },
                        },
                        "with_entries": {
                            "summary": "Eintraege vorhanden",
                            "value": {
                                "anzahl": 24,
                                "letzte_feedback_nummer": 24,
                                "letzter_hash": "e13d...2a7b",
                            },
                        },
                    }
                }
            },
        }
    },
)
def count_feedback():
    return svc_count_feedback()


@router.get(
    "/{hash_value}",
    summary="Holt einen KI-Feedback-Eintrag per vollem SHA-256",
)
def get_feedback_by_hash(hash_value: str):
    try:
        return svc_get_feedback_by_hash(hash_value)
    except AnalysisError as e:
        raise HTTPException(status_code=e.http_status, detail=e.to_dict())
