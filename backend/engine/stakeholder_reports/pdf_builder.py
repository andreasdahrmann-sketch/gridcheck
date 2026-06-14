"""
High-quality ReportLab PDF builder for stakeholder reports (Projektierer, VNB,
Invest). Three stakeholder-specific Platypus stories share a common visual
system (brand bar, palette, status badges, KPI cards, signature blocks,
deterministic SHA-256 footer hash). Public entry point stays
``build_stakeholder_report_pdf(report) -> bytes`` for backward compatibility
with `api/v2_reports.py` and the existing tests.

Visual system reference: docs/PDF_REPORTS.md (Layout-Stand).
"""
from __future__ import annotations

import hashlib
import io
import json
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from engine.stakeholder_reports.pdf_layout import (
    FONT_BOLD,
    FONT_REGULAR,
    StakeholderPalette,
    alt_table,
    body_bold_style,
    body_style,
    brand_header,
    bulleted_block,
    decision_picks,
    kpi_strip,
    kv_table,
    lined_field,
    make_footer_callback,
    muted_style,
    p,
    p_html,
    palette_for,
    section,
    signature_block,
    status_badge_paragraph,
    summary_box,
)

try:  # pragma: no cover - optional dependency, only used for richer plant labels
    from engine.plant_types import PLANT_TYPE_CONFIG, PlantType
except Exception:  # pragma: no cover
    PLANT_TYPE_CONFIG = {}  # type: ignore[assignment]
    PlantType = None  # type: ignore[assignment]


_SELF_REFERENTIAL_KEYS = frozenset(
    {
        "audit_hash",
        "report_generated_at",
        "report_revision",
        "report_revision_number",
        "report_revision_uuid",
        "report_verify_path",
    }
)

_STAKEHOLDER_TITLES = {
    "projektierer": "Stakeholder-Report Projektierer",
    "vnb": "Stakeholder-Report Netzbetreiber",
    "invest": "Stakeholder-Report Invest / Management",
}

_STAKEHOLDER_SUBTITLES = {
    "projektierer": "Technische Vorplanung & §9 EEG 2023",
    "vnb": "Strukturierte Vorprüfung & Entscheidungsvorlage",
    "invest": "Due-Diligence-Sicht & Investitionsindikatoren",
}

_VOLTAGE_LABELS = {
    "NS": "Niederspannung",
    "MS": "Mittelspannung",
    "HS": "Hochspannung",
    "LOW": "Niederspannung",
    "MEDIUM": "Mittelspannung",
    "HIGH": "Hochspannung",
}

_CONNECTION_LABELS = {
    "einspeisung": "Einspeisung",
    "entnahme": "Entnahme",
    "verbrauch": "Entnahme",
    "speicher": "Bidirektional (Speicher)",
    "bidirektional": "Bidirektional",
    "mixed": "Bidirektional",
}

_DECISION_BADGES = {
    "A": ("Geht", "pass", "Anschlussfähig im Screening — Standardweg empfohlen."),
    "B": (
        "Geht mit Auflagen",
        "warn",
        "Vorprüfung positiv, aber an Bedingungen / Nachweise gekoppelt.",
    ),
    "C": (
        "Geht-nicht (vorläufig)",
        "fail",
        "Screening zeigt Engpässe — Re-Design oder Variantenprüfung erforderlich.",
    ),
}

_VNB_CHECKLIST_10 = [
    "Antragsformular vollständig (Antragsteller, Standort, Anlagentyp)",
    "Leistungs- und Spannungsdaten plausibel zur deklarierten Spannungsebene",
    "Netzanschlusspunkt (NVP) und Übergabestation definiert",
    "Schutz-, Mess- und Steuerungskonzept dokumentiert",
    "Blindleistungs-/Q-Modus mit TAB des VNB abgeglichen",
    "EEG-Einspeisemanagement (§9 EEG 2023) entsprechend Leistungsklasse",
    "N-1-/Topologiebewertung schlüssig (Datengrundlage benannt)",
    "Kurzschlussverhältnis und Rückwirkung im plausiblen Band",
    "BKZ-Indikation und Vertragsform (TAB / NNV) referenziert",
    "Erforderliche Nachweise und Auflagen schriftlich festgehalten",
]

_PROJEKTIERER_NORMS_FALLBACK = [
    "VDE-AR-N 4105 (Niederspannung, Erzeugungsanlagen)",
    "VDE-AR-N 4110 (Mittelspannung, Erzeugungsanlagen)",
    "VDE-AR-N 4120 (Hochspannung, Erzeugungsanlagen)",
    "§9 EEG 2023 — Einspeisemanagement",
    "§14a / §25 NAV — Baukostenzuschuss (BKZ)",
    "DIN EN 60909 — Kurzschlussberechnung",
]

_DISCLAIMER_LINE = (
    "Vorläufige Diagnose – keine verbindliche Netzanschlusszusage. "
    "Keine Kapazitätsgarantie, freie Netzkapazität nur mit belastbarem VNB-Datenstand."
)


