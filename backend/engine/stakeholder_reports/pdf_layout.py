"""
PDF layout primitives for stakeholder reports.

Stakeholder-specific palettes, status badges, key-value rows, alternating tables,
KPI cards and signature blocks. Used by `pdf_builder.py` to compose three
stakeholder layouts (Projektierer, VNB, Invest) with consistent quality.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether, Paragraph, Spacer, Table, TableStyle


# === Stakeholder palettes ==============================================
@dataclass(frozen=True)
class StakeholderPalette:
    primary: str
    primary_dark: str
    accent: str
    text: str
    text_muted: str
    zebra: str
    border: str
    pass_color: str
    warn_color: str
    fail_color: str
    label: str


PROJEKTIERER_PALETTE = StakeholderPalette(
    primary="#0F3460",
    primary_dark="#0A1F3D",
    accent="#1F6FEB",
    text="#1F2A2E",
    text_muted="#5A6B70",
    zebra="#F1F5F9",
    border="#CBD5E1",
    pass_color="#16A34A",
    warn_color="#D97706",
    fail_color="#DC2626",
    label="Projektierer",
)

VNB_PALETTE = StakeholderPalette(
    primary="#1E40AF",
    primary_dark="#1E3A8A",
    accent="#0EA5E9",
    text="#1F2A2E",
    text_muted="#475569",
    zebra="#EEF2FF",
    border="#C7D2FE",
    pass_color="#16A34A",
    warn_color="#D97706",
    fail_color="#DC2626",
    label="Netzbetreiber (VNB)",
)

INVEST_PALETTE = StakeholderPalette(
    primary="#7C3AED",
    primary_dark="#5B21B6",
    accent="#F59E0B",
    text="#1F2A2E",
    text_muted="#52525B",
    zebra="#F5F3FF",
    border="#DDD6FE",
    pass_color="#16A34A",
    warn_color="#D97706",
    fail_color="#DC2626",
    label="Investor / Management",
)


def palette_for(report_type: str) -> StakeholderPalette:
    rt = (report_type or "").strip().lower()
    if rt == "vnb":
        return VNB_PALETTE
    if rt == "invest":
        return INVEST_PALETTE
    return PROJEKTIERER_PALETTE


# === Style factories ==================================================
FONT_REGULAR = "Helvetica"
FONT_BOLD = "Helvetica-Bold"


def title_style(palette: StakeholderPalette) -> ParagraphStyle:
    return ParagraphStyle(
        "title",
        fontName=FONT_BOLD,
        fontSize=18,
        textColor=colors.white,
        leading=22,
        leftIndent=0,
    )


def subtitle_style(palette: StakeholderPalette) -> ParagraphStyle:
    return ParagraphStyle(
        "subtitle",
        fontName=FONT_REGULAR,
        fontSize=10,
        textColor=colors.HexColor("#FFFFFFCC"),
        leading=12,
    )


def section_style(palette: StakeholderPalette) -> ParagraphStyle:
    return ParagraphStyle(
        "section",
        fontName=FONT_BOLD,
        fontSize=12,
        textColor=colors.HexColor(palette.primary),
        spaceBefore=10,
        spaceAfter=4,
        leading=15,
    )


def body_style(palette: StakeholderPalette) -> ParagraphStyle:
    return ParagraphStyle(
        "body",
        fontName=FONT_REGULAR,
        fontSize=10,
        textColor=colors.HexColor(palette.text),
        leading=13,
    )


def body_bold_style(palette: StakeholderPalette) -> ParagraphStyle:
    return ParagraphStyle(
        "body_bold",
        fontName=FONT_BOLD,
        fontSize=10,
        textColor=colors.HexColor(palette.text),
        leading=13,
    )


def muted_style(palette: StakeholderPalette) -> ParagraphStyle:
    return ParagraphStyle(
        "muted",
        fontName=FONT_REGULAR,
        fontSize=8.5,
        textColor=colors.HexColor(palette.text_muted),
        leading=11,
    )


def hero_value_style(palette: StakeholderPalette) -> ParagraphStyle:
    return ParagraphStyle(
        "hero_value",
        fontName=FONT_BOLD,
        fontSize=22,
        textColor=colors.HexColor(palette.primary),
        leading=26,
    )


def hero_label_style(palette: StakeholderPalette) -> ParagraphStyle:
    return ParagraphStyle(
        "hero_label",
        fontName=FONT_REGULAR,
        fontSize=8.5,
        textColor=colors.HexColor(palette.text_muted),
        leading=11,
    )


# === Helpers ==========================================================
def _esc(value: Any) -> str:
    return escape(str(value if value is not None else ""))


def p(text: Any, style: ParagraphStyle) -> Paragraph:
    return Paragraph(_esc(text), style)


def p_html(html: str, style: ParagraphStyle) -> Paragraph:
    """Paragraph that allows pre-escaped/safe HTML markup (for inline color spans)."""
    return Paragraph(html, style)


# === Status badge =====================================================
_STATUS_MAP = {
    "PASS": ("PASS", "pass"),
    "OK": ("OK", "pass"),
    "GRUEN": ("OK", "pass"),
    "GRÜN": ("OK", "pass"),
    "GREEN": ("OK", "pass"),
    "BESTANDEN": ("BESTANDEN", "pass"),
    "VORHANDEN": ("VORHANDEN", "pass"),
    "VOLLSTAENDIG": ("VOLLSTÄNDIG", "pass"),
    "VOLLSTÄNDIG": ("VOLLSTÄNDIG", "pass"),
    "HOCH": ("HOCH", "pass"),
    "WARN": ("WARN", "warn"),
    "GELB": ("WARN", "warn"),
    "ORANGE": ("WARN", "warn"),
    "MITTEL": ("MITTEL", "warn"),
    "TEILWEISE": ("TEILWEISE", "warn"),
    "OFFEN": ("OFFEN", "warn"),
    "FAIL": ("FAIL", "fail"),
    "FEHLER": ("FEHLER", "fail"),
    "ROT": ("FAIL", "fail"),
    "RED": ("FAIL", "fail"),
    "NIEDRIG": ("NIEDRIG", "fail"),
    "NICHT BESTANDEN": ("NICHT BESTANDEN", "fail"),
}


def classify_status(raw: Any) -> tuple[str, str]:
    """Return (label, severity) for a free-form engine status string.

    severity is one of 'pass' | 'warn' | 'fail' | 'neutral'.
    """
    token = str(raw or "").strip().upper()
    if not token:
        return ("OFFEN", "neutral")
    if token in _STATUS_MAP:
        return _STATUS_MAP[token]
    if "FAIL" in token or "ROT" in token or "ABGE" in token:
        return (token, "fail")
    if "WARN" in token or "GELB" in token or "MITTEL" in token:
        return (token, "warn")
    if "PASS" in token or "OK" in token or "GRUEN" in token or "GRÜN" in token:
        return (token, "pass")
    return (token, "neutral")


def severity_color(palette: StakeholderPalette, severity: str) -> str:
    if severity == "pass":
        return palette.pass_color
    if severity == "warn":
        return palette.warn_color
    if severity == "fail":
        return palette.fail_color
    return palette.text_muted


def status_badge_text(palette: StakeholderPalette, raw: Any) -> str:
    """Inline-HTML badge: small colored bullet + label, safe for Paragraph()."""
    label, severity = classify_status(raw)
    color = severity_color(palette, severity)
    bullet = f'<font color="{color}"><b>●</b></font>'
    return f"{bullet} {escape(label)}"


def status_badge_paragraph(
    palette: StakeholderPalette, raw: Any, *, body: ParagraphStyle | None = None
) -> Paragraph:
    style = body or body_style(palette)
    return p_html(status_badge_text(palette, raw), style)


# === Key/Value row ====================================================
def kv_row(palette: StakeholderPalette, key: str, value: Any, doc_width: float) -> Table:
    """Two-column key/value row used in cover and identification blocks."""
    bold = body_bold_style(palette)
    body = body_style(palette)
    t = Table(
        [[p(key, bold), p(value if value not in (None, "") else "—", body)]],
        colWidths=[doc_width * 0.32, doc_width * 0.68],
    )
    t.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 1),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
            ]
        )
    )
    return t


def kv_table(
    palette: StakeholderPalette,
    rows: list[tuple[str, Any]],
    doc_width: float,
    *,
    boxed: bool = True,
) -> Table:
    """Compact 2-column key/value table with optional outer border."""
    bold = body_bold_style(palette)
    body = body_style(palette)
    data = [[p(k, bold), p(v if v not in (None, "") else "—", body)] for k, v in rows]
    t = Table(data, colWidths=[doc_width * 0.32, doc_width * 0.68])
    style_cmds = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    if boxed:
        style_cmds += [
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor(palette.border)),
            ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor(palette.border)),
        ]
    for r_idx in range(len(data)):
        if r_idx % 2 == 1:
            style_cmds.append(("BACKGROUND", (0, r_idx), (-1, r_idx), colors.HexColor(palette.zebra)))
    t.setStyle(TableStyle(style_cmds))
    return t


# === Alternating-row data table =======================================
def alt_table(
    palette: StakeholderPalette,
    headers: list[str],
    rows: list[list[Any]],
    *,
    col_widths: list[float] | None = None,
    cell_style: ParagraphStyle | None = None,
) -> Table:
    """Table with header band, alternating zebra rows, palette border."""
    body = cell_style or body_style(palette)
    head_style = ParagraphStyle(
        "alt_head",
        fontName=FONT_BOLD,
        fontSize=9,
        textColor=colors.white,
        leading=11,
        alignment=0,
    )
    head_cells = [p(h, head_style) for h in headers]
    body_cells: list[list[Any]] = []
    for row in rows:
        body_cells.append([cell if isinstance(cell, Paragraph) else p(cell, body) for cell in row])
    data = [head_cells, *body_cells]
    n = len(headers)
    cw = col_widths or None
    t = Table(data, colWidths=cw, repeatRows=1)
    cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(palette.primary)),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor(palette.border)),
        ("LINEBELOW", (0, 0), (-1, 0), 1.0, colors.HexColor(palette.primary_dark)),
    ]
    for r in range(1, len(data)):
        if r % 2 == 0:
            cmds.append(("BACKGROUND", (0, r), (-1, r), colors.HexColor(palette.zebra)))
    t.setStyle(TableStyle(cmds))
    _ = n
    return t


# === Hero / KPI card ==================================================
def kpi_card(
    palette: StakeholderPalette,
    *,
    label: str,
    value: str,
    sublabel: str = "",
    width_mm: float = 40,
) -> Table:
    """Small card with a big value, label above and optional sublabel below."""
    label_p = Paragraph(_esc(label), hero_label_style(palette))
    value_p = Paragraph(_esc(value), hero_value_style(palette))
    sub_p = Paragraph(_esc(sublabel), muted_style(palette)) if sublabel else None
    rows: list[list[Any]] = [[label_p], [value_p]]
    if sub_p is not None:
        rows.append([sub_p])
    t = Table(rows, colWidths=[width_mm * mm])
    t.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(palette.zebra)),
                ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor(palette.border)),
                ("LINEBELOW", (0, 0), (-1, 0), 1.0, colors.HexColor(palette.primary)),
            ]
        )
    )
    return t


def kpi_strip(
    palette: StakeholderPalette,
    cards: list[tuple[str, str, str]],
    doc_width: float,
) -> Table:
    """Strip of equal-width KPI cards: list of (label, value, sublabel)."""
    if not cards:
        return Table([[Spacer(1, 1)]])
    n = len(cards)
    w_mm = (doc_width / mm) / n
    cells = [
        kpi_card(palette, label=lbl, value=val, sublabel=sub, width_mm=w_mm)
        for lbl, val, sub in cards
    ]
    t = Table([cells], colWidths=[doc_width / n] * n)
    t.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 2),
                ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    return t


# === Brand header banner =============================================
def brand_header(
    palette: StakeholderPalette,
    *,
    title: str,
    subtitle: str,
    doc_width: float,
) -> Table:
    """Stakeholder-coloured top banner with GridCheck wordmark + title + subtitle."""
    title_p = Paragraph(_esc(title), title_style(palette))
    sub_p = Paragraph(_esc(subtitle), subtitle_style(palette))
    wordmark_style = ParagraphStyle(
        "wordmark",
        fontName=FONT_BOLD,
        fontSize=14,
        textColor=colors.white,
        leading=16,
    )
    product_style = ParagraphStyle(
        "product",
        fontName=FONT_REGULAR,
        fontSize=8.5,
        textColor=colors.HexColor("#FFFFFFAA"),
        leading=10,
    )
    left = Table(
        [[Paragraph("GridCheck", wordmark_style)], [Paragraph(_esc(palette.label), product_style)]],
        colWidths=[doc_width * 0.30],
    )
    left.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    right = Table(
        [[title_p], [sub_p]],
        colWidths=[doc_width * 0.70],
    )
    right.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    title_p.style.alignment = 2  # right
    sub_p.style.alignment = 2

    banner = Table([[left, right]], colWidths=[doc_width * 0.30, doc_width * 0.70])
    banner.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(palette.primary)),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ("LINEBELOW", (0, 0), (-1, -1), 2.5, colors.HexColor(palette.accent)),
            ]
        )
    )
    return banner


# === Executive summary box ===========================================
def summary_box(
    palette: StakeholderPalette,
    *,
    headline: str,
    body_text: str,
    severity: str = "neutral",
    doc_width: float,
) -> Table:
    """Boxed summary block (cover or hero); severity drives the side bar colour."""
    bar_color = severity_color(palette, severity)
    head_style = ParagraphStyle(
        "summary_head",
        fontName=FONT_BOLD,
        fontSize=13,
        textColor=colors.HexColor(palette.primary),
        leading=16,
    )
    body_para = ParagraphStyle(
        "summary_body",
        fontName=FONT_REGULAR,
        fontSize=10,
        textColor=colors.HexColor(palette.text),
        leading=13,
    )
    inner = Table(
        [
            [Paragraph(_esc(headline), head_style)],
            [Paragraph(_esc(body_text), body_para)],
        ],
        colWidths=[doc_width - 6 * mm],
    )
    inner.setStyle(
        TableStyle(
            [
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    box = Table([[inner]], colWidths=[doc_width])
    box.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(palette.zebra)),
                ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor(palette.border)),
                ("LINEBEFORE", (0, 0), (0, -1), 4, colors.HexColor(bar_color)),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return box


# === Signature block (3 boxes side-by-side) ==========================
def signature_block(
    palette: StakeholderPalette,
    boxes: list[dict[str, str]],
    doc_width: float,
) -> Table:
    """Three signature boxes (Antragsteller, Sachbearbeiter, Freizeichnung)."""
    label_style_local = ParagraphStyle(
        "sig_label",
        fontName=FONT_BOLD,
        fontSize=9,
        textColor=colors.HexColor(palette.primary),
        leading=11,
    )
    place_style = ParagraphStyle(
        "sig_place",
        fontName=FONT_REGULAR,
        fontSize=8,
        textColor=colors.HexColor(palette.text_muted),
        leading=10,
    )
    cells: list[Any] = []
    for box in boxes:
        rows: list[list[Any]] = [
            [Paragraph(_esc(box.get("label", "")), label_style_local)],
            [Paragraph("&nbsp;", place_style)],
            [Paragraph("&nbsp;", place_style)],
            [Paragraph(_esc(box.get("placeholder") or "Datum, Ort"), place_style)],
            [Paragraph(_esc(box.get("hint") or "Unterschrift / Stempel"), place_style)],
        ]
        cell = Table(rows, colWidths=[(doc_width - 8 * mm) / max(1, len(boxes))])
        cell.setStyle(
            TableStyle(
                [
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor(palette.border)),
                    ("LINEABOVE", (0, 4), (-1, 4), 0.4, colors.HexColor(palette.text_muted)),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        cells.append(cell)
    if not cells:
        return Table([[Spacer(1, 1)]])
    n = len(cells)
    return Table([cells], colWidths=[doc_width / n] * n)


# === Decision-pick boxes (VNB approve / approve-with-conditions / reject) ===
def decision_picks(
    palette: StakeholderPalette,
    options: list[str],
    doc_width: float,
) -> Table:
    """Row of ankreuzbare Felder (VNB Entscheidungsblock)."""
    box_style = ParagraphStyle(
        "decision",
        fontName=FONT_BOLD,
        fontSize=9.5,
        textColor=colors.HexColor(palette.primary),
        leading=12,
    )
    cells = [Paragraph(f"☐ &nbsp; {_esc(opt)}", box_style) for opt in options]
    if not cells:
        return Table([[Spacer(1, 1)]])
    n = len(cells)
    t = Table([cells], colWidths=[doc_width / n] * n)
    t.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor(palette.border)),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor(palette.border)),
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(palette.zebra)),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    return t


# === Lined free-form notes area =====================================
def lined_field(
    palette: StakeholderPalette, *, lines: int = 5, doc_width: float
) -> Table:
    """A bordered block with ruled lines for handwritten notes."""
    line_style = ParagraphStyle(
        "lined_blank",
        fontName=FONT_REGULAR,
        fontSize=10,
        textColor=colors.HexColor(palette.text_muted),
        leading=18,
    )
    rows = [[Paragraph("&nbsp;", line_style)] for _ in range(lines)]
    t = Table(rows, colWidths=[doc_width])
    cmds = [
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor(palette.border)),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    for r_idx in range(lines):
        cmds.append(
            ("LINEBELOW", (0, r_idx), (-1, r_idx), 0.25, colors.HexColor(palette.border))
        )
    t.setStyle(TableStyle(cmds))
    return t


# === Bulleted block ==================================================
def bulleted_block(
    palette: StakeholderPalette,
    items: list[str],
    *,
    empty_label: str = "—",
) -> list[Any]:
    body = body_style(palette)
    if not items:
        return [p(empty_label, muted_style(palette))]
    flow: list[Any] = []
    for line in items:
        line_text = str(line).strip()
        if not line_text:
            continue
        flow.append(p_html(f"&bull;&nbsp;{escape(line_text)}", body))
    if not flow:
        return [p(empty_label, muted_style(palette))]
    return flow


# === KeepTogether wrappers for short sections =======================
def section(
    palette: StakeholderPalette,
    title: str,
    flowables: list[Any],
    *,
    keep: bool = False,
) -> list[Any]:
    head = p(title, section_style(palette))
    block: list[Any] = [head, *flowables]
    if keep:
        return [KeepTogether(block)]
    return block


# === Footer factory ==================================================
def make_footer_callback(
    palette: StakeholderPalette,
    *,
    short_hash: str,
    disclaimer: str = (
        "Vorläufige Diagnose – keine verbindliche Netzanschlusszusage. "
        "Prüfung durch zuständigen VNB erforderlich."
    ),
):
    """ReportLab onPage callback that draws a coloured footer with hash + page no."""
    def _draw(canvas, doc) -> None:
        canvas.saveState()
        breite, _ = doc.pagesize
        y = 10 * mm
        canvas.setStrokeColor(colors.HexColor(palette.accent))
        canvas.setLineWidth(0.7)
        canvas.line(15 * mm, y + 6 * mm, breite - 15 * mm, y + 6 * mm)
        canvas.setFont(FONT_REGULAR, 7.5)
        canvas.setFillColor(colors.HexColor(palette.text_muted))
        left_text = f"GridCheck {palette.label} · {disclaimer}"
        canvas.drawString(15 * mm, y + 2.2 * mm, left_text[:140])
        canvas.setFont(FONT_REGULAR, 7)
        canvas.drawString(15 * mm, y - 1.8 * mm, f"SHA-256 (Audit): {short_hash}")
        canvas.setFont(FONT_BOLD, 7.5)
        canvas.setFillColor(colors.HexColor(palette.primary))
        canvas.drawRightString(breite - 15 * mm, y + 0.0 * mm, f"Seite {doc.page}")
        canvas.restoreState()

    return _draw
