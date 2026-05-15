"""
B.6 - Revisions-Export (CSV / JSON / PDF).
B.6.2 - Refactor: Branding ueber core.branding (Adecarb CI).
"""
from __future__ import annotations

import csv
import io
from datetime import datetime, timezone
from typing import Dict, Any

from engine.revision import lade_revisionen, pruefe_integritaet, SCHEMA_VERSION
from core import branding as B


def _audit_header() -> Dict[str, Any]:
    integ = pruefe_integritaet()
    revs = lade_revisionen()
    letzter_hash = revs[-1].get("hash") if revs else None
    return {
        "export_timestamp": datetime.now(timezone.utc).isoformat(),
        "schema_version": SCHEMA_VERSION,
        "anzahl_eintraege": integ["anzahl"],
        "chain_ok": integ["ok"],
        "chain_fehler": integ["fehler"],
        "engine_versions": integ["engine_versions"],
        "letzter_hash": letzter_hash,
    }


def export_json() -> Dict[str, Any]:
    return {"audit": _audit_header(), "revisionen": lade_revisionen()}


def export_csv() -> str:
    revs = lade_revisionen()
    header = _audit_header()
    buf = io.StringIO()
    buf.write("# Adecarb GridCheck - Revisions-Export\n")
    buf.write(f"# Export-Timestamp: {header['export_timestamp']}\n")
    buf.write(f"# Schema-Version: {header['schema_version']}\n")
    buf.write(f"# Anzahl: {header['anzahl_eintraege']}\n")
    buf.write(f"# Chain-OK: {header['chain_ok']}\n")
    buf.write(f"# Letzter-Hash: {header['letzter_hash']}\n")
    buf.write("#\n")

    fieldnames = ["revisionsnummer", "timestamp", "engine_version", "hash", "vorgaenger_hash"]
    writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for r in revs:
        writer.writerow({k: r.get(k, "") for k in fieldnames})
    return buf.getvalue()


