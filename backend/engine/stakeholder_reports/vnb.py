from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from compliance import APP_VERSION_NORMSTAND, get_normen_fuer_spannungsebene
from engine.stakeholder_reports.content_blocks import (
    build_process_timeline_lines,
    build_vnb_signature_section,
    build_vnb_technical_review_table,
)
from engine.stakeholder_reports.scope_meta import resolve_report_scope_meta


@dataclass(frozen=True)
class VnbReportDTO:
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
    netzbetreiber_checkliste_hinweis: str
    request_review: list[dict[str, str]]
    technical_precheck: list[dict[str, str]]
    technical_requirements: list[str]
    process_view: list[str]
    data_basis: list[str]
    data_role_summary: str
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
    includes_visualization_note: bool
    operational_boundary_note: str | None
    technical_review_table: list[dict[str, str]]
    signature_section: dict[str, Any]
    process_timeline: list[str]


VNB_NB_CHECKLISTE_HINWEIS = (
    "Für eine verbindliche Einschätzung prüft der zuständige Netzbetreiber projektspezifisch u. a.: "
    "Anschluss- und Übergabestation, vorhandene Schaltfelder, Schutz- und Blindleistungskonzept, "
    "Netz-/Vertragsform und relevante Rahmenbedingungen der TAB/Netznutzungsverträge. "
    "Diese Checkliste-Hinweise ersetzen keine Kapazitätsaussage: freie Netzkapazität wird nur vom VNB "
    "mit belastbarem Datenstand bekanntgegeben."
)


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


def _status_label(is_complete: bool, is_partial: bool = False) -> str:
    if is_complete:
        return "vollstaendig"
    if is_partial:
        return "teilweise"
    return "offen"


def _request_review(eingabe: dict[str, Any], n1: dict[str, Any], dq: dict[str, Any]) -> list[dict[str, str]]:
    has_location = any(
        [
            str(eingabe.get("standort") or "").strip(),
            str(eingabe.get("ort") or "").strip(),
            str(eingabe.get("plz") or "").strip(),
            isinstance(eingabe.get("project_location"), dict),
        ]
    )
    has_core = bool(eingabe.get("leistung_mw")) and bool(eingabe.get("nennspannung"))
    n1_class = str(n1.get("n1_klasse") or "N1-0")
    has_verified_basis = str(eingabe.get("n1_datengrundlage") or "unknown") == "dso_verified"
    has_grid_basis = has_verified_basis or any(
        [
            eingabe.get("sk_mva") is not None,
            eingabe.get("trafo_s_mva") is not None,
            eingabe.get("restkapazitaet_ms_mva") is not None,
            isinstance(eingabe.get("umspannwerk"), dict),
        ]
    )
    return [
        {
            "label": "Antragskern",
            "status": _status_label(has_core and has_location, has_core or has_location),
            "detail": "Standort, Leistung und Spannungsebene fuer die Vorpruefung plausibel erfasst."
            if has_core and has_location
            else "Standort- oder Kerndaten sind fuer die VNB-Vorpruefung noch unvollstaendig.",
        },
        {
            "label": "N-1 / Topologie",
            "status": _status_label(n1_class in {"N1-3", "N1-4"}, n1_class in {"N1-1", "N1-2"}),
            "detail": f"N-1-Screening aktuell als {n1_class} klassifiziert.",
        },
        {
            "label": "Netzdatenbasis",
            "status": _status_label(has_verified_basis, has_grid_basis),
            "detail": f"Datenqualitaet {dq.get('klasse', 'D')} mit Datengrundlage {eingabe.get('n1_datengrundlage', 'unknown')}.",
        },
        {
            "label": "Pruefidentitaet",
            "status": _status_label(bool(str(eingabe.get('antragsteller') or '').strip()), has_location),
            "detail": "Antragsteller- und Projektbezug fuer Audit und Prozesssicht dokumentiert."
            if str(eingabe.get("antragsteller") or "").strip()
            else "Antragsteller / verantwortliche Stelle sollte fuer den VNB-Workflow noch explizit hinterlegt werden.",
        },
    ]


def _technical_precheck(engine_result: dict[str, Any], n1: dict[str, Any]) -> list[dict[str, str]]:
    thermisch = engine_result.get("thermisch", {})
    spannung = engine_result.get("spannung", {})
    kurzschluss = engine_result.get("kurzschluss", {})
    return [
        {
            "label": "Thermische Vorpruefung",
            "status": str(thermisch.get("bewertung", "OFFEN")),
            "detail": str(thermisch.get("text") or "Keine thermische Detailbeschreibung verfuegbar."),
        },
        {
            "label": "Spannungsband",
            "status": str(spannung.get("bewertung", "OFFEN")),
            "detail": str(spannung.get("text") or "Keine Spannungsbewertung verfuegbar."),
        },
        {
            "label": "Kurzschluss / Rueckwirkung",
            "status": str(kurzschluss.get("bewertung", "OFFEN")),
            "detail": str(kurzschluss.get("text") or kurzschluss.get("rw_text") or "Keine Kurzschlussbewertung verfuegbar."),
        },
        {
            "label": "N-1-Screening",
            "status": str(n1.get("bewertung") or "OFFEN"),
            "detail": str(n1.get("detail_text") or n1.get("stufenbegruendung") or n1.get("topologie_text") or ""),
        },
    ]