# ============================================================================
# Hash + ID helpers
# ============================================================================
def _canonical_input_for_hash(report: dict[str, Any]) -> str:
    """Stable JSON of report payload with self-referential metadata stripped.

    perf: shallow copy ist ausreichend, weil nur Top-Level-Keys via pop()
    entfernt werden; json.dumps liest danach nur und mutiert die Nested-Daten
    nicht. deepcopy auf grossen Report-Dicts war ein messbarer Hotspot.
    """
    snapshot = dict(report)
    for key in _SELF_REFERENTIAL_KEYS:
        snapshot.pop(key, None)
    return json.dumps(snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def compute_footer_hash(report: dict[str, Any]) -> str:
    """Public helper — full SHA-256 hex over a stable view of the report."""
    raw = _canonical_input_for_hash(report)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _short_hash(full_hash: str, length: int = 12) -> str:
    return (full_hash or "").strip()[:length] or ("0" * length)


def _report_id(report: dict[str, Any], full_hash: str) -> str:
    """Stable identifier: prefer persisted revision uuid, fall back to hash prefix."""
    rev = report.get("report_revision")
    if isinstance(rev, dict):
        uid = str(rev.get("uuid") or "").strip()
        if uid:
            return uid
    uid = str(report.get("report_revision_uuid") or "").strip()
    if uid:
        return uid
    return f"GC-{_short_hash(full_hash, 16).upper()}"


# ============================================================================
# Label helpers
# ============================================================================
def _voltage_label(raw: Any) -> str:
    token = str(raw or "").strip().upper()
    if not token:
        return "n/a"
    return _VOLTAGE_LABELS.get(token, str(raw))


def _connection_label(raw: Any) -> str:
    token = str(raw or "").strip().lower()
    if not token:
        return "n/a"
    return _CONNECTION_LABELS.get(token, str(raw))


def _plant_label(report: dict[str, Any]) -> str:
    """Try plant_types.py for canonical labels, else fall back to engine label."""
    persp = _persp(report)
    if persp:
        lbl = persp.get("plant_type_label")
        if lbl:
            return str(lbl)
        pt_key = str(persp.get("plant_type") or "").strip().lower()
        if pt_key and PlantType is not None:
            try:
                cfg = PLANT_TYPE_CONFIG.get(PlantType(pt_key))
                if cfg is not None:
                    return cfg.label
            except (ValueError, KeyError):
                pass
    raw = str(report.get("anlagentyp") or "").strip()
    return raw or "Anlage"


def _fmt_num(value: Any, *, digits: int = 2, suffix: str = "", default: str = "—") -> str:
    if value is None or value == "":
        return default
    try:
        num = float(value)
    except (TypeError, ValueError):
        return str(value)
    base = f"{num:.{digits}f}".rstrip("0").rstrip(".") if digits > 0 else f"{num:.0f}"
    return f"{base}{suffix}"


def _fmt_eur(value: Any, default: str = "—") -> str:
    if value is None or value == "":
        return default
    try:
        num = float(value)
    except (TypeError, ValueError):
        return str(value)
    if abs(num) >= 1_000_000:
        return f"{num / 1_000_000:.2f} Mio. €"
    if abs(num) >= 1_000:
        return f"{num / 1_000:.0f} Tsd. €"
    return f"{num:.0f} €"


def _safe(value: Any, default: str = "—") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text or default


def _persp(report: dict[str, Any]) -> dict[str, Any] | None:
    """Pull out projektierer_perspective from the v2 calculation block."""
    v2 = report.get("grid_calculation_v2")
    if not isinstance(v2, dict):
        return None
    persp = v2.get("projektierer_perspective")
    if isinstance(persp, dict):
        return persp
    return None


# ============================================================================
# Generic story helpers
# ============================================================================
def _build_meta_strip(
    palette: StakeholderPalette,
    report: dict[str, Any],
    *,
    report_id: str,
    full_hash: str,
    doc_width: float,
) -> Table:
    """Tiny grey strip under the brand bar with report ID + version + hash."""
    style = muted_style(palette)
    bold = body_bold_style(palette)
    version = _safe(report.get("report_version"))
    normstand = _safe(report.get("app_normstand"))
    package = _safe(
        report.get("report_scope_label") or report.get("package_scope_label") or "Standard",
    )
    rows = [
        [
            Paragraph(f"<b>Report-ID</b><br/>{report_id}", style),
            Paragraph(f"<b>Version</b><br/>{version} / Normstand {normstand}", style),
            Paragraph(f"<b>Paket</b><br/>{package}", style),
            Paragraph(
                f"<b>SHA-256</b><br/>{_short_hash(full_hash, 16)}…", style
            ),
        ]
    ]
    t = Table(rows, colWidths=[doc_width / 4] * 4)
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(palette.zebra)),
                ("LINEBELOW", (0, 0), (-1, -1), 0.5, colors.HexColor(palette.border)),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    _ = bold  # kept for readability of intent
    return t


def _disclaimer_paragraph(palette: StakeholderPalette) -> Paragraph:
    style = muted_style(palette)
    style = ParagraphStyle(
        "disclaimer",
        parent=style,
        textColor=colors.HexColor(palette.text_muted),
        fontSize=8.5,
        leading=11,
    )
    return Paragraph(
        "<b>Hinweis:</b> Vorläufige Diagnose auf Basis eines automatisierten Screenings. "
        "Keine verbindliche Netzanschlusszusage und keine Kapazitätsgarantie. "
        "N-1-Aussage maximal bis N1-2 ohne verifizierte Netzbetreiberdaten. "
        "Bindende Aussagen erteilt ausschließlich der zuständige Verteilnetzbetreiber (VNB).",
        style,
    )


def _ensure_three_lines(items: list[str], minimum: int = 3) -> list[str]:
    cleaned = [str(x).strip() for x in items if str(x).strip()]
    while len(cleaned) < minimum:
        cleaned.append("—")
    return cleaned


# ============================================================================
# Projektierer story
# ============================================================================
def _decision_summary(report: dict[str, Any]) -> tuple[str, str, str]:
    decision = str(report.get("entscheidung") or "C").strip().upper() or "C"
    if decision not in _DECISION_BADGES:
        decision = "C"
    label, severity, default_msg = _DECISION_BADGES[decision]
    msg_parts = [default_msg]
    n1_detail = _safe(report.get("n1_detail"), default="")
    if n1_detail:
        msg_parts.append(f"N-1: {n1_detail}")
    return f"Entscheidung {decision} — {label}", severity, " ".join(msg_parts)


def _projektierer_cover(
    palette: StakeholderPalette,
    report: dict[str, Any],
    *,
    report_id: str,
    doc_width: float,
) -> list[Any]:
    persp = _persp(report) or {}
    plant_label = _plant_label(report)
    ac_kw = persp.get("ac_kw")
    dc_kwp = persp.get("dc_kwp")
    leistung_mw = report.get("leistung_mw")
    if ac_kw is None and leistung_mw is not None:
        try:
            ac_kw = float(leistung_mw) * 1000.0
        except (TypeError, ValueError):
            ac_kw = None

    plz = _safe(report.get("plz"))
    standort = _safe(report.get("standort"))
    ort_zeile = f"{standort} (PLZ {plz})" if plz != "—" else standort

    rows: list[tuple[str, Any]] = [
        ("Projekt", _safe(report.get("standort") or report.get("project_name"))),
        ("Anlagentyp", plant_label),
        ("Standort / PLZ", ort_zeile),
        ("Spannungsebene", _voltage_label(report.get("spannungsebene"))),
        ("Anschlussart", _connection_label(report.get("anschlussart"))),
        ("AC-Leistung", _fmt_num(ac_kw, digits=0, suffix=" kW")),
    ]
    if dc_kwp is not None:
        rows.append(("DC-Leistung (PV)", _fmt_num(dc_kwp, digits=0, suffix=" kWp")))
    rows.append(("Datum", _safe(report.get("report_generated_at")).split("T", 1)[0]))
    rows.append(("Report-ID", report_id))

    return [
        kv_table(palette, rows, doc_width=doc_width, boxed=True),
        Spacer(1, 4 * mm),
    ]


