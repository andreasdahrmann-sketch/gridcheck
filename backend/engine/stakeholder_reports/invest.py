from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from compliance import APP_VERSION_NORMSTAND, get_normen_fuer_spannungsebene
from engine.gridcheck_report_mapper import _sources_from_engine
from engine.stakeholder_reports.content_blocks import (
    build_invest_kpi_summary,
    build_process_timeline_lines,
)
from engine.stakeholder_reports.projektierer import (
    _build_connection_variants,
    _build_cost_band,
    _build_location_meta,
    _build_risks,
)
from engine.stakeholder_reports.scope_meta import resolve_report_scope_meta


@dataclass(frozen=True)
class InvestReportDTO:
    report_type: str
    report_version: str
    app_normstand: str
    engine_revision_hash: str | None
    report_generated_at: str | None
    audit_hash: str | None
    offer_id: str | None
    package_scope: str
    package_scope_label: str
    report_scope: str
    report_scope_label: str
    scope_summary: str
    scope_boundary_note: str
    ops_followup_required: bool
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
    kosten_indikation: dict[str, Any] | None
    cost_band: dict[str, Any] | None
    site_assessment: list[dict[str, str]]
    risk_overview: list[dict[str, str]]
    due_diligence_checklist: list[dict[str, str]]
    portfolio_view: list[str]
    data_basis: list[str]
    visibility_boundary_note: str
    projektprofil_summary: str
    speicher_summary: str
    route_environment_summary: str
    stakeholder_konflikt: str
    recommended_focus: str
    transparenz_hinweise: list[str]
    disclaimers: list[str]
    includes_strategy_section: bool
    includes_transparency_section: bool
    includes_cost_section: bool
    operational_boundary_note: str | None
    kpi_summary: list[str]
    process_timeline: list[str]
    # P3: Score-Hero, Standort/Netzumfeld, Risiko-Block, Worst/Base/Best-Szenario,
    # Datenquellen — analog Projektierer-DTO; defaults wahren Abwaertskompatibilitaet.
    gridcheck_score: int | None = None
    scores: dict[str, Any] = field(default_factory=dict)
    connection_variants: list[dict[str, Any]] = field(default_factory=list)
    risks: dict[str, Any] = field(default_factory=dict)
    sources: list[dict[str, Any]] = field(default_factory=list)
    location_meta: dict[str, Any] = field(default_factory=dict)
    scenarios: dict[str, Any] = field(default_factory=dict)
    sensitivities: list[str] = field(default_factory=list)


def _spannungsebene_from_kv(u_kv: float) -> str:
    if u_kv < 1:
        return "NS"
    if u_kv <= 35:
        return "MS"
    return "HS"


def _as_text_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def _kosten_indikation(engine_result: dict[str, Any]) -> dict[str, Any] | None:
    raw = engine_result.get("kosten")
    if not isinstance(raw, dict) or not raw:
        return None
    return {
        str(k): v
        for k, v in raw.items()
        if isinstance(v, (str, int, float, bool)) or v is None
    } or None


def _cost_band(engine_result: dict[str, Any]) -> dict[str, Any] | None:
    raw = engine_result.get("kosten")
    if not isinstance(raw, dict) or not raw:
        return None
    basis = raw.get("band_basis_eur") or raw.get("investition_gesamt_eur")
    if basis is None:
        return None
    return {
        "niedrig_eur": raw.get("band_niedrig_eur") or basis,
        "basis_eur": basis,
        "hoch_eur": raw.get("band_hoch_eur") or basis,
        "confidence_pct": raw.get("konfidenz_prozent"),
        "source": raw.get("quelle"),
        "assumptions": _as_text_list(raw.get("band_annahmen")),
        "drivers": _as_text_list(raw.get("hauptrisikotreiber")),
    }


