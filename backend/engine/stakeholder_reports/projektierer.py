from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from compliance import APP_VERSION_NORMSTAND, get_normen_fuer_spannungsebene
from engine.gridcheck_report_mapper import _sources_from_engine
from engine.stakeholder_reports.content_blocks import (
    build_bkz_hint_text,
    build_eeg_checklist,
    build_process_timeline_lines,
    build_reactive_checklist,
    build_technical_details_table,
)
from engine.stakeholder_reports.scope_meta import resolve_report_scope_meta


@dataclass(frozen=True)
class ProjektiererReportDTO:
    report_type: str
    report_version: str
    app_normstand: str
    engine_revision_hash: str | None
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
    projektprofil_summary: str
    speicher_summary: str
    route_environment_summary: str
    stakeholder_konflikt: str
    recommended_focus: str
    transparenz_hinweise: list[str]
    disclaimers: list[str]
    includes_strategy_section: bool
    includes_transparency_section: bool
    includes_visualization_note: bool
    operational_boundary_note: str | None
    grid_calculation_version: str | None
    projektierer_v2_lines: list[str]
    technical_details_table: list[dict[str, str]]
    eeg_checklist: list[str]
    reactive_checklist: list[str]
    process_timeline: list[str]
    bkz_hint: str | None
    warnungen: list[str]
    # P1/P2: Felder fuer Score-Hero, Kostenband, Risiko-/Variantenblock, Datenquellen.
    # Defaults sind backwards-kompatibel: bestehende Aufrufer ohne diese Felder
    # rendern den Report wie bisher, nur ohne die neuen Sektionen.
    report_generated_at: str | None = None
    gridcheck_score: int | None = None
    scores: dict[str, Any] = field(default_factory=dict)
    cost_band: dict[str, Any] | None = None
    connection_variants: list[dict[str, Any]] = field(default_factory=list)
    risks: dict[str, Any] = field(default_factory=dict)
    sources: list[dict[str, Any]] = field(default_factory=list)
    location_meta: dict[str, Any] = field(default_factory=dict)


_FEED_IN_CLASS_LABELS = {
    "none": "EEG §9 2023: unter 25 kW AC (kein Einspeisemanagement)",
    "remote_control": "EEG §9 2023: 25–<100 kW AC (Fernsteuerbarkeit prüfen)",
    "direct_marketing": "EEG §9 2023: ≥100 kW AC (Direktvermarktung / Bilanzkreis)",
}


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


def _build_projektierer_v2_lines(
    v2: dict[str, Any],
    persp: dict[str, Any] | None,
) -> list[str]:
    """Structured PDF/HTML lines from grid_calculation_v2 + projektierer_perspective."""
    lines: list[str] = []
    version = v2.get("calculation_version")
    if version:
        lines.append(f"Engine grid_calculation_v2: {version}")

    if isinstance(persp, dict):
        plant = persp.get("plant_type_label") or persp.get("plant_type")
        ac_kw = persp.get("ac_kw")
        dc_kwp = persp.get("dc_kwp")
        screening = persp.get("screening_power_kw")
        if plant and ac_kw is not None:
            line = f"Anlage: {plant}, AC {float(ac_kw):.0f} kW"
            if dc_kwp is not None:
                line += f", DC {float(dc_kwp):.0f} kWp"
            if screening is not None:
                line += f", Screening {float(screening):.0f} kW"
            lines.append(line)
        fic = persp.get("feed_in_management_class")
        if fic:
            lines.append(_FEED_IN_CLASS_LABELS.get(str(fic), f"Einspeisemanagement: {fic}"))
        tl = persp.get("process_timeline") or {}
        if isinstance(tl, dict) and tl.get("estimated_total"):
            lines.append(f"Zeitplan (heuristisch): {tl['estimated_total']}")
        bkz = persp.get("bkz_hint") or {}
        if isinstance(bkz, dict) and bkz.get("hint"):
            lines.append(f"BKZ-Hinweis: {bkz['hint']}")
        nvp = persp.get("nvp_recommendation") or {}
        if isinstance(nvp, dict):
            parts = [
                str(nvp.get("suggested_voltage_level") or "").strip(),
                str(nvp.get("nearest_node_hint") or "").strip(),
            ]
            parts = [p for p in parts if p]
            if parts:
                lines.append(f"NVP-Empfehlung (heuristisch): {' — '.join(parts)}")
            if nvp.get("disclaimer"):
                lines.append(str(nvp["disclaimer"]))
        tab = persp.get("tab_disclaimer") or {}
        if isinstance(tab, dict) and tab.get("message"):
            lines.append(f"TAB: {tab['message']}")

    eeg = v2.get("eeg_feed_in_screening")
    if isinstance(eeg, dict) and eeg.get("applicable"):
        eeg_class = eeg.get("feed_in_management_class")
        if eeg_class and not any("EEG" in ln for ln in lines):
            lines.append(_FEED_IN_CLASS_LABELS.get(str(eeg_class), f"EEG-Klasse: {eeg_class}"))
        for hint in _as_text_list(eeg.get("hints"))[:3]:
            lines.append(f"EEG-Hinweis: {hint}")

    reactive = v2.get("reactive_power_screening")
    if isinstance(reactive, dict) and reactive.get("applicable"):
        for item in reactive.get("checklist") or []:
            if isinstance(item, dict) and item.get("topic"):
                lines.append(f"Blindleistung: {item['topic']} — {item.get('note', '')}")

    norms = v2.get("norm_references_applied")
    if isinstance(norms, list) and norms:
        refs = []
        for n in norms[:4]:
            if isinstance(n, dict):
                refs.append(str(n.get("reference") or n.get("norm_id") or ""))
        refs = [r for r in refs if r]
        if refs:
            lines.append("Normen (Screening): " + "; ".join(refs))

    return lines