def export_pdf() -> bytes:
    """Audit-PDF im Adecarb Corporate Design (hell, druckoptimiert)."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

    header = _audit_header()
    revs = lade_revisionen()

    petrol = colors.HexColor(B.PETROL)
    orange = colors.HexColor(B.ORANGE)
    grau_bg = colors.HexColor(B.GRAU_BG)
    grau_linie = colors.HexColor(B.GRAU_LINIE)
    grau_zebra = colors.HexColor(B.GRAU_ZEBRA)
    text_col = colors.HexColor(B.TEXT)
    text_muted = colors.HexColor(B.TEXT_MUTED)
    ok_col = colors.HexColor(B.OK_GRUEN)
    fehler_col = colors.HexColor(B.FEHLER_ROT)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        topMargin=15 * mm, bottomMargin=22 * mm,
        leftMargin=15 * mm, rightMargin=15 * mm,
        title="Adecarb GridCheck - Audit-Report",
        author="Adecarb",
    )

    styles = getSampleStyleSheet()
    h2 = ParagraphStyle("H2", parent=styles["Heading2"],
                        fontName=B.FONT_BOLD, fontSize=12,
                        textColor=petrol, spaceAfter=4, spaceBefore=10)
    label = ParagraphStyle("Label", parent=styles["Normal"],
                           fontName=B.FONT_BOLD, fontSize=9,
                           textColor=petrol, leading=12)
    value = ParagraphStyle("Value", parent=styles["Normal"],
                           fontName=B.FONT_REGULAR, fontSize=9,
                           textColor=text_col, leading=12)
    mono = ParagraphStyle("Mono", parent=styles["Normal"],
                          fontName=B.FONT_MONO_BOLD, fontSize=8,
                          textColor=text_col, leading=11)

    story = []

    # === Header-Banner ===
    story.append(B.build_header_banner(doc.width / mm, untertitel="Revisions-Audit-Report"))
    story.append(Spacer(1, 6 * mm))

    # === Status-Badge ===
    chain_ok = header["chain_ok"]
    badge_text = "CHAIN-INTEGRITAET: OK" if chain_ok else "CHAIN-INTEGRITAET: FEHLER"
    badge_bg = ok_col if chain_ok else fehler_col
    badge_style = ParagraphStyle("Badge", fontName=B.FONT_BOLD, fontSize=11,
                                 textColor=colors.white, alignment=1, leading=14)
    badge = Table([[Paragraph(badge_text, badge_style)]], colWidths=[doc.width])
    badge.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), badge_bg),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    story.append(badge)
    story.append(Spacer(1, 5 * mm))

    # === Audit-Metadaten ===
    story.append(Paragraph("Audit-Metadaten", h2))
    meta_rows = [
        [Paragraph("Export-Timestamp", label), Paragraph(header["export_timestamp"], value)],
        [Paragraph("Schema-Version", label), Paragraph(str(header["schema_version"]), value)],
        [Paragraph("Anzahl Eintraege", label), Paragraph(str(header["anzahl_eintraege"]), value)],
        [Paragraph("Engine-Versionen", label), Paragraph(", ".join(header["engine_versions"]) or "-", value)],
        [Paragraph("Letzter Hash", label), Paragraph(header["letzter_hash"] or "-", mono)],
    ]
    meta_tbl = Table(meta_rows, colWidths=[45 * mm, doc.width - 45 * mm])
    meta_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), grau_bg),
        ("LINEBELOW", (0, 0), (-1, -2), 0.4, grau_linie),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(meta_tbl)

    if header["chain_fehler"]:
        story.append(Spacer(1, 4 * mm))
        story.append(Paragraph("Chain-Fehler", h2))
        for f in header["chain_fehler"]:
            story.append(Paragraph(f"&bull; {f}", value))

    # === Revisions-Tabelle ===
    story.append(Spacer(1, 5 * mm))
    story.append(Paragraph(f"Revisionen ({len(revs)})", h2))

    if not revs:
        story.append(Paragraph("Keine Revisionen vorhanden.", value))
    else:
        head_style = ParagraphStyle("TblHead", fontName=B.FONT_BOLD, fontSize=9,
                                    textColor=colors.white, leading=11)
        cell_style = ParagraphStyle("Cell", fontName=B.FONT_REGULAR, fontSize=8,
                                    textColor=text_col, leading=10)
        cell_mono = ParagraphStyle("CellMono", fontName=B.FONT_MONO, fontSize=7,
                                   textColor=text_col, leading=9)

        data = [[
            Paragraph("Nr.", head_style),
            Paragraph("Timestamp (UTC)", head_style),
            Paragraph("Engine", head_style),
            Paragraph("Hash (gekuerzt)", head_style),
        ]]
        for r in revs:
            h = r.get("hash", "")
            h_short = f"{h[:12]}...{h[-8:]}" if len(h) > 24 else h
            data.append([
                Paragraph(str(r.get("revisionsnummer", "")), cell_style),
                Paragraph(str(r.get("timestamp", "")), cell_style),
                Paragraph(str(r.get("engine_version", "")), cell_style),
                Paragraph(h_short, cell_mono),
            ])

        col_widths = [15 * mm, 50 * mm, 30 * mm, doc.width - 95 * mm]
        rev_tbl = Table(data, colWidths=col_widths, repeatRows=1)
        style_cmds = [
            ("BACKGROUND", (0, 0), (-1, 0), petrol),
            ("LINEBELOW", (0, 0), (-1, 0), 1.5, orange),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LINEBELOW", (0, 1), (-1, -1), 0.25, grau_linie),
        ]
        for i in range(1, len(data)):
            if i % 2 == 0:
                style_cmds.append(("BACKGROUND", (0, i), (-1, i), grau_zebra))
        rev_tbl.setStyle(TableStyle(style_cmds))
        story.append(rev_tbl)

    # Build mit Footer-Callback (Seitennummer + Akzentlinie)
    doc.build(story, onFirstPage=B.footer_callback, onLaterPages=B.footer_callback)
    return buf.getvalue()
