"""
ReportLab PDFs for stakeholder HTML report dicts (VNB, Invest, Projektierer).
Mirrors mandatory blocks from the Jinja HTML templates without WeasyPrint.
"""
from __future__ import annotations

import io
from typing import Any
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from core import branding as B

_BANNER_SUBTITLE = {
    "vnb": "Netzbetreiber (VNB)",
    "invest": "Investor",
    "projektierer": "Projektierer",
}


def _p(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(escape(str(text)), style)


_SECTION_TITLE_STYLE = ParagraphStyle(
    "stakeholder_section",
    fontName=B.FONT_BOLD,
    fontSize=12,
    textColor=colors.HexColor(B.PETROL),
    spaceBefore=8,
    spaceAfter=4,
    leading=14,
)


def _body_style() -> ParagraphStyle:
    return ParagraphStyle(
        "stakeholder_body",
        fontName=B.FONT_REGULAR,
        fontSize=10,
        textColor=colors.HexColor(B.TEXT),
        leading=13,
    )


def _muted_style() -> ParagraphStyle:
    return ParagraphStyle(
        "stakeholder_muted",
        fontName=B.FONT_REGULAR,
        fontSize=9,
        textColor=colors.HexColor(B.TEXT_MUTED),
        leading=11,
    )


def _bool_geht(report: dict[str, Any]) -> str:
    if report.get("geht"):
        return "Geht"
    return "Geht-nicht"


def _bulleted_block(story: list[Any], style: ParagraphStyle, items: list[str], empty_label: str) -> None:
    if items:
        for line in items:
            story.append(_p(f"• {line}", style))
    else:
        story.append(_p(empty_label, style))


def _append_table(
    story: list[Any],
    doc: SimpleDocTemplate,
    headers: list[str],
    rows: list[list[str]],
    *,
    col_widths: list[float] | None = None,
) -> None:
    if not rows:
        return
    tbl_data = [headers, *rows]
    tw = doc.width
    if col_widths is None:
        col_widths = [tw / len(headers)] * len(headers)
    t = Table(tbl_data, colWidths=col_widths)
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(B.GRAU_ZEBRA)),
                ("FONTNAME", (0, 0), (-1, 0), B.FONT_BOLD),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor(B.GRAU_LINIE)),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(t)


def _auflagen_empty_label(report: dict[str, Any]) -> str:
    if report.get("empfohlene_massnahmen"):
        return (
            "Keine separaten Auflagen aus Warnungen – "
            "Bedingungen und nächste Schritte siehe «Empfohlene Maßnahmen»."
        )
    return "Keine Auflagen gemeldet."