def _technical_requirements(engine_result: dict[str, Any], n1: dict[str, Any]) -> list[str]:
    warnungen = _as_text_list(engine_result.get("warnungen"))
    empfehlungen = _as_text_list(engine_result.get("empfehlungen"))
    anforderungen = []
    for item in warnungen[:3]:
        anforderungen.append(item)
    for item in empfehlungen[:3]:
        if item not in anforderungen:
            anforderungen.append(item)
    if str(n1.get("n1_klasse") or "N1-0") in {"N1-0", "N1-1", "N1-2"}:
        anforderungen.append(
            "Belastbare Reserveaussage erst nach Nachreichung verifizierter Netz- oder Umspannwerksdaten treffen."
        )
    if not anforderungen:
        anforderungen.append(
            "Keine zusaetzlichen Auflagen erkannt; Standardverfahren und formale Detailpruefung beim VNB bleiben dennoch erforderlich."
        )
    return anforderungen


def _process_view(engine_result: dict[str, Any], scope_meta: Any) -> list[str]:
    revision = engine_result.get("revision", {})
    n1 = engine_result.get("n1", {})
    lines = [
        "Vorpruefung abgeschlossen: Ergebnis bleibt vorlaeufig und ersetzt keine verbindliche Netzanschlussentscheidung.",
        f"N-1-Level aktuell: {n1.get('n1_klasse', 'N1-0')}.",
    ]
    if scope_meta.ops_followup_required:
        lines.append("Professional-Follow-up markiert: operativer Abstimmungs- und Nachlaufpfad ist sichtbar freigeschaltet.")
    if revision.get("hash"):
        lines.append(f"Audit-Hash fuer Rueckverfolgbarkeit vorhanden: {revision['hash']}.")
    return lines


def _data_basis(engine_result: dict[str, Any]) -> list[str]:
    eingabe = engine_result.get("eingabe", {})
    kosten = engine_result.get("kosten", {})
    standort = str(eingabe.get("standort") or eingabe.get("ort") or eingabe.get("plz") or "Unbekannt")
    return [
        f"Projekt- und Standortangaben aus Nutzer-/Antragskontext: {standort}.",
        f"N-1-Datengrundlage: {eingabe.get('n1_datengrundlage', 'unknown')}.",
        f"Kostenreferenz: {kosten.get('quelle', 'n/a')}.",
    ]


def _data_role_summary(engine_result: dict[str, Any]) -> str:
    dq = engine_result.get("datenqualitaet", {})
    eingabe = engine_result.get("eingabe", {})
    return (
        f"Datenqualitaet {dq.get('klasse', 'D')}: {dq.get('text', '')} "
        f"Die Vorpruefung nutzt die deklarierte Datengrundlage {eingabe.get('n1_datengrundlage', 'unknown')} "
        "und macht fehlende Nachweise explizit sichtbar."
    ).strip()


def build_vnb_report(engine_result: dict[str, Any]) -> dict[str, Any]:
    eingabe = engine_result.get("eingabe", {})
    fazit = engine_result.get("fazit", {})
    n1 = engine_result.get("n1", {})
    warnungen = engine_result.get("warnungen", [])
    empfehlungen = engine_result.get("empfehlungen", [])
    revision = engine_result.get("revision", {})
    datenqualitaet = engine_result.get("datenqualitaet", {})
    projektprofil = engine_result.get("projektprofil", {})
    speicher = engine_result.get("speicher_bewertung", {})
    route_environment = engine_result.get("route_environment", {})
    stakeholder = engine_result.get("stakeholder_bewertung", {})
    transparenz = engine_result.get("transparenz", {})
    scope_meta = resolve_report_scope_meta(engine_result)

    nennspannung = float(eingabe.get("nennspannung", 20.0))
    normen = get_normen_fuer_spannungsebene(nennspannung)
    normen_snapshot = [
        {"norm_id": n.norm_id, "titel": n.titel, "stand": n.stand, "kategorie": n.kategorie}
        for n in normen
    ]

    dto = VnbReportDTO(
        report_type="vnb",
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
        netzbetreiber_checkliste_hinweis=VNB_NB_CHECKLISTE_HINWEIS,
        request_review=_request_review(eingabe, n1, datenqualitaet),
        technical_precheck=_technical_precheck(engine_result, n1),
        technical_requirements=_technical_requirements(engine_result, n1),
        process_view=_process_view(engine_result, scope_meta),
        data_basis=_data_basis(engine_result),
        data_role_summary=_data_role_summary(engine_result),
        visibility_boundary_note=(
            "Dieser VNB-Report zeigt nur die fuer die Vorpruefung verwendeten Projekt- und Netzgrundlagen. "
            "Er gibt keine freie interne Netzkapazitaet oder stillschweigende Freigabe interner Netzdaten preis."
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
        includes_visualization_note=scope_meta.includes_visualization_note,
        operational_boundary_note=(
            "Professional markiert den Run fuer operative Abstimmung mit Anschlussstrategie und Visualisierungspfad."
            if scope_meta.ops_followup_required
            else None
        ),
        technical_review_table=build_vnb_technical_review_table(engine_result),
        signature_section=build_vnb_signature_section(),
        process_timeline=build_process_timeline_lines(engine_result),
    )
    return asdict(dto)