def _build_kpi_status_table(
    palette: StakeholderPalette, report: dict[str, Any], *, doc_width: float
) -> Table:
    persp = _persp(report) or {}
    rows: list[list[Any]] = []

    technical_table = report.get("technical_details_table")
    spannung_row = {}
    leitung_row = {}
    kurz_row = {}
    if isinstance(technical_table, list):
        for entry in technical_table:
            if not isinstance(entry, dict):
                continue
            key = str(entry.get("kenngroesse") or "").strip().lower()
            if key.startswith("spannung"):
                spannung_row = entry
            elif key.startswith("kurzschluss"):
                kurz_row = entry
            elif key.startswith("leitung") or "querschnitt" in key:
                leitung_row = entry

    thermisch_bewertung = report.get("thermisch_bewertung") or ""

    # Fallbacks to perspective if technical_details_table missing
    persp_du = persp.get("delta_u_prozent")
    persp_ik = persp.get("ik_referenz_ka")

    delta_u_wert = spannung_row.get("wert") if spannung_row else _fmt_num(
        persp_du, digits=2, suffix=" %"
    )
    ik_wert = kurz_row.get("wert") if kurz_row else _fmt_num(
        persp_ik, digits=1, suffix=" kA"
    )
    leitung_wert = (
        leitung_row.get("wert")
        if leitung_row
        else _fmt_num(persp.get("querschnitt_mm2"), digits=0, suffix=" mm²")
    )

    status_du = spannung_row.get("hinweis") or "Screening"
    status_ik = kurz_row.get("hinweis") or "Screening"
    status_leitung = leitung_row.get("hinweis") or "Screening"

    headers = ["Kenngröße", "Wert", "Norm-Bezug", "Status"]

    rows.append(
        [
            "Spannungsfall (dU)",
            _safe(delta_u_wert),
            "VDE-AR-N 4105 / 4110",
            status_badge_paragraph(palette, status_du),
        ]
    )
    rows.append(
        [
            "Kurzschluss Ik",
            _safe(ik_wert),
            "DIN EN 60909",
            status_badge_paragraph(palette, status_ik),
        ]
    )
    rows.append(
        [
            "Thermische Auslastung",
            _safe(
                _fmt_num(persp.get("thermische_auslastung_prozent"), digits=0, suffix=" %"),
                default=_safe(thermisch_bewertung),
            ),
            "VDE-AR-N 4110 §6",
            status_badge_paragraph(palette, thermisch_bewertung or "OFFEN"),
        ]
    )
    rows.append(
        [
            "Querschnitt / Leitung",
            _safe(leitung_wert),
            "DIN VDE 0276 / 4110",
            status_badge_paragraph(palette, status_leitung),
        ]
    )
    rows.append(
        [
            "N-1-Klasse",
            _safe(persp.get("n1_klasse") or report.get("n1_status")),
            "VDE-AR-N 4110 §10",
            status_badge_paragraph(palette, report.get("n1_status")),
        ]
    )

    return alt_table(
        palette,
        headers,
        rows,
        col_widths=[doc_width * 0.30, doc_width * 0.24, doc_width * 0.26, doc_width * 0.20],
    )


_RISK_LEVEL_LABELS = {
    "low": ("Niedrig", "GRUEN"),
    "medium": ("Mittel", "GELB"),
    "high": ("Hoch", "ROT"),
    "critical": ("Kritisch", "ROT"),
    "unknown": ("Unbekannt", "OFFEN"),
}


def _confidence_label(value: Any) -> str:
    token = str(value or "").strip().lower()
    return {"low": "niedrig", "medium": "mittel", "high": "hoch"}.get(token, token or "—")


def _projektierer_score_hero(
    palette: StakeholderPalette, report: dict[str, Any], *, doc_width: float
) -> Table:
    """Kompakter Hero-Block fuer den Projektierer-Report (Score-Zahl + Verdict-Badge).

    Stilistisch an _invest_hero angelehnt, aber kleinere Schrift / kompakter
    fuer den technischen Bericht.
    """
    score: int | None = None
    if report.get("gridcheck_score") is not None:
        try:
            score = int(report["gridcheck_score"])
        except (TypeError, ValueError):
            score = None
    if score is None:
        scores = report.get("scores")
        if isinstance(scores, dict):
            try:
                score = int(float(scores.get("gesamt", 0)))
            except (TypeError, ValueError):
                score = None
    score_text = f"{score}/100" if score is not None else "—/100"

    decision = str(report.get("entscheidung") or "C").strip().upper() or "C"
    label, severity, _msg = _DECISION_BADGES.get(decision, _DECISION_BADGES["C"])

    big = ParagraphStyle(
        "p_score_big",
        fontName=FONT_BOLD,
        fontSize=34,
        textColor=colors.HexColor(palette.primary),
        leading=38,
        alignment=0,
    )
    label_style = ParagraphStyle(
        "p_score_label",
        fontName=FONT_REGULAR,
        fontSize=9,
        textColor=colors.HexColor(palette.text_muted),
        leading=11,
    )
    headline_style = ParagraphStyle(
        "p_score_head",
        fontName=FONT_BOLD,
        fontSize=14,
        textColor=colors.HexColor(palette.primary_dark),
        leading=18,
    )
    badge_color = (
        palette.pass_color
        if severity == "pass"
        else palette.warn_color
        if severity == "warn"
        else palette.fail_color
    )
    badge_style = ParagraphStyle(
        "p_score_badge",
        fontName=FONT_BOLD,
        fontSize=10,
        textColor=colors.HexColor(badge_color),
        leading=13,
    )
    sub_style = ParagraphStyle(
        "p_score_sub",
        fontName=FONT_REGULAR,
        fontSize=9,
        textColor=colors.HexColor(palette.text),
        leading=12,
    )

    left = Table(
        [
            [Paragraph("GridCheck-Score (0–100)", label_style)],
            [Paragraph(score_text, big)],
            [Paragraph(f"Entscheidung: {decision}", label_style)],
        ],
        colWidths=[doc_width * 0.36],
    )
    left.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(palette.zebra)),
                ("LINEAFTER", (-1, 0), (-1, -1), 1.0, colors.HexColor(palette.primary)),
            ]
        )
    )

    headline_text = _safe(report.get("standort"), default="Projektstandort")
    plz = _safe(report.get("plz"))
    if plz != "—":
        headline_text = f"{headline_text} (PLZ {plz})"
    sub_lines = [_safe(report.get("scope_summary"), default=label)]
    rec_focus = _safe(report.get("recommended_focus"), default="")
    if rec_focus and rec_focus != "—":
        sub_lines.append(rec_focus)

    right_rows: list[list[Any]] = [
        [Paragraph(headline_text, headline_style)],
        [Paragraph(label, badge_style)],
    ]
    for line in sub_lines:
        right_rows.append([Paragraph(line, sub_style)])

    right = Table(right_rows, colWidths=[doc_width * 0.64])
    right.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("BACKGROUND", (0, 0), (-1, -1), colors.white),
            ]
        )
    )

    hero = Table([[left, right]], colWidths=[doc_width * 0.36, doc_width * 0.64])
    hero.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor(palette.border)),
            ]
        )
    )
    return hero


def _projektierer_location_rows(report: dict[str, Any]) -> list[tuple[str, Any]]:
    meta = report.get("location_meta") if isinstance(report.get("location_meta"), dict) else {}
    persp = _persp(report) or {}
    plz = _safe(report.get("plz") or meta.get("plz"))
    standort = _safe(report.get("standort") or meta.get("ort"))
    bundesland = _safe(meta.get("bundesland"))
    lat = meta.get("latitude")
    lon = meta.get("longitude")
    if lat is not None and lon is not None:
        try:
            koord = f"{float(lat):.4f}, {float(lon):.4f}"
        except (TypeError, ValueError):
            koord = "—"
    else:
        koord = "—"
    rec_v = meta.get("recommended_voltage_level")
    if not rec_v:
        nvp = persp.get("nvp_recommendation") if isinstance(persp.get("nvp_recommendation"), dict) else {}
        rec_v = nvp.get("suggested_voltage_level") if isinstance(nvp, dict) else None
    return [
        ("Standort", standort),
        ("PLZ", plz),
        ("Bundesland", bundesland if bundesland != "—" else "—"),
        ("Koordinaten (lat, lon)", koord),
        ("Empfohlene Spannungsebene", _voltage_label(rec_v) if rec_v else "—"),
        ("VNB-Gebiet", _safe(meta.get("vnb_gebiet"))),
        ("Naehester Knoten", _safe(meta.get("nearest_node_hint"))),
    ]


