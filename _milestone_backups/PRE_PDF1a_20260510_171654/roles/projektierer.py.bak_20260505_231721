"""Projektierer-Rolle: Engine-Ergebnis + Constraints + Optimizer-Platzhalter."""

from __future__ import annotations

from typing import Any, Dict

from core.schemas import ProjektiererRequest
from core.service import run_analysis

_PROJ_KEYS = (
    "budget_eur",
    "zeitfenster_monate",
    "flex_leistung",
    "flex_zeitfenster",
    "flex_standort",
)


def analyze_for_projektierer(req: ProjektiererRequest) -> Dict[str, Any]:
    eingabe = req.model_dump(exclude_none=False)
    constraints: Dict[str, Any] = {k: eingabe.pop(k) for k in _PROJ_KEYS if k in eingabe}

    result = run_analysis(eingabe)
    result["projektierer"] = {
        "constraints": constraints,
        "optimizer": {
            "status": "PENDING",
            "hinweis": "Optimizer-Logik folgt in Sprint 1 / Schritt 3 (Variante a).",
        },
    }
    return result