def _site_assessment(engine_result: dict[str, Any]) -> list[dict[str, str]]:
    eingabe = engine_result.get("eingabe", {})
    location = eingabe.get("project_location") if isinstance(eingabe.get("project_location"), dict) else {}
    has_coordinates = location.get("latitude") is not None and location.get("longitude") is not None
    has_hint = bool(str(location.get("address_hint") or eingabe.get("standort") or eingabe.get("ort") or "").strip())
    projektreife = str(eingabe.get("projektreife") or "offen")
    baugenehmigung = bool(eingabe.get("baugenehmigung_vorhanden"))
    nap = eingabe.get("netzanschlusspunkt") if isinstance(eingabe.get("netzanschlusspunkt"), dict) else {}
    return [
        {
            "label": "Standortpraezisierung",
            "status": "hoch" if has_coordinates else "mittel" if has_hint else "niedrig",
            "detail": "Koordinate und Adresshinweis vorhanden."
            if has_coordinates
            else "Adress- oder Flurstueckshinweis vorhanden."
            if has_hint
            else "Nur grobe Regionalangabe vorhanden.",
        },
        {
            "label": "Projektreife",
            "status": "hoch" if projektreife in {"genehmigt", "baubereit"} else "mittel" if projektreife == "planung" else "niedrig",
            "detail": f"Projektstatus aktuell: {projektreife}.",
        },
        {
            "label": "Genehmigungsstand",
            "status": "hoch" if baugenehmigung else "mittel",
            "detail": "Baugenehmigung ist bereits hinterlegt." if baugenehmigung else "Genehmigungsstand bleibt fuer Due Diligence noch offen.",
        },
        {
            "label": "NAP-Strategie",
            "status": "hoch" if nap.get("own_transformer") or nap.get("own_substation") else "mittel",
            "detail": "Eigene Anschlussinfrastruktur ist vorgesehen."
            if nap.get("own_transformer") or nap.get("own_substation")
            else "Anschlussinfrastruktur liegt voraussichtlich im Standard-VNB-Pfad.",
        },
    ]


def _risk_overview(engine_result: dict[str, Any]) -> list[dict[str, str]]:
    route_environment = engine_result.get("route_environment", {})
    stakeholder = engine_result.get("stakeholder_bewertung", {})
    datenqualitaet = engine_result.get("datenqualitaet", {})
    n1 = engine_result.get("n1", {})
    eingabe = engine_result.get("eingabe", {})
    baugenehmigung = bool(eingabe.get("baugenehmigung_vorhanden"))
    return [
        {
            "label": "Netz- / N-1-Risiko",
            "status": "hoch" if str(n1.get("bewertung") or "").upper() in {"ROT", "ORANGE"} else "mittel" if str(n1.get("n1_klasse") or "N1-0") in {"N1-1", "N1-2"} else "niedrig",
            "detail": str(n1.get("detail_text") or n1.get("stufenbegruendung") or n1.get("topologie_text") or ""),
        },
        {
            "label": "Trassen- / Umwelt",
            "status": str(route_environment.get("risk_level") or "mittel"),
            "detail": str(route_environment.get("summary") or ""),
        },
        {
            "label": "Datenrisiko",
            "status": "niedrig" if str(datenqualitaet.get("klasse") or "D") == "A" else "mittel" if str(datenqualitaet.get("klasse") or "D") == "B" else "hoch",
            "detail": f"Datenqualitaet {datenqualitaet.get('klasse', 'D')}: {datenqualitaet.get('text', '')}",
        },
        {
            "label": "Stakeholder / Umsetzung",
            "status": str(stakeholder.get("konflikt_level") or "mittel"),
            "detail": str(stakeholder.get("konflikt_summary") or ""),
        },
        {
            "label": "Termin / Freigabe",
            "status": "niedrig" if baugenehmigung else "mittel",
            "detail": "Genehmigungsseitig bereits weiter fortgeschritten." if baugenehmigung else "Genehmigungs- oder Freigabeschritte koennen die Umsetzungszeit dominieren.",
        },
    ]