def _projektierer_connection_variants_table(
    palette: StakeholderPalette, report: dict[str, Any], *, doc_width: float
) -> Table:
    raw = report.get("connection_variants")
    rows: list[list[Any]] = []
    if isinstance(raw, list):
        for entry in raw:
            if not isinstance(entry, dict):
                continue
            label = _safe(entry.get("label"))
            voltage = _safe(entry.get("voltage_label"))
            distance = _fmt_num(entry.get("distance_km"), digits=2, suffix=" km")
            confidence = _confidence_label(entry.get("confidence"))
            cost_label, cost_status = _RISK_LEVEL_LABELS.get(
                str(entry.get("cost_risk") or "unknown").lower(),
                _RISK_LEVEL_LABELS["unknown"],
            )
            route_label, route_status = _RISK_LEVEL_LABELS.get(
                str(entry.get("route_risk") or "unknown").lower(),
                _RISK_LEVEL_LABELS["unknown"],
            )
            comment = _safe(entry.get("comment"))
            rows.append(
                [
                    label,
                    voltage,
                    distance,
                    confidence,
                    status_badge_paragraph(palette, cost_status) if cost_status else cost_label,
                    status_badge_paragraph(palette, route_status) if route_status else route_label,
                    comment,
                ]
            )
    if not rows:
        rows.append(
            [
                "—",
                "—",
                "—",
                "—",
                status_badge_paragraph(palette, "OFFEN"),
                status_badge_paragraph(palette, "OFFEN"),
                "1 Kandidat verfuegbar — OSM-/Asset-Pipeline liefert spaeter weitere Varianten.",
            ]
        )
    return alt_table(
        palette,
        ["Variante", "Spannung", "Distanz", "Confidence", "Kostenrisiko", "Trassenrisiko", "Bemerkung"],
        rows,
        col_widths=[
            doc_width * 0.18,
            doc_width * 0.12,
            doc_width * 0.10,
            doc_width * 0.10,
            doc_width * 0.13,
            doc_width * 0.13,
            doc_width * 0.24,
        ],
    )


def _projektierer_risk_table(
    palette: StakeholderPalette, report: dict[str, Any], *, doc_width: float
) -> Table:
    risks = report.get("risks") if isinstance(report.get("risks"), dict) else {}
    rows: list[list[Any]] = []
    keys: list[tuple[str, str]] = [
        ("overall", "Gesamtrisiko"),
        ("grid", "Netzanschluss-Risiko"),
        ("route", "Trassenrisiko"),
        ("cost", "Kostenrisiko"),
        ("timeline", "Terminrisiko"),
        ("data_quality", "Datenqualitaet"),
    ]
    for key, label in keys:
        level = str(risks.get(key) or "unknown").lower()
        de_label, status = _RISK_LEVEL_LABELS.get(level, _RISK_LEVEL_LABELS["unknown"])
        rows.append([label, de_label, status_badge_paragraph(palette, status)])
    return alt_table(
        palette,
        ["Risiko-Dimension", "Stufe", "Status"],
        rows,
        col_widths=[doc_width * 0.45, doc_width * 0.25, doc_width * 0.30],
    )


def _projektierer_cost_band_blocks(
    palette: StakeholderPalette, report: dict[str, Any], *, doc_width: float
) -> list[Any]:
    band = report.get("cost_band") if isinstance(report.get("cost_band"), dict) else None
    if not band:
        return [p(
            "Keine belastbare Kostenbandbreite aus der Engine — bitte Detail-Pruefung anstossen.",
            body_style(palette),
        )]
    blocks: list[Any] = []
    rows: list[list[Any]] = [
        ["Niedrig", _fmt_eur(band.get("niedrig_eur"))],
        ["Basis", _fmt_eur(band.get("basis_eur"))],
        ["Hoch", _fmt_eur(band.get("hoch_eur"))],
    ]
    blocks.append(
        alt_table(
            palette,
            ["Bandbreite", "Wert (EUR)"],
            rows,
            col_widths=[doc_width * 0.40, doc_width * 0.60],
        )
    )
    blocks.append(Spacer(1, 2 * mm))
    items = band.get("items") if isinstance(band.get("items"), list) else []
    if items:
        item_rows: list[list[Any]] = []
        for it in items:
            if not isinstance(it, dict):
                continue
            item_rows.append(
                [
                    _safe(it.get("label")),
                    _fmt_eur(it.get("low")),
                    _fmt_eur(it.get("base")),
                    _fmt_eur(it.get("high")),
                    _confidence_label(it.get("confidence")),
                ]
            )
        if item_rows:
            blocks.append(p_html("<b>Kostenpositionen</b>", body_bold_style(palette)))
            blocks.append(
                alt_table(
                    palette,
                    ["Position", "Niedrig", "Basis", "Hoch", "Confidence"],
                    item_rows,
                    col_widths=[
                        doc_width * 0.34,
                        doc_width * 0.16,
                        doc_width * 0.16,
                        doc_width * 0.16,
                        doc_width * 0.18,
                    ],
                )
            )
            blocks.append(Spacer(1, 2 * mm))
    drivers = band.get("main_drivers") if isinstance(band.get("main_drivers"), list) else []
    if drivers:
        blocks.append(p_html("<b>Hauptkostentreiber</b>", body_bold_style(palette)))
        blocks.extend(bulleted_block(palette, [str(d) for d in drivers]))
    return blocks


def _projektierer_sources_table(
    palette: StakeholderPalette, report: dict[str, Any], *, doc_width: float
) -> Table:
    sources = report.get("sources") if isinstance(report.get("sources"), list) else []
    rows: list[list[Any]] = []
    for entry in sources:
        if not isinstance(entry, dict):
            continue
        retrieved = str(entry.get("retrievedAt") or "").split("T", 1)[0]
        rows.append(
            [
                _safe(entry.get("sourceName")),
                _safe(entry.get("sourceType")),
                retrieved or "—",
                _safe(entry.get("license"), default="—"),
                _confidence_label(entry.get("confidence")),
            ]
        )
    if not rows:
        rows.append(["—", "—", "—", "—", "—"])
    return alt_table(
        palette,
        ["Quelle", "Typ", "Stand", "Lizenz", "Confidence"],
        rows,
        col_widths=[
            doc_width * 0.30,
            doc_width * 0.20,
            doc_width * 0.16,
            doc_width * 0.16,
            doc_width * 0.18,
        ],
    )


def _projektierer_assumptions(report: dict[str, Any]) -> list[tuple[str, str]]:
    persp = _persp(report) or {}
    cos_phi = persp.get("cos_phi") or persp.get("power_factor")
    glz = persp.get("simultaneity_factor") or persp.get("default_simultaneity_factor")
    eeg_class = persp.get("feed_in_management_class")
    q_mode = persp.get("reactive_power_mode") or persp.get("default_reactive_power_mode")

    return [
        ("cos φ (Wirkungsfaktor)", _fmt_num(cos_phi, digits=2, default="0,90")),
        ("Gleichzeitigkeit", _fmt_num(glz, digits=2, default="0,85")),
        ("EEG-Klasse §9 2023", _safe(eeg_class)),
        ("Q-Modus", _safe(q_mode)),
        (
            "Datenqualität",
            _safe(report.get("datenqualitaet_klasse"), default="B"),
        ),
        (
            "N-1 Datengrundlage",
            _safe(persp.get("n1_datengrundlage"), default="planner_assumption"),
        ),
    ]


