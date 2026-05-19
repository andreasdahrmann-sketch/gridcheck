from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from compliance import APP_VERSION_NORMSTAND, get_normen_fuer_spannungsebene
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
    )
    return asdict(dto)

