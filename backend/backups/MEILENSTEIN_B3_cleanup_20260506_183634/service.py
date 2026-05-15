from __future__ import annotations

from typing import Any, Dict

from engine import berechne_netzanschluss, ki_bewertung

from core.errors import AnalysisError


def run_analysis(eingabe: Dict[str, Any]) -> Dict[str, Any]:
    """
    Führt die deterministische Engine aus. KI + Revision sind optional (wie v2).
    """
    result = berechne_netzanschluss(eingabe)

    if result.get("status") == "FEHLER":
        fehler = result.get("fehler", []) or []
        message = fehler[0] if fehler else "Engine-Validierung fehlgeschlagen"
        hint = "; ".join(str(x) for x in fehler[:8]) if fehler else None
        raise AnalysisError(
            code="ENGINE_VALIDATION_FAILED",
            message=str(message),
            hint=hint,
            http_status=422,
        )

    try:
        result = ki_bewertung(result)
    except Exception:
        result.setdefault(
            "ki",
            {"konfidenz_prozent": 0, "hinweise": ["KI-Modul nicht verfuegbar"]},
        )

    return result