def _build_projektierer_story(
    palette: StakeholderPalette,
    report: dict[str, Any],
    *,
    doc_width: float,
    report_id: str,
    full_hash: str,
) -> list[Any]:
    """Projektierer-Story (P1/P2/P3-Sektionen).

    Reihenfolge: Score-Hero → Standort/Netzumfeld → Kurz-Cover/Decision →
    Technische KPI → Anschlussvarianten → Risiko-Block → Kostenbandbreite →
    Annahmen/Empfehlungen/Auflagen → Datenquellen → Disclaimer.
    """
    story: list[Any] = []
    body = body_style(palette)

    # 1. Score-Hero (P1) — kompakt analog zu _invest_hero.
    story.append(_projektierer_score_hero(palette, report, doc_width=doc_width))
    story.append(Spacer(1, 4 * mm))

    # 2. Standort / Netzumfeld (P2). Fehlende Felder werden sichtbar als "—" markiert.
    story.extend(
        section(
            palette,
            "Standort & Netzumfeld",
            [kv_table(palette, _projektierer_location_rows(report), doc_width=doc_width, boxed=True)],
        )
    )

    # Cover-Block (Projekt-Eckdaten) bleibt, ist aber jetzt nach Hero+Standort.
    story.extend(_projektierer_cover(palette, report, report_id=report_id, doc_width=doc_width))

    headline, severity, msg = _decision_summary(report)
    story.append(
        summary_box(
            palette,
            headline=headline,
            body_text=msg,
            severity=severity,
            doc_width=doc_width,
        )
    )
    story.append(Spacer(1, 3 * mm))

    # 4. Technische KPI-Tabelle (bleibt).
    story.extend(
        section(
            palette,
            "Technische KPI mit Status und Norm-Bezug",
            [_build_kpi_status_table(palette, report, doc_width=doc_width)],
        )
    )
    story.append(Spacer(1, 3 * mm))

    # 5. Anschlussvarianten (P2) — Pflicht-Sektion, Layout fuer N>=2 Kandidaten.
    story.extend(
        section(
            palette,
            "Anschlussvarianten",
            [_projektierer_connection_variants_table(palette, report, doc_width=doc_width)],
        )
    )
    story.append(Spacer(1, 3 * mm))

    # 6. Risiko-Block (P1) — kompakte Status-Tabelle.
    story.extend(
        section(
            palette,
            "Risiko-Block (Gesamt / Netz / Trasse / Kosten / Termin / Datenqualitaet)",
            [_projektierer_risk_table(palette, report, doc_width=doc_width)],
        )
    )
    story.append(Spacer(1, 3 * mm))

    # 7. Kostenbandbreite (P1) — Niedrig/Basis/Hoch + costItems + Hauptkostentreiber.
    story.extend(
        section(
            palette,
            "Kostenbandbreite (Niedrig / Basis / Hoch)",
            _projektierer_cost_band_blocks(palette, report, doc_width=doc_width),
        )
    )
    story.append(Spacer(1, 3 * mm))

    # Annahmen + Anlagenkontext + EEG + Zeitplan + NVP (bleibt strukturell, aber spaeter).
    story.extend(
        section(
            palette,
            "Annahmen & Confidence",
            [
                kv_table(palette, _projektierer_assumptions(report), doc_width=doc_width, boxed=True),
            ],
        )
    )

    persp = _persp(report) or {}
    plant_context = [
        ("Anlage", _plant_label(report)),
        ("AC-Leistung", _fmt_num(persp.get("ac_kw"), digits=0, suffix=" kW")),
        ("DC-Leistung", _fmt_num(persp.get("dc_kwp"), digits=0, suffix=" kWp")),
        ("Screening-Leistung", _fmt_num(persp.get("screening_power_kw"), digits=0, suffix=" kW")),
        ("Profilhinweis", _safe(persp.get("feed_in_profile_note"))),
    ]
    story.extend(
        section(
            palette,
            "Anlagen- / Plant-Context",
            [kv_table(palette, plant_context, doc_width=doc_width, boxed=True)],
        )
    )

    eeg_items = list(report.get("eeg_checklist") or [])
    story.extend(
        section(
            palette,
            "§9 EEG 2023 — Einspeisemanagement-Checkliste",
            bulleted_block(palette, eeg_items, empty_label="Keine EEG-Hinweise."),
        )
    )

    timeline = list(report.get("process_timeline") or [])
    bkz = _safe(report.get("bkz_hint"), default="")
    story.extend(
        section(
            palette,
            "Zeitplan (heuristisch) & BKZ-Indikation",
            [
                *bulleted_block(palette, timeline, empty_label="Keine Zeitplan-Daten."),
                Spacer(1, 2 * mm),
                p_html(
                    f"<b>BKZ-Hinweis (§25 NAV, qualitativ):</b> {bkz or '—'}",
                    body,
                ),
            ],
        )
    )

    nvp = (persp.get("nvp_recommendation") if isinstance(persp.get("nvp_recommendation"), dict) else {}) or {}
    nvp_rows: list[tuple[str, Any]] = []
    if nvp.get("suggested_voltage_level"):
        nvp_rows.append(
            ("Empfohlene Spannungsebene", _voltage_label(nvp.get("suggested_voltage_level")))
        )
    if nvp.get("nearest_node_hint"):
        nvp_rows.append(("Nähester Knoten", _safe(nvp.get("nearest_node_hint"))))
    if nvp.get("disclaimer"):
        nvp_rows.append(("Vorbehalt", _safe(nvp.get("disclaimer"))))
    if not nvp_rows:
        nvp_rows = [("Empfehlung", "Keine NVP-Empfehlung aus Engine.")]
    story.extend(
        section(
            palette,
            "NVP-Empfehlung",
            [kv_table(palette, nvp_rows, doc_width=doc_width, boxed=True)],
        )
    )

    # 8. Empfehlungen + Auflagen (bleibt).
    story.extend(
        section(
            palette,
            "Maßnahmen / Auflagen",
            [
                p_html("<b>Empfohlene Maßnahmen</b>", body_bold_style(palette)),
                *bulleted_block(
                    palette,
                    list(report.get("empfohlene_massnahmen") or []),
                    empty_label="Keine zusätzlichen Maßnahmen.",
                ),
                Spacer(1, 2 * mm),
                p_html("<b>Auflagen / Bedingungen</b>", body_bold_style(palette)),
                *bulleted_block(
                    palette,
                    list(report.get("auflagen") or []),
                    empty_label="Keine Auflagen gemeldet.",
                ),
            ],
        )
    )

    norms = list(report.get("normen_snapshot") or [])
    if norms:
        rows: list[list[Any]] = []
        for entry in norms:
            if isinstance(entry, dict):
                rows.append(
                    [
                        _safe(entry.get("norm_id")),
                        _safe(entry.get("stand")),
                        _safe(entry.get("kategorie")),
                    ]
                )
        story.extend(
            section(
                palette,
                "Norm-Referenzen",
                [
                    alt_table(
                        palette,
                        ["Norm-ID", "Stand", "Kategorie"],
                        rows,
                        col_widths=[doc_width * 0.45, doc_width * 0.25, doc_width * 0.30],
                    )
                ],
            )
        )
    else:
        story.extend(
            section(
                palette,
                "Norm-Referenzen",
                bulleted_block(palette, _PROJEKTIERER_NORMS_FALLBACK),
            )
        )

    # 9. Datenquellen-Block (P2). Tabelle mit Quelle/Typ/Stand/Lizenz/Confidence.
    story.extend(
        section(
            palette,
            "Datenquellen",
            [_projektierer_sources_table(palette, report, doc_width=doc_width)],
        )
    )

    # 10. Disclaimer + Audit-Footer (bleibt).
    story.append(Spacer(1, 3 * mm))
    story.append(_disclaimer_paragraph(palette))
    return story


