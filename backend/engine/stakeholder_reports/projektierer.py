from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from compliance import APP_VERSION_NORMSTAND, get_normen_fuer_spannungsebene


@dataclass(frozen=True)
class ProjektiererReportDTO:
    report_type: str
    report_version: str
    app_normstand: str
    engine_revision_hash: str | None
    standort: str
    plz: str | None
    leistung_mw: float
    spannungsebene: str
    anschlussart: str
    entscheidung: str
    geht: bool
    auflagen: list[str]
    n1_status: str
    n1_detail: str
    empfohlene_massnahmen: list[str]
    normen_snapshot: list[dict[str, str]]


def _spannungsebene_from_kv(u_kv: float) -> str:
    if u_kv < 1:
        return "NS"
    if u_kv <= 35:
        return "MS"
    return "HS"


def build_projektierer_report(engine_result: dict[str, Any]) -> dict[str, Any]:
    eingabe = engine_result.get("eingabe", {})
    fazit = engine_result.get("fazit", {})
    n1 = engine_result.get("n1", {})
    warnungen = engine_result.get("warnungen", [])
    empfehlungen = engine_result.get("empfehlungen", [])
    revision = engine_result.get("revision", {})

    nennspannung = float(eingabe.get("nennspannung", 20.0))
    normen = get_normen_fuer_spannungsebene(nennspannung)
    normen_snapshot = [
        {"norm_id": n.norm_id, "titel": n.titel, "stand": n.stand, "kategorie": n.kategorie}
        for n in normen
    ]

    dto = ProjektiererReportDTO(
        report_type="projektierer",
        report_version="1.0.0",
        app_normstand=APP_VERSION_NORMSTAND,
        engine_revision_hash=revision.get("hash") if isinstance(revision, dict) else None,
        standort=str(eingabe.get("ort") or eingabe.get("standort") or "Unbekannt"),
        plz=eingabe.get("plz"),
        leistung_mw=float(eingabe.get("leistung_mw", 0.0)),
        spannungsebene=_spannungsebene_from_kv(nennspannung),
        anschlussart=str(eingabe.get("anschlussart", "Unbekannt")),
        entscheidung=str(fazit.get("entscheidung", "C")),
        geht=str(fazit.get("entscheidung", "C")) != "C",
        auflagen=[str(w) for w in warnungen if isinstance(w, str)],
        n1_status="BESTANDEN" if bool(n1.get("n1_sicher")) else "NICHT BESTANDEN",
        n1_detail=str(n1.get("topologie_text", "")),
        empfohlene_massnahmen=[str(x) for x in empfehlungen if isinstance(x, str)],
        normen_snapshot=normen_snapshot,
    )
    return asdict(dto)