def _f(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


_DE_RISK_TO_LEVEL = {
    "niedrig": "low",
    "mittel": "medium",
    "hoch": "high",
    "sehr_hoch": "critical",
}


def _de_risk_to_level(level: Any) -> str:
    if not level:
        return "unknown"
    return _DE_RISK_TO_LEVEL.get(str(level).strip().lower(), "unknown")


def _build_cost_band(kosten: dict[str, Any]) -> dict[str, Any] | None:
    """Liefert eine Kostenbandbreite (Niedrig / Basis / Hoch) plus Confidence
    und Hauptrisikotreiber. Niemals stille Scheingenauigkeit — fehlende Felder
    werden weggelassen, nicht erfunden."""
    if not isinstance(kosten, dict):
        return None
    base_e = int(_f(kosten.get("band_basis_eur") or kosten.get("investition_gesamt_eur"), 0))
    low_e = int(_f(kosten.get("band_niedrig_eur"), 0))
    high_e = int(_f(kosten.get("band_hoch_eur"), 0))
    if base_e <= 0 and low_e <= 0 and high_e <= 0:
        return None
    if base_e <= 0:
        base_e = max(low_e, high_e, 1)
    if low_e <= 0:
        low_e = int(base_e * 0.85)
    if high_e <= 0:
        high_e = int(base_e * 1.15)

    conf_pct = _f(kosten.get("konfidenz_prozent"), 50.0)
    conf: str = "high" if conf_pct >= 70 else ("medium" if conf_pct >= 45 else "low")

    items: list[dict[str, Any]] = []
    trasse = int(_f(kosten.get("kosten_trasse_eur"), 0))
    if trasse > 0:
        items.append({
            "label": "Trasse / Kabel / Tiefbau",
            "low": max(0, int(trasse * 0.85)),
            "base": trasse,
            "high": int(trasse * 1.15),
            "confidence": conf,
        })
    station = int(_f(kosten.get("kosten_station_eur"), 0))
    if station > 0:
        items.append({
            "label": "Station / Schaltanlage",
            "low": max(0, int(station * 0.85)),
            "base": station,
            "high": int(station * 1.20),
            "confidence": conf,
        })
    planung = int(_f(kosten.get("kosten_planung_eur"), 0)) + int(
        _f(kosten.get("kosten_genehmigung_eur"), 0)
    )
    if planung > 0:
        items.append({
            "label": "Planung / Genehmigung",
            "low": max(0, int(planung * 0.90)),
            "base": planung,
            "high": int(planung * 1.15),
            "confidence": conf,
        })

    main_drivers = [
        str(x) for x in (kosten.get("hauptrisikotreiber") or []) if str(x).strip()
    ]
    return {
        "currency": "EUR",
        "niedrig_eur": low_e,
        "basis_eur": base_e,
        "hoch_eur": high_e,
        "confidence": conf,
        "confidence_pct": int(conf_pct),
        "items": items,
        "main_drivers": main_drivers[:8],
        "annahmen": [
            str(a) for a in (kosten.get("band_annahmen") or []) if str(a).strip()
        ],
        "quelle": str(kosten.get("quelle") or "") or None,
    }


def _voltage_label_for_kv(u_kv: float) -> str:
    if u_kv < 1:
        return "NS (< 1 kV)"
    if u_kv <= 35:
        return f"MS ({u_kv:g} kV)"
    if u_kv <= 110:
        return f"HS ({u_kv:g} kV)"
    return f"HöS ({u_kv:g} kV)"


def _build_connection_variants(
    engine_result: dict[str, Any], eingabe: dict[str, Any], u_kv: float
) -> list[dict[str, Any]]:
    """Anschlussvarianten-Tabelle.
    - Bevorzugt explizite Liste aus engine_result['connection_variants'].
    - Fallback: ein Modell-Kandidat aus den Eingaben (Distanz / Spannung).
    Layout im Renderer ist N>=1 fähig.
    """
    raw = engine_result.get("connection_variants")
    out: list[dict[str, Any]] = []
    if isinstance(raw, list):
        for entry in raw:
            if not isinstance(entry, dict):
                continue
            out.append({
                "label": str(entry.get("label") or "Variante"),
                "voltage_label": str(
                    entry.get("voltage_label")
                    or _voltage_label_for_kv(_f(entry.get("voltage_kv"), u_kv))
                ),
                "distance_km": float(_f(entry.get("distance_km"), 0.0)),
                "confidence": str(entry.get("confidence") or "medium"),
                "cost_risk": str(entry.get("cost_risk") or "unknown"),
                "route_risk": str(entry.get("route_risk") or "unknown"),
                "comment": str(entry.get("comment") or ""),
            })
    if out:
        return out

    dist = _f(eingabe.get("entfernung_km"), 0.0)
    return [
        {
            "label": "Modell-Anschluss (heuristisch)",
            "voltage_label": _voltage_label_for_kv(u_kv),
            "distance_km": round(dist, 3),
            "confidence": "medium",
            "cost_risk": "medium",
            "route_risk": "medium",
            "comment": "1 Kandidat verfuegbar — OSM-/Asset-Pipeline liefert spaeter weitere Varianten.",
        }
    ]


def _build_risks(
    engine_result: dict[str, Any],
    fazit: dict[str, Any],
    scores: dict[str, Any],
    cost_band: dict[str, Any] | None,
    route_environment: dict[str, Any],
) -> dict[str, Any]:
    """Konsolidierter Risiko-Block fuer Renderer + revisionssichere Doku."""
    ents = str(fazit.get("entscheidung") or "B").strip().upper()
    g = _f(scores.get("gesamt"), 50.0)
    if ents == "C" or g < 35:
        overall = "high"
    elif ents == "B" or g < 60:
        overall = "medium"
    elif ents == "A" and g >= 70:
        overall = "low"
    else:
        overall = "medium"
    grid_r = overall

    route_r = _de_risk_to_level(route_environment.get("risk_level"))

    cost_r = "unknown"
    if cost_band and cost_band.get("basis_eur"):
        base_e = int(cost_band["basis_eur"]) or 1
        high_e = int(cost_band.get("hoch_eur") or base_e)
        if high_e > base_e * 1.35:
            cost_r = "high"
        elif high_e > base_e * 1.15:
            cost_r = "medium"
        else:
            cost_r = "low"

    timeline_r = "medium"

    dq_block = engine_result.get("datenqualitaet") if isinstance(
        engine_result.get("datenqualitaet"), dict
    ) else {}
    dq_class = str(dq_block.get("klasse") or "C").strip().upper()
    if dq_class in ("D", "C"):
        data_q = "high"
    elif dq_class == "B":
        data_q = "medium"
    elif dq_class == "A":
        data_q = "low"
    else:
        data_q = "unknown"

    return {
        "overall": overall,
        "grid": grid_r,
        "route": route_r,
        "cost": cost_r,
        "timeline": timeline_r,
        "data_quality": data_q,
    }


def _build_location_meta(
    eingabe: dict[str, Any], persp: dict[str, Any] | None
) -> dict[str, Any]:
    loc = eingabe.get("project_location") if isinstance(eingabe.get("project_location"), dict) else {}
    out: dict[str, Any] = {
        "ort": str(eingabe.get("ort") or eingabe.get("standort") or ""),
        "plz": str(eingabe.get("plz") or ""),
        "bundesland": str(eingabe.get("bundesland") or loc.get("federal_state") or ""),
        "latitude": loc.get("latitude"),
        "longitude": loc.get("longitude"),
        "vnb_gebiet": str(eingabe.get("vnb_gebiet") or ""),
    }
    if isinstance(persp, dict):
        nvp = persp.get("nvp_recommendation") if isinstance(persp.get("nvp_recommendation"), dict) else {}
        if isinstance(nvp, dict):
            if nvp.get("suggested_voltage_level"):
                out["recommended_voltage_level"] = str(nvp.get("suggested_voltage_level"))
            if nvp.get("nearest_node_hint"):
                out["nearest_node_hint"] = str(nvp.get("nearest_node_hint"))
    return out


def build_projektierer_report(engine_result: dict[str, Any]) -> dict[str, Any]:
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
    v2_lines = _build_projektierer_v2_lines(v2, persp)
    scope_meta = resolve_report_scope_meta(engine_result)

    nennspannung = float(eingabe.get("nennspannung", 20.0))
    normen = get_normen_fuer_spannungsebene(nennspannung)
    normen_snapshot = [
        {"norm_id": n.norm_id, "titel": n.titel, "stand": n.stand, "kategorie": n.kategorie}
        for n in normen
    ]

    extra_auflagen: list[str] = []
    if isinstance(persp, dict):
        tl = persp.get("process_timeline") or {}
        if isinstance(tl, dict) and tl.get("estimated_total"):
            extra_auflagen.append(f"Zeitplan (heuristisch): {tl['estimated_total']}")
        bkz = persp.get("bkz_hint") or {}
        if isinstance(bkz, dict) and bkz.get("hint"):
            extra_auflagen.append(str(bkz["hint"]))
        tab = persp.get("tab_disclaimer") or {}
        if isinstance(tab, dict) and tab.get("message"):
            extra_auflagen.append(str(tab["message"]))
        kum = persp.get("kumulation_warning") or {}
        if isinstance(kum, dict) and kum.get("message"):
            extra_auflagen.append(str(kum["message"]))

    # P1/P2 Sektionen: Score-Hero, Kostenband, Risiko-Block, Anschlussvarianten,
    # Datenquellen, Standort/Netzumfeld. Werden im Renderer + im PDF angezeigt.
    generated_at_iso = (
        str(revision.get("timestamp"))
        if isinstance(revision, dict) and revision.get("timestamp")
        else datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    )
    cost_band = _build_cost_band(kosten)
    connection_variants = _build_connection_variants(engine_result, eingabe, nennspannung)
    risks_block = _build_risks(
        engine_result, fazit, scores, cost_band, route_environment if isinstance(route_environment, dict) else {}
    )
    sources_block = _sources_from_engine(engine_result, retrieved_at=generated_at_iso)
    location_meta = _build_location_meta(eingabe, persp)
    score_int: int | None
    try:
        score_int = int(float(scores.get("gesamt"))) if scores.get("gesamt") is not None else None
    except (TypeError, ValueError):
        score_int = None

    dto = ProjektiererReportDTO(
        report_type="projektierer",
        report_version="1.0.0",
        app_normstand=APP_VERSION_NORMSTAND,
        engine_revision_hash=revision.get("hash") if isinstance(revision, dict) else None,
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
        auflagen=[str(w) for w in warnungen if isinstance(w, str)] + extra_auflagen,
        n1_status="BESTANDEN" if bool(n1.get("n1_sicher")) else "NICHT BESTANDEN",
        n1_detail=str(n1.get("detail_text") or n1.get("topologie_text", "")),
        empfohlene_massnahmen=[str(x) for x in empfehlungen if isinstance(x, str)],
        normen_snapshot=normen_snapshot,
        projektprofil_summary=str(projektprofil.get("summary", "")),
        speicher_summary=str(speicher.get("summary", "")),
        route_environment_summary=str(route_environment.get("summary", "")),
        stakeholder_konflikt=str(stakeholder.get("konflikt_summary", "")),
        recommended_focus=str(stakeholder.get("recommended_focus", "")),
        transparenz_hinweise=_as_text_list(transparenz.get("confidence_notes")),
        disclaimers=_as_text_list(transparenz.get("disclaimers")),
        includes_strategy_section=scope_meta.includes_strategy_section,
        includes_transparency_section=scope_meta.includes_transparency_section,
        includes_visualization_note=scope_meta.includes_visualization_note,
        operational_boundary_note=(
            "Professional enthaelt operative Anschlussstrategie und erzeugt einen Follow-up-Pfad fuer die weitere Bearbeitung."
            if scope_meta.ops_followup_required
            else None
        ),
        grid_calculation_version=str(v2.get("calculation_version") or "") or None,
        projektierer_v2_lines=v2_lines,
        technical_details_table=build_technical_details_table(engine_result),
        eeg_checklist=build_eeg_checklist(engine_result),
        reactive_checklist=build_reactive_checklist(engine_result),
        process_timeline=build_process_timeline_lines(engine_result),
        bkz_hint=build_bkz_hint_text(engine_result),
        warnungen=[str(w) for w in warnungen if isinstance(w, str)],
        report_generated_at=generated_at_iso,
        gridcheck_score=score_int,
        scores=dict(scores),
        cost_band=cost_band,
        connection_variants=connection_variants,
        risks=risks_block,
        sources=sources_block,
        location_meta=location_meta,
    )
    return asdict(dto)