# ============================================================================
# VNB story
# ============================================================================
def _vnb_antrag_identification(report: dict[str, Any]) -> list[tuple[str, Any]]:
    plz = _safe(report.get("plz"))
    standort = _safe(report.get("standort"))
    ort_zeile = f"{standort} (PLZ {plz})" if plz != "—" else standort
    return [
        ("Antragsteller / verantwortliche Stelle", _safe(report.get("antragsteller"), default="—")),
        ("Standort", ort_zeile),
        ("Anlagentyp", _plant_label(report)),
        ("Geplante Leistung", _fmt_num(report.get("leistung_mw"), digits=3, suffix=" MW")),
        ("Spannungsebene", _voltage_label(report.get("spannungsebene"))),
        ("Anschlussart", _connection_label(report.get("anschlussart"))),
        ("Datengrundlage", _safe(report.get("n1_datengrundlage"), default="planner_assumption")),
        (
            "Datum",
            _safe(report.get("report_generated_at")).split("T", 1)[0],
        ),
    ]


def _vnb_technical_pruefung_table(
    palette: StakeholderPalette, report: dict[str, Any], *, doc_width: float
) -> Table:
    headers = ["Kenngröße", "Vorprüfwert", "Norm", "Screening", "VNB-Prüfung"]
    rows: list[list[Any]] = []
    table_data = list(report.get("technical_review_table") or [])

    norm_map = {
        "spannungsfall": "VDE-AR-N 4110 §5",
        "kurzschluss": "DIN EN 60909",
        "thermik": "VDE-AR-N 4110 §6",
        "spannung": "VDE-AR-N 4110 §5",
        "leitung": "DIN VDE 0276",
        "trasse": "DIN VDE 0276",
        "n-1-screening": "VDE-AR-N 4110 §10",
        "n-1": "VDE-AR-N 4110 §10",
    }

    for entry in table_data:
        if not isinstance(entry, dict):
            continue
        label = _safe(entry.get("kenngroesse") or entry.get("label"))
        screening_val = _safe(entry.get("screening") or entry.get("wert"))
        hinweis = _safe(entry.get("hinweis"), default="Screening")
        norm = ""
        for key, val in norm_map.items():
            if key in label.lower():
                norm = val
                break
        if not norm:
            norm = "VDE-AR-N 4110"
        rows.append(
            [
                label,
                screening_val,
                norm,
                status_badge_paragraph(palette, hinweis),
                "☐ ____________________",
            ]
        )
    if not rows:
        rows = [["Keine Vorprüfdaten verfügbar.", "—", "—", "—", "☐"]]
    return alt_table(
        palette,
        headers,
        rows,
        col_widths=[
            doc_width * 0.22,
            doc_width * 0.20,
            doc_width * 0.18,
            doc_width * 0.18,
            doc_width * 0.22,
        ],
    )


def _vnb_checklist_table(palette: StakeholderPalette, *, doc_width: float) -> Table:
    headers = ["#", "VNB-Prüfpunkt (10 Punkte)", "Geprüft", "Bemerkung"]
    rows: list[list[Any]] = []
    for i, label in enumerate(_VNB_CHECKLIST_10, start=1):
        rows.append([f"{i:>2}.", label, "☐ ja  ☐ nein", "_____________________"])
    return alt_table(
        palette,
        headers,
        rows,
        col_widths=[
            doc_width * 0.06,
            doc_width * 0.52,
            doc_width * 0.16,
            doc_width * 0.26,
        ],
    )


def _build_vnb_story(
    palette: StakeholderPalette,
    report: dict[str, Any],
    *,
    doc_width: float,
    report_id: str,
    full_hash: str,
) -> list[Any]:
    story: list[Any] = []
    body = body_style(palette)

    headline, severity, msg = _decision_summary(report)
    story.append(
        summary_box(
            palette,
            headline=f"Vorprüfung: {headline}",
            body_text=msg,
            severity=severity,
            doc_width=doc_width,
        )
    )
    story.append(Spacer(1, 3 * mm))

    story.extend(
        section(
            palette,
            "Antragsidentifikation",
            [
                kv_table(
                    palette,
                    _vnb_antrag_identification(report),
                    doc_width=doc_width,
                    boxed=True,
                )
            ],
        )
    )

    story.extend(
        section(
            palette,
            "Technische Antragsdaten (Screening)",
            [_vnb_technical_pruefung_table(palette, report, doc_width=doc_width)],
        )
    )
    story.append(Spacer(1, 2 * mm))

    story.extend(
        section(
            palette,
            "VNB-Prüfcheckliste (10 Punkte)",
            [_vnb_checklist_table(palette, doc_width=doc_width)],
        )
    )

    story.extend(
        section(
            palette,
            "Status- / Prozesssicht",
            bulleted_block(
                palette,
                list(report.get("process_view") or []),
                empty_label="Keine Prozesssicht hinterlegt.",
            ),
        )
    )

    story.append(PageBreak())

    story.extend(
        section(
            palette,
            "Hinweis zur VNB-Prüfung",
            [p(_safe(report.get("netzbetreiber_checkliste_hinweis")), body)],
        )
    )

    story.extend(
        section(
            palette,
            "Entscheidungsblock (VNB)",
            [
                decision_picks(
                    palette,
                    [
                        "Vorgang positiv — Standardverfahren",
                        "Positiv mit Auflagen",
                        "Vorgang abgelehnt / Nachreichung erforderlich",
                    ],
                    doc_width=doc_width,
                ),
            ],
        )
    )

    story.extend(
        section(
            palette,
            "Auflagen / Bedingungen (8 Linien)",
            [lined_field(palette, lines=8, doc_width=doc_width)],
        )
    )

    story.append(Spacer(1, 4 * mm))
    story.extend(
        section(
            palette,
            "Freigabe / Unterschriften",
            [
                signature_block(
                    palette,
                    [
                        {
                            "label": "Antragsteller / Projektierer",
                            "placeholder": "Datum, Ort, Name",
                            "hint": "Unterschrift",
                        },
                        {
                            "label": "VNB-Sachbearbeitung",
                            "placeholder": "Datum, Ort, Name",
                            "hint": "Unterschrift / Stempel",
                        },
                        {
                            "label": "Freizeichnung / Leitung",
                            "placeholder": "Datum, Ort, Name",
                            "hint": "Unterschrift / Stempel",
                        },
                    ],
                    doc_width=doc_width,
                )
            ],
        )
    )

    story.append(Spacer(1, 4 * mm))
    story.append(_disclaimer_paragraph(palette))
    return story