def _due_diligence_checklist(engine_result: dict[str, Any]) -> list[dict[str, str]]:
    revision = engine_result.get("revision", {})
    n1 = engine_result.get("n1", {})
    wirtschaftlichkeit = engine_result.get("wirtschaftlichkeit")
    kosten = engine_result.get("kosten", {})
    location = engine_result.get("eingabe", {}).get("project_location")
    has_location = isinstance(location, dict) and (
        location.get("latitude") is not None or str(location.get("address_hint") or "").strip()
    )
    return [
        {
            "label": "Revisionsspur",
            "status": "vorhanden" if revision.get("hash") else "offen",
            "detail": "Audit-Hash und Report-Revision sind vorhanden." if revision.get("hash") else "Revisionssichere Zuordnung fehlt.",
        },
        {
            "label": "Standortgrundlage",
            "status": "vorhanden" if has_location else "offen",
            "detail": "Standort ist fuer Datenraum und Ortsbezug ausreichend hinterlegt." if has_location else "Standortpraezisierung sollte fuer Due Diligence nachgeschaerft werden.",
        },
        {
            "label": "Netznachweistiefe",
            "status": "vorhanden" if str(n1.get("n1_klasse") or "N1-0") in {"N1-3", "N1-4"} else "teilweise",
            "detail": f"N-1-Screening derzeit auf {n1.get('n1_klasse', 'N1-0')} klassifiziert.",
        },
        {
            "label": "Kostenbandbreite",
            "status": "vorhanden" if kosten.get("band_basis_eur") or kosten.get("investition_gesamt_eur") else "offen",
            "detail": "Bandbreite und Risikotreiber sind fuer die Investsicht hergeleitet.",
        },
        {
            "label": "Wirtschaftlichkeit",
            "status": "vorhanden" if isinstance(wirtschaftlichkeit, dict) else "teilweise",
            "detail": "Wirtschaftlichkeitsmodul mit ROI-/Cashflow-Indikatoren ist befuellt."
            if isinstance(wirtschaftlichkeit, dict)
            else "Erlos- und Betriebsdaten fehlen; Kostenbandbreite bleibt der belastbarere MVP-Anker.",
        },
    ]


def _portfolio_view(engine_result: dict[str, Any]) -> list[str]:
    stakeholder = engine_result.get("stakeholder_bewertung", {})
    projektprofil = engine_result.get("projektprofil", {})
    score = float((engine_result.get("scores") or {}).get("gesamt", 0))
    avg_fit = round(
        (
            float(stakeholder.get("netzbetreiber_score", 0))
            + float(stakeholder.get("projektierer_score", 0))
            + float(stakeholder.get("umsetzung_score", 0))
        )
        / 3,
        1,
    )
    bucket = "oberes Anschlussband" if score >= 70 else "mittleres Anschlussband" if score >= 40 else "kritisches Anschlussband"
    return [
        f"Score-Einordnung: {bucket} ({score}/100).",
        f"Stakeholder-Fit im Mittel: {avg_fit}/100.",
        f"Projektprofil: {'Hybrid' if projektprofil.get('is_hybrid') else 'Einzelprofil'} mit {projektprofil.get('component_count', 0)} Komponente(n).",
    ]


def _data_basis(engine_result: dict[str, Any]) -> list[str]:
    eingabe = engine_result.get("eingabe", {})
    kosten = engine_result.get("kosten", {})
    return [
        f"Standort- und Projektbasis: {eingabe.get('standort') or eingabe.get('ort') or eingabe.get('plz') or 'Unbekannt'}.",
        f"N-1-Datengrundlage: {eingabe.get('n1_datengrundlage', 'unknown')}.",
        f"Kostenquelle: {kosten.get('quelle', 'n/a')}.",
    ]


