from __future__ import annotations

from typing import Any

from engine import berechne_netzanschluss, ki_bewertung


def run_v1_analysis(
    eingabe: dict[str, Any],
    *,
    revision_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    result = berechne_netzanschluss(eingabe, revision_context=revision_context)
    if result.get("status") == "FEHLER":
        return result
    try:
        result = ki_bewertung(result)
    except Exception:
        result.setdefault("ki", {"konfidenz_prozent": 0, "hinweise": ["KI-Modul nicht verfuegbar"]})
    return result