# ============================================================================
# Invest story
# ============================================================================
def _invest_score(report: dict[str, Any]) -> int | None:
    kpi = report.get("kpi_summary")
    if isinstance(kpi, list):
        for line in kpi:
            if isinstance(line, str) and "Score" in line:
                # parse first integer found
                digits = "".join(ch if ch.isdigit() else " " for ch in line).split()
                if digits:
                    try:
                        return int(digits[0])
                    except ValueError:
                        continue
    scores = report.get("scores")
    if isinstance(scores, dict):
        try:
            return int(float(scores.get("gesamt", 0)))
        except (TypeError, ValueError):
            return None
    return None


def _invest_cost_estimate(report: dict[str, Any]) -> tuple[str, str]:
    cost_band = report.get("cost_band") if isinstance(report.get("cost_band"), dict) else None
    if cost_band:
        basis = cost_band.get("basis_eur")
        low = cost_band.get("niedrig_eur") or basis
        high = cost_band.get("hoch_eur") or basis
        return (_fmt_eur(basis), f"{_fmt_eur(low)} – {_fmt_eur(high)}")
    kosten = report.get("kosten_indikation")
    if isinstance(kosten, dict):
        basis = kosten.get("investition_gesamt_eur") or kosten.get("band_basis_eur")
        return (_fmt_eur(basis), "Bandbreite n/a")
    return ("—", "Kostenband fehlt")


def _invest_timeframe(report: dict[str, Any]) -> str:
    timeline = report.get("process_timeline")
    if isinstance(timeline, list):
        for line in timeline:
            if isinstance(line, str) and "Wochen" in line:
                return line
    return "8–16 Wochen (heuristisch)"


def _invest_hero(
    palette: StakeholderPalette, report: dict[str, Any], *, doc_width: float
) -> Table:
    score = _invest_score(report)
    score_text = f"{score}/100" if score is not None else "—"
    decision = str(report.get("entscheidung") or "C").strip().upper() or "C"
    decision_label, severity, _msg = _DECISION_BADGES.get(
        decision, _DECISION_BADGES["C"]
    )
    big = ParagraphStyle(
        "invest_score",
        fontName=FONT_BOLD,
        fontSize=44,
        textColor=colors.HexColor(palette.primary),
        leading=48,
        alignment=0,
    )
    label = ParagraphStyle(
        "invest_label",
        fontName=FONT_REGULAR,
        fontSize=10,
        textColor=colors.HexColor(palette.text_muted),
        leading=12,
        alignment=0,
    )
    headline = ParagraphStyle(
        "invest_head",
        fontName=FONT_BOLD,
        fontSize=18,
        textColor=colors.HexColor(palette.primary_dark),
        leading=22,
    )
    rec = ParagraphStyle(
        "invest_rec",
        fontName=FONT_REGULAR,
        fontSize=10,
        textColor=colors.HexColor(palette.text),
        leading=14,
    )
    badge_color = (
        palette.pass_color
        if severity == "pass"
        else palette.warn_color
        if severity == "warn"
        else palette.fail_color
    )
    badge = ParagraphStyle(
        "invest_badge",
        fontName=FONT_BOLD,
        fontSize=11,
        textColor=colors.HexColor(badge_color),
        leading=14,
    )

    left = Table(
        [
            [Paragraph("GridCheck-Score", label)],
            [Paragraph(score_text, big)],
            [Paragraph(f"Entscheidung: {decision}", label)],
        ],
        colWidths=[doc_width * 0.42],
    )
    left.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 14),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(palette.zebra)),
                ("LINEAFTER", (-1, 0), (-1, -1), 1.0, colors.HexColor(palette.primary)),
            ]
        )
    )

    headline_text = _safe(report.get("standort"), default="Projektportfolio")
    rec_text = _safe(report.get("recommended_focus"), default=_safe(report.get("scope_summary")))

    right = Table(
        [
            [Paragraph(headline_text, headline)],
            [Paragraph(decision_label, badge)],
            [Paragraph(rec_text, rec)],
        ],
        colWidths=[doc_width * 0.58],
    )
    right.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 14),
                ("RIGHTPADDING", (0, 0), (-1, -1), 14),
                ("TOPPADDING", (0, 0), (-1, -1), 12),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
                ("BACKGROUND", (0, 0), (-1, -1), colors.white),
            ]
        )
    )

    hero = Table([[left, right]], colWidths=[doc_width * 0.42, doc_width * 0.58])
    hero.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor(palette.border)),
            ]
        )
    )
    return hero


def _invest_kpi_cards(
    palette: StakeholderPalette, report: dict[str, Any], *, doc_width: float
) -> Table:
    basis, band = _invest_cost_estimate(report)
    score = _invest_score(report)
    leistung_mw = report.get("leistung_mw")
    persp = _persp(report) or {}
    ac_kw = persp.get("ac_kw") or (
        float(leistung_mw) * 1000.0 if isinstance(leistung_mw, (int, float)) else None
    )

    cards = [
        ("Anschlussleistung", _fmt_num(ac_kw, digits=0, suffix=" kW"), _voltage_label(report.get("spannungsebene"))),
        ("GridCheck-Score", f"{score}/100" if score is not None else "—", "Confidence A–D"),
        ("Kosten-Schätzung", basis, band),
        ("Zeitrahmen (heuristisch)", _invest_timeframe(report), "VNB-abhängig"),
    ]
    return kpi_strip(palette, cards, doc_width=doc_width)


def _invest_chancen_risiken(
    palette: StakeholderPalette, report: dict[str, Any], *, doc_width: float
) -> Table:
    risks_raw = list(report.get("risk_overview") or [])
    chances: list[str] = []
    risks_list: list[str] = []
    for item in risks_raw:
        if not isinstance(item, dict):
            continue
        label = _safe(item.get("label"))
        detail = _safe(item.get("detail"))
        status = str(item.get("status") or "").lower()
        rendered = f"{label}: {detail}" if detail != "—" else label
        if status in {"hoch", "high", "fail", "rot"}:
            risks_list.append(rendered)
        elif status in {"niedrig", "low", "pass", "gruen", "grün"}:
            chances.append(rendered)
        else:
            risks_list.append(rendered)

    portfolio = list(report.get("portfolio_view") or [])
    for line in portfolio:
        if "kritisch" in str(line).lower():
            risks_list.append(str(line))
        else:
            chances.append(str(line))

    if not chances:
        chances = ["Score und Stakeholder-Fit liegen im akzeptablen Band — DD kann fortgesetzt werden."]
    if not risks_list:
        risks_list = ["Aktuell keine harten Risikoflags — Standardvorbehalte des Screenings beachten."]

    body = body_style(palette)
    head_left = ParagraphStyle(
        "chance_head",
        fontName=FONT_BOLD,
        fontSize=11,
        textColor=colors.HexColor(palette.pass_color),
        leading=14,
    )
    head_right = ParagraphStyle(
        "risk_head",
        fontName=FONT_BOLD,
        fontSize=11,
        textColor=colors.HexColor(palette.fail_color),
        leading=14,
    )

    left_rows: list[list[Any]] = [[Paragraph("Chancen", head_left)]]
    for line in chances:
        left_rows.append([p_html(f"+&nbsp; {line}", body)])
    right_rows: list[list[Any]] = [[Paragraph("Risiken / Watchpoints", head_right)]]
    for line in risks_list:
        right_rows.append([p_html(f"!&nbsp; {line}", body)])

    left = Table(left_rows, colWidths=[(doc_width - 6 * mm) / 2])
    right = Table(right_rows, colWidths=[(doc_width - 6 * mm) / 2])
    for sub, accent in ((left, palette.pass_color), (right, palette.fail_color)):
        sub.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(palette.zebra)),
                    ("LINEBELOW", (0, 0), (-1, 0), 1.0, colors.HexColor(accent)),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor(palette.border)),
                ]
            )
        )

    return Table([[left, right]], colWidths=[doc_width / 2, doc_width / 2])


