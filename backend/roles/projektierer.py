"""Projektierer-Rolle: Engine-Ergebnis + Constraints + Wirtschaftlichkeit."""

from __future__ import annotations

from typing import Any, Dict

from core.schemas import ProjektiererRequest
from core.service import run_analysis
from economics import berechne_erloes
from engine.optimizer import optimiere

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

    # --- Wirtschaftlichkeit (Erloes mit Live-Strompreis) ---
    erloes = None
    erloes_fehler = None
    try:
        anlagentyp = eingabe.get("anlagentyp", "DEFAULT")
        # Leistung in MW: bevorzugt leistung_mw, sonst aus p_kw ableiten
        leistung_mw = eingabe.get("leistung_mw")
        if leistung_mw is None and eingabe.get("p_kw") is not None:
            leistung_mw = float(eingabe["p_kw"]) / 1000.0
        if leistung_mw and leistung_mw > 0:
            erloes = berechne_erloes(anlagentyp, float(leistung_mw))
    except Exception as e:
        erloes_fehler = f"Erloesberechnung fehlgeschlagen: {e}"

    # Investkosten aus bestehender Engine (falls vorhanden)
    investkosten_eur = None
    kosten_block = result.get("kosten") if isinstance(result, dict) else None
    if isinstance(kosten_block, dict):
        investkosten_eur = (
            kosten_block.get("investition_gesamt_eur")
            or kosten_block.get("investition_eur")
            or kosten_block.get("summe_eur")
        )

    # Einfache Amortisation (statisch, ohne Diskontierung)
    amortisation_jahre = None
    if erloes and investkosten_eur and erloes.get("erloes_jahr_eur", 0) > 0:
        amortisation_jahre = round(investkosten_eur / erloes["erloes_jahr_eur"], 1)

    result["projektierer"] = {
        "constraints": constraints,
        "wirtschaftlichkeit": {
            "erloes": erloes,
            "investkosten_eur": investkosten_eur,
            "amortisation_jahre": amortisation_jahre,
            "fehler": erloes_fehler,
            "hinweis": "Statische Amortisation ohne Kapitalkosten/OPEX. Indikativ.",
        },
        "optimizer": optimiere(result, eingabe, constraints),
    }
    return result