def _invest_scenarios(cost_band: dict[str, Any] | None) -> dict[str, Any]:
    """Worst/Base/Best CAPEX-Szenarien fuer die Investsicht.

    Reine Ableitung aus cost_band. Wenn keine Bandbreite vorhanden ist, wird
    ein leeres Dict zurueckgegeben — keine erfundenen Werte. Worst/Best wird
    bewusst um +20%/-10% gegenueber high/low erweitert (Stress-Spread,
    transparente Annahme), damit die Sensitivitaet nicht versteckt bleibt.
    """
    if not isinstance(cost_band, dict):
        return {}
    base = int(cost_band.get("basis_eur") or 0)
    low = int(cost_band.get("niedrig_eur") or 0)
    high = int(cost_band.get("hoch_eur") or 0)
    if base <= 0 and low <= 0 and high <= 0:
        return {}
    if base <= 0:
        base = max(low, high, 1)
    if low <= 0:
        low = int(base * 0.85)
    if high <= 0:
        high = int(base * 1.15)
    worst = int(high * 1.20)
    best = max(0, int(low * 0.90))
    conf = str(cost_band.get("confidence") or "medium")
    conf_pct = cost_band.get("confidence_pct")
    return {
        "best_eur": best,
        "low_eur": low,
        "base_eur": base,
        "high_eur": high,
        "worst_eur": worst,
        "confidence": conf,
        "confidence_pct": conf_pct,
        "note": (
            "Worst/Best erweitern Hoch/Niedrig um +20%/-10% als transparenter "
            "Stress-Spread. Keine Kapazitaetsgarantie."
        ),
    }


def _invest_sensitivities(cost_band: dict[str, Any] | None, engine_result: dict[str, Any]) -> list[str]:
    """Sensitivitaeten / Annahmen, die das Kostenband am staerksten treiben.

    Quellen: cost_band.annahmen, kosten.hauptrisikotreiber, route_environment.
    Keine Erfindung — wenn nichts da ist, kommt ein leerer Block zurueck.
    """
    out: list[str] = []
    if isinstance(cost_band, dict):
        for item in cost_band.get("annahmen") or []:
            if str(item).strip():
                out.append(str(item))
        for item in cost_band.get("main_drivers") or []:
            if str(item).strip():
                out.append(str(item))
    kosten = engine_result.get("kosten") if isinstance(engine_result.get("kosten"), dict) else {}
    for item in kosten.get("hauptrisikotreiber") or []:
        if str(item).strip() and str(item) not in out:
            out.append(str(item))
    return out[:8]