def _invest_eckdaten(report: dict[str, Any]) -> list[tuple[str, Any]]:
    return [
        ("Standort", _safe(report.get("standort"))),
        ("PLZ", _safe(report.get("plz"))),
        ("Anlagentyp", _plant_label(report)),
        ("Leistung", _fmt_num(report.get("leistung_mw"), digits=3, suffix=" MW")),
        ("Spannungsebene", _voltage_label(report.get("spannungsebene"))),
        ("Anschlussart", _connection_label(report.get("anschlussart"))),
        ("N-1-Klasse", _safe(report.get("n1_status"))),
        (
            "Datengrundlage",
            _safe(report.get("n1_datengrundlage"), default="planner_assumption"),
        ),
    ]


def _build_invest_story(
    palette: StakeholderPalette,
    report: dict[str, Any],
    *,
    doc_width: float,
    report_id: str,
    full_hash: str,
) -> list[Any]:
    story: list[Any] = []
    body = body_style(palette)

    story.append(_invest_hero(palette, report, doc_width=doc_width))
    story.append(Spacer(1, 4 * mm))

    story.extend(
        section(
            palette,
            "Investitions-KPIs",
            [_invest_kpi_cards(palette, report, doc_width=doc_width)],
        )
    )
    story.append(Spacer(1, 3 * mm))

    story.extend(
        section(
            palette,
            "Chancen & Risiken (kuratiert)",
            [_invest_chancen_risiken(palette, report, doc_width=doc_width)],
        )
    )

    story.extend(
        section(
            palette,
            "Eckdaten",
            [kv_table(palette, _invest_eckdaten(report), doc_width=doc_width, boxed=True)],
        )
    )

    cost_band = report.get("cost_band") if isinstance(report.get("cost_band"), dict) else None
    if cost_band:
        rows: list[list[Any]] = []
        for key, label in (
            ("niedrig_eur", "Niedrig"),
            ("basis_eur", "Basis"),
            ("hoch_eur", "Hoch"),
            ("confidence_pct", "Confidence"),
            ("source", "Quelle"),
        ):
            value = cost_band.get(key)
            if value is None:
                continue
            if key.endswith("_eur"):
                rows.append([label, _fmt_eur(value), "EUR"])
            elif key == "confidence_pct":
                rows.append([label, f"{value} %", "Schätzbandbreite"])
            else:
                rows.append([label, _safe(value), ""])
        story.extend(
            section(
                palette,
                "Kostenbandbreite (Detail)",
                [
                    alt_table(
                        palette,
                        ["Position", "Wert", "Anmerkung"],
                        rows,
                        col_widths=[doc_width * 0.30, doc_width * 0.35, doc_width * 0.35],
                    )
                ],
            )
        )

    next_steps_raw = list(report.get("empfohlene_massnahmen") or []) + list(
        report.get("kpi_summary") or []
    )[:1]
    next_steps = _ensure_three_lines(next_steps_raw, minimum=3)[:6]
    story.extend(
        section(
            palette,
            "Nächste Schritte",
            bulleted_block(palette, next_steps, empty_label="—"),
        )
    )

    story.append(Spacer(1, 3 * mm))
    story.append(_disclaimer_paragraph(palette))

    boundary = _safe(report.get("visibility_boundary_note"), default="")
    if boundary and boundary != "—":
        story.append(Spacer(1, 2 * mm))
        story.append(p(boundary, muted_style(palette)))
    return story


# ============================================================================
# Public entry point
# ============================================================================
def build_stakeholder_report_pdf(report: dict[str, Any]) -> bytes:
    """Render a stakeholder-report dict to a high-quality PDF byte string.

    The function picks one of three layouts based on ``report['report_type']``
    (``projektierer``/``vnb``/``invest``) and stamps a deterministic SHA-256
    footer hash plus stable Report-ID on every page.
    """
    if not isinstance(report, dict):
        raise TypeError("build_stakeholder_report_pdf requires a dict report payload")

    rt = str(report.get("report_type") or "projektierer").strip().lower()
    if rt not in {"projektierer", "vnb", "invest"}:
        rt = "projektierer"

    palette = palette_for(rt)
    full_hash = compute_footer_hash(report)
    short_hash = _short_hash(full_hash, 12)
    report_id = _report_id(report, full_hash)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        topMargin=14 * mm,
        bottomMargin=22 * mm,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        title=f"GridCheck — {_STAKEHOLDER_TITLES.get(rt, 'Stakeholder-Report')}",
        author="GridCheck / Adecarb",
    )
    doc_width = doc.width

    story: list[Any] = []

    story.append(
        brand_header(
            palette,
            title=_STAKEHOLDER_TITLES.get(rt, "Stakeholder-Report"),
            subtitle=(
                f"{_STAKEHOLDER_SUBTITLES.get(rt, '')} · Report-ID {report_id} · "
                f"Stand {_safe(report.get('report_generated_at')).split('T', 1)[0]}"
            ),
            doc_width=doc_width,
        )
    )
    story.append(Spacer(1, 4 * mm))
    story.append(
        _build_meta_strip(
            palette,
            report,
            report_id=report_id,
            full_hash=full_hash,
            doc_width=doc_width,
        )
    )
    story.append(Spacer(1, 4 * mm))

    if rt == "vnb":
        story.extend(
            _build_vnb_story(
                palette,
                report,
                doc_width=doc_width,
                report_id=report_id,
                full_hash=full_hash,
            )
        )
    elif rt == "invest":
        story.extend(
            _build_invest_story(
                palette,
                report,
                doc_width=doc_width,
                report_id=report_id,
                full_hash=full_hash,
            )
        )
    else:
        story.extend(
            _build_projektierer_story(
                palette,
                report,
                doc_width=doc_width,
                report_id=report_id,
                full_hash=full_hash,
            )
        )

    footer_cb = make_footer_callback(
        palette,
        short_hash=short_hash,
        disclaimer=_DISCLAIMER_LINE,
    )

    def _on_page(canvas, doc_inner) -> None:
        footer_cb(canvas, doc_inner)
        # add "Seite x / y" with both numbers in the bottom-right
        canvas.saveState()
        breite, _h = doc_inner.pagesize
        canvas.setFont(FONT_REGULAR, 7.5)
        canvas.setFillColor(colors.HexColor(palette.text_muted))
        canvas.drawRightString(
            breite - 15 * mm,
            10 * mm - 3.5 * mm,
            f"Report-ID {report_id}",
        )
        canvas.restoreState()

    doc.build(story, onFirstPage=_on_page, onLaterPages=_on_page)
    return buf.getvalue()