def build_stakeholder_report_pdf(report: dict[str, Any]) -> bytes:
    """Map a stakeholder report dict (from build_*_report) to a PDF byte string."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        topMargin=15 * mm,
        bottomMargin=22 * mm,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        title="Adecarb GridCheck - Stakeholder-Kurzreport",
        author="Adecarb",
    )
    rt = str(report.get("report_type", "stakeholder"))
    unter = _BANNER_SUBTITLE.get(rt, "Stakeholder")
    story: list[Any] = []
    story.append(B.build_header_banner(doc.width / mm, untertitel=f"{unter} Kurzreport"))
    story.append(Spacer(1, 6 * mm))

    body = _body_style()
    muted = _muted_style()

    story.append(
        _p(
            f"Version {report.get('report_version', '')} | Normstand {report.get('app_normstand', '')}",
            muted,
        )
    )
    story.append(_p(f"Engine-Revision: {report.get('engine_revision_hash') or 'n/a'}", muted))
    if report.get("report_revision_number") or report.get("report_revision_uuid"):
        story.append(
            _p(
                "Report-Revision: "
                f"#{report.get('report_revision_number') or 'n/a'} | "
                f"UUID: {report.get('report_revision_uuid') or 'n/a'}",
                muted,
            )
        )
    if report.get("report_generated_at") or report.get("audit_hash"):
        story.append(
            _p(
                f"Erzeugt: {report.get('report_generated_at') or 'n/a'} | Audit-Hash: {report.get('audit_hash') or 'n/a'}",
                muted,
            )
        )
    if report.get("report_verify_path"):
        story.append(_p(f"Verify-Pfad: {report.get('report_verify_path')}", muted))
    if report.get("source_analysis_run_id") or report.get("source_revision_hash"):
        story.append(
            _p(
                "Quelle: "
                f"Analysis-Run {report.get('source_analysis_run_id') or 'n/a'} | "
                f"Source-Revision: {report.get('source_revision_hash') or 'n/a'}",
                muted,
            )
        )
    if report.get("source_request_checksum") or report.get("source_result_checksum"):
        story.append(
            _p(
                "Source-Checksums: "
                f"Request {report.get('source_request_checksum') or 'n/a'} | "
                f"Result {report.get('source_result_checksum') or 'n/a'}",
                muted,
            )
        )
    story.append(
        _p(
            "Paket: "
            f"{report.get('offer_id') or 'manual'} | "
            f"Package-Scope: {report.get('package_scope_label') or report.get('package_scope') or 'n/a'} | "
            f"Report-Scope: {report.get('report_scope_label') or report.get('report_scope') or 'n/a'}",
            muted,
        )
    )
    if report.get("scope_summary"):
        story.append(_p(str(report.get("scope_summary")), muted))
    story.append(Spacer(1, 3 * mm))

    story.append(_p("Projektkern", _SECTION_TITLE_STYLE))
    plz = report.get("plz")
    plz_s = str(plz) if plz not in (None, "") else "n/a"
    leistung = float(report.get("leistung_mw", 0.0))
    story.append(
        _p(
            f"Standort: {report.get('standort', '')} (PLZ: {plz_s})",
            body,
        )
    )
    story.append(_p(f"Leistung: {leistung:.3f} MW", body))
    story.append(_p(f"Spannungsebene: {report.get('spannungsebene', '')}", body))
    story.append(_p(f"Anschlussart: {report.get('anschlussart', '')}", body))
    story.append(
        _p(
            "Einschätzung Screening: "
            f"{_bool_geht(report)} ({report.get('entscheidung', '')})",
            body,
        )
    )

    if rt == "projektierer":
        warnungen = list(report.get("warnungen") or [])
        if warnungen:
            story.append(_p("Warnungen", _SECTION_TITLE_STYLE))
            _bulleted_block(story, body, warnungen, "Keine Warnungen.")

        tech_table = list(report.get("technical_details_table") or [])
        if tech_table:
            story.append(_p("Technische Kenngrößen (Screening)", _SECTION_TITLE_STYLE))
            _append_table(
                story,
                doc,
                ["Kenngröße", "Wert", "Hinweis"],
                [
                    [str(r.get("kenngroesse", "")), str(r.get("wert", "")), str(r.get("hinweis", ""))]
                    for r in tech_table
                    if isinstance(r, dict)
                ],
            )
            story.append(Spacer(1, 3 * mm))

        timeline = list(report.get("process_timeline") or [])
        if timeline:
            story.append(_p("Zeitplan (heuristisch)", _SECTION_TITLE_STYLE))
            _bulleted_block(story, body, timeline, "")

        bkz = report.get("bkz_hint")
        if bkz:
            story.append(_p("BKZ-Hinweis (§25 NAV, qualitativ)", _SECTION_TITLE_STYLE))
            story.append(_p(str(bkz), body))

        eeg_items = list(report.get("eeg_checklist") or [])
        if eeg_items:
            story.append(_p("EEG §9 — Einspeisemanagement-Checkliste", _SECTION_TITLE_STYLE))
            _bulleted_block(story, body, eeg_items, "")

        reactive_items = list(report.get("reactive_checklist") or [])
        if reactive_items:
            story.append(_p("Blindleistung — Screening-Checkliste", _SECTION_TITLE_STYLE))
            _bulleted_block(story, body, reactive_items, "")

    if rt == "vnb" and report.get("netzbetreiber_checkliste_hinweis"):
        story.append(_p("Checkliste-Netzbetreiber (Hinweis)", _SECTION_TITLE_STYLE))
        story.append(_p(str(report["netzbetreiber_checkliste_hinweis"]), body))
        request_review = list(report.get("request_review") or [])
        if request_review:
            story.append(_p("Strukturierte Anfragepruefung", _SECTION_TITLE_STYLE))
            for item in request_review:
                if isinstance(item, dict):
                    story.append(
                        _p(
                            f"{item.get('label', '')} [{item.get('status', '')}]: {item.get('detail', '')}",
                            body,
                        )
                    )
        technical_precheck = list(report.get("technical_precheck") or [])
        if technical_precheck:
            story.append(_p("Technische Vorpruefung", _SECTION_TITLE_STYLE))
            for item in technical_precheck:
                if isinstance(item, dict):
                    story.append(
                        _p(
                            f"{item.get('label', '')} [{item.get('status', '')}]: {item.get('detail', '')}",
                            body,
                        )
                    )
        review_table = list(report.get("technical_review_table") or [])
        if review_table:
            story.append(_p("Technische Kenngrößen — VNB-Prüfmatrix", _SECTION_TITLE_STYLE))
            _append_table(
                story,
                doc,
                ["Kenngröße", "Screening", "VNB-Prüfung"],
                [
                    [
                        str(r.get("kenngroesse", "")),
                        str(r.get("screening", "")),
                        str(r.get("vnb_pruefung", "")),
                    ]
                    for r in review_table
                    if isinstance(r, dict)
                ],
                col_widths=[doc.width * 0.32, doc.width * 0.28, doc.width * 0.4],
            )
            story.append(Spacer(1, 3 * mm))
        vnb_timeline = list(report.get("process_timeline") or [])
        if vnb_timeline:
            story.append(_p("Prozess-Zeitplan (Referenz)", _SECTION_TITLE_STYLE))
            _bulleted_block(story, body, vnb_timeline, "")

    story.append(_p("N-1 Status", _SECTION_TITLE_STYLE))
    story.append(_p(str(report.get("n1_status", "")), body))
    story.append(_p(str(report.get("n1_detail", "")), body))

    v2_lines = list(report.get("projektierer_v2_lines") or [])
    if rt == "projektierer" and v2_lines:
        story.append(_p("Projektierer-Vorplanung (grid_calculation_v2)", _SECTION_TITLE_STYLE))
        if report.get("grid_calculation_version"):
            story.append(_p(f"Version: {report.get('grid_calculation_version')}", muted))
        _bulleted_block(story, body, v2_lines, "Keine v2-Details.")

    if rt == "vnb" and report.get("process_view"):
        story.append(_p("Status- / Prozesssicht", _SECTION_TITLE_STYLE))
        _bulleted_block(story, body, list(report.get("process_view") or []), "")

    story.append(_p("Auflagen", _SECTION_TITLE_STYLE))
    _bulleted_block(
        story,
        body,
        list(report.get("auflagen") or []),
        _auflagen_empty_label(report),
    )

    story.append(_p("Empfohlene Maßnahmen", _SECTION_TITLE_STYLE))
    _bulleted_block(
        story,
        body,
        list(report.get("empfohlene_massnahmen") or []),
        "Keine Maßnahmen gemeldet.",
    )
    if rt == "vnb" and report.get("technical_requirements"):
        story.append(_p("Technische Auflagen / Nachreichungen", _SECTION_TITLE_STYLE))
        _bulleted_block(
            story,
            body,
            list(report.get("technical_requirements") or []),
            "",
        )

    extra_blocks = [
        ("Projektprofil", report.get("projektprofil_summary")),
        ("Speicher / Flexibilität", report.get("speicher_summary")),
        ("Umwelt / Trasse", report.get("route_environment_summary")),
        ("Stakeholder-Zielkonflikt", report.get("stakeholder_konflikt")),
        ("Empfohlener Fokus", report.get("recommended_focus")),
    ]
    if any(value for _label, value in extra_blocks):
        story.append(_p("Anschlussstrategie / Risiko", _SECTION_TITLE_STYLE))
        for label, value in extra_blocks:
            if value:
                story.append(_p(f"{label}: {value}", body))
    elif report.get("scope_boundary_note"):
        story.append(_p("Paketgrenze", _SECTION_TITLE_STYLE))
        story.append(_p(str(report.get("scope_boundary_note")), body))

    if rt == "invest":
        kpi = list(report.get("kpi_summary") or [])
        if kpi:
            story.append(_p("KPI-Zusammenfassung", _SECTION_TITLE_STYLE))
            _bulleted_block(story, body, kpi, "")
        inv_timeline = list(report.get("process_timeline") or [])
        if inv_timeline:
            story.append(_p("Zeitplan-Indikation", _SECTION_TITLE_STYLE))
            _bulleted_block(story, body, inv_timeline, "")
        ki = report.get("kosten_indikation")
        if isinstance(ki, dict) and ki:
            story.append(_p("Kosten-Indikation", _SECTION_TITLE_STYLE))
            for k, v in sorted(ki.items(), key=lambda x: str(x[0])):
                story.append(_p(f"{k}: {v}", body))
        elif report.get("scope_boundary_note"):
            story.append(_p("Invest-Hinweis", _SECTION_TITLE_STYLE))
            story.append(_p(str(report.get("scope_boundary_note")), body))
        cost_band = report.get("cost_band")
        if isinstance(cost_band, dict) and cost_band:
            story.append(_p("Kostenbandbreite", _SECTION_TITLE_STYLE))
            for key in ("niedrig_eur", "basis_eur", "hoch_eur", "confidence_pct", "source"):
                if key in cost_band:
                    story.append(_p(f"{key}: {cost_band.get(key)}", body))
            assumptions = list(cost_band.get("assumptions") or [])
            drivers = list(cost_band.get("drivers") or [])
            if assumptions:
                story.append(_p("Annahmen", _SECTION_TITLE_STYLE))
                _bulleted_block(story, body, assumptions, "")
            if drivers:
                story.append(_p("Risikotreiber", _SECTION_TITLE_STYLE))
                _bulleted_block(story, body, drivers, "")
        site_assessment = list(report.get("site_assessment") or [])
        if site_assessment:
            story.append(_p("Standortbewertung", _SECTION_TITLE_STYLE))
            for item in site_assessment:
                if isinstance(item, dict):
                    story.append(
                        _p(
                            f"{item.get('label', '')} [{item.get('status', '')}]: {item.get('detail', '')}",
                            body,
                        )
                    )
        risk_overview = list(report.get("risk_overview") or [])
        if risk_overview:
            story.append(_p("Risikoanalyse", _SECTION_TITLE_STYLE))
            for item in risk_overview:
                if isinstance(item, dict):
                    story.append(
                        _p(
                            f"{item.get('label', '')} [{item.get('status', '')}]: {item.get('detail', '')}",
                            body,
                        )
                    )
        dd_items = list(report.get("due_diligence_checklist") or [])
        if dd_items:
            story.append(_p("Due-Diligence-orientierte Sicht", _SECTION_TITLE_STYLE))
            for item in dd_items:
                if isinstance(item, dict):
                    story.append(
                        _p(
                            f"{item.get('label', '')} [{item.get('status', '')}]: {item.get('detail', '')}",
                            body,
                        )
                    )
        if report.get("portfolio_view"):
            story.append(_p("Portfolio- / Vergleichssicht", _SECTION_TITLE_STYLE))
            _bulleted_block(story, body, list(report.get("portfolio_view") or []), "")

    story.append(_p("Normen-Snapshot", _SECTION_TITLE_STYLE))
    norms = list(report.get("normen_snapshot") or [])
    if norms:
        # Abbreviated: key fields only (Titel oft lang)
        tbl_data: list[list[str]] = [["Norm-ID", "Stand", "Kategorie"]]
        for n in norms:
            if not isinstance(n, dict):
                continue
            tbl_data.append(
                [
                    str(n.get("norm_id", "")),
                    str(n.get("stand", "")),
                    str(n.get("kategorie", "")),
                ]
            )
        tw = doc.width
        t = Table(tbl_data, colWidths=[tw * 0.42, tw * 0.28, tw * 0.28])
        t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(B.GRAU_ZEBRA)),
                    ("FONTNAME", (0, 0), (-1, 0), B.FONT_BOLD),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor(B.GRAU_LINIE)),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        story.append(t)
    else:
        story.append(_p("Keine Normen-Einträge.", body))

    transparency_notes = list(report.get("transparenz_hinweise") or [])
    if transparency_notes:
        story.append(_p("Transparenz / Confidence", _SECTION_TITLE_STYLE))
        _bulleted_block(story, body, transparency_notes, "Keine zusätzlichen Hinweise.")
    if report.get("data_role_summary"):
        story.append(_p("Daten-, Pruef- und Auditrolle", _SECTION_TITLE_STYLE))
        story.append(_p(str(report.get("data_role_summary")), body))
    if report.get("data_basis"):
        story.append(_p("Datenbasis", _SECTION_TITLE_STYLE))
        _bulleted_block(story, body, list(report.get("data_basis") or []), "")
    if report.get("visibility_boundary_note"):
        story.append(_p("Sichtbarkeitsgrenze", _SECTION_TITLE_STYLE))
        story.append(_p(str(report.get("visibility_boundary_note")), body))

    if rt == "vnb":
        sig = report.get("signature_section")
        if isinstance(sig, dict) and sig.get("fields"):
            story.append(_p(str(sig.get("title") or "VNB-Prüfung / Freigabe"), _SECTION_TITLE_STYLE))
            for field in sig.get("fields") or []:
                if isinstance(field, dict):
                    story.append(
                        _p(
                            f"{field.get('label', '')}: {field.get('placeholder', '')}",
                            body,
                        )
                    )
            if sig.get("disclaimer"):
                story.append(_p(str(sig["disclaimer"]), muted))

    story.append(Spacer(1, 4 * mm))
    story.append(
        _p(
            "Vorläufige Analyse. Keine verbindliche Netzanschlusszusage. "
            "Keine Kapazitätsgarantie. Freie Netzkapazität nur mit belastbarem Datenstand des VNB.",
            muted,
        )
    )
    disclaimers = list(report.get("disclaimers") or [])
    if disclaimers:
        _bulleted_block(story, muted, disclaimers, "")

    doc.build(story, onFirstPage=B.footer_callback, onLaterPages=B.footer_callback)
    return buf.getvalue()