def build_invest_report(engine_result: dict[str, Any]) -> dict[str, Any]:
    eingabe = engine_result.get("eingabe", {})
    fazit = engine_result.get("fazit", {})
    n1 = engine_result.get("n1", {})
    warnungen = engine_result.get("warnungen", [])
    empfehlungen = engine_result.get("empfehlungen", [])
    revision = engine_result.get("revision", {})
    projektprofil = engine_result.get("projektprofil", {})
    speicher = engine_result.get("speicher_bewertung", {})
    route_environment = engine_result.get("route_environment", {})
    stakeholder = engine_result.get("stakeholder_bewertung", {})
    transparenz = engine_result.get("transparenz", {})
    scope_meta = resolve_report_scope_meta(engine_result)
    scores = engine_result.get("scores", {})
    if not isinstance(scores, dict):
        scores = {}
    kosten = engine_result.get("kosten", {})
    if not isinstance(kosten, dict):
        kosten = {}
    v2 = engine_result.get("grid_calculation_v2") or {}
    if not isinstance(v2, dict):
        v2 = {}
    persp = v2.get("projektierer_perspective") if isinstance(v2.get("projektierer_perspective"), dict) else None

    nennspannung = float(eingabe.get("nennspannung", 20.0))
    normen = get_normen_fuer_spannungsebene(nennspannung)
    normen_snapshot = [
        {"norm_id": n.norm_id, "titel": n.titel, "stand": n.stand, "kategorie": n.kategorie}
        for n in normen
    ]

    generated_at_iso = (
        str(revision.get("timestamp"))
        if isinstance(revision, dict) and revision.get("timestamp")
        else datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    )
    # Projektierer-Style Kostenbandbreite (mit items + main_drivers) parallel zum
    # bestehenden _cost_band(): wird intern fuer scenarios/sensitivities genutzt,
    # nicht ueber das DTO-Feld exportiert (HTML-Template erwartet die schlanke
    # Form).
    pj_cost_band = _build_cost_band(kosten)
    connection_variants = _build_connection_variants(engine_result, eingabe, nennspannung)
    risks_block = _build_risks(
        engine_result,
        fazit,
        scores,
        pj_cost_band,
        route_environment if isinstance(route_environment, dict) else {},
    )
    sources_block = _sources_from_engine(engine_result, retrieved_at=generated_at_iso)
    location_meta = _build_location_meta(eingabe, persp)
    score_int: int | None
    try:
        score_int = int(float(scores.get("gesamt"))) if scores.get("gesamt") is not None else None
    except (TypeError, ValueError):
        score_int = None
    scenarios_block = _invest_scenarios(pj_cost_band)
    sensitivities_block = _invest_sensitivities(pj_cost_band, engine_result)

    dto = InvestReportDTO(
        report_type="invest",
        report_version="1.0.0",
        app_normstand=APP_VERSION_NORMSTAND,
        engine_revision_hash=revision.get("hash") if isinstance(revision, dict) else None,
        report_generated_at=revision.get("timestamp") if isinstance(revision, dict) else None,
        audit_hash=revision.get("hash") if isinstance(revision, dict) else None,
        offer_id=scope_meta.offer_id,
        package_scope=scope_meta.package_scope,
        package_scope_label=scope_meta.package_scope_label,
        report_scope=scope_meta.report_scope,
        report_scope_label=scope_meta.report_scope_label,
        scope_summary=scope_meta.scope_summary,
        scope_boundary_note=scope_meta.scope_boundary_note,
        ops_followup_required=scope_meta.ops_followup_required,
        standort=str(eingabe.get("ort") or eingabe.get("standort") or "Unbekannt"),
        plz=eingabe.get("plz"),
        leistung_mw=float(eingabe.get("leistung_mw", 0.0)),
        spannungsebene=_spannungsebene_from_kv(nennspannung),
        anschlussart=str(eingabe.get("anschlussart", "Unbekannt")),
        entscheidung=str(fazit.get("entscheidung", "C")),
        geht=str(fazit.get("entscheidung", "C")) != "C",
        auflagen=[str(w) for w in warnungen if isinstance(w, str)],
        n1_status="BESTANDEN" if bool(n1.get("n1_sicher")) else "NICHT BESTANDEN",
        n1_detail=str(n1.get("detail_text") or n1.get("topologie_text", "")),
        empfohlene_massnahmen=[str(x) for x in empfehlungen if isinstance(x, str)],
        normen_snapshot=normen_snapshot,
        kosten_indikation=_kosten_indikation(engine_result),
        cost_band=_cost_band(engine_result),
        site_assessment=_site_assessment(engine_result),
        risk_overview=_risk_overview(engine_result),
        due_diligence_checklist=_due_diligence_checklist(engine_result),
        portfolio_view=_portfolio_view(engine_result),
        data_basis=_data_basis(engine_result),
        visibility_boundary_note=(
            "Die Investsicht zeigt bewusst nur aggregierte Risiko-, Kosten- und Prozessindikatoren. "
            "Rohe Feeder-, Impedanz- oder interne Netzkapazitaetsdaten werden fuer diesen Pfad nicht offengelegt."
        ),
        projektprofil_summary=str(projektprofil.get("summary", "")),
        speicher_summary=str(speicher.get("summary", "")),
        route_environment_summary=str(route_environment.get("summary", "")),
        stakeholder_konflikt=str(stakeholder.get("konflikt_summary", "")),
        recommended_focus=str(stakeholder.get("recommended_focus", "")),
        transparenz_hinweise=_as_text_list(transparenz.get("confidence_notes")),
        disclaimers=_as_text_list(transparenz.get("disclaimers")),
        includes_strategy_section=scope_meta.includes_strategy_section,
        includes_transparency_section=scope_meta.includes_transparency_section,
        includes_cost_section=scope_meta.includes_cost_section,
        operational_boundary_note=(
            "Professional enthaelt operative Anschlussstrategie; Express bleibt ein separater operativer SLA-Zusatz."
            if scope_meta.ops_followup_required
            else None
        ),
        kpi_summary=build_invest_kpi_summary(engine_result),
        process_timeline=build_process_timeline_lines(engine_result),
        gridcheck_score=score_int,
        scores=dict(scores),
        connection_variants=connection_variants,
        risks=risks_block,
        sources=sources_block,
        location_meta=location_meta,
        scenarios=scenarios_block,
        sensitivities=sensitivities_block,
    )
    return asdict(dto)
