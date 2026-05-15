"""
B.6 - Revisions-Export (CSV / JSON / PDF).
Polish B.6.1: Corporate Design (Dunkellila / Hellgrau, kraeftigere Schrift).
"""
from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone
from typing import Dict, Any, List

from engine.revision import lade_revisionen, pruefe_integritaet, SCHEMA_VERSION


# === Corporate Design ===
FARBE_PRIMAER = "#4A148C"      # Dunkellila
FARBE_PRIMAER_HELL = "#7B1FA2"  # Akzent
FARBE_GRAU_HELL = "#F5F5F5"    # Zebra
FARBE_GRAU_MITTEL = "#E0E0E0"  # Linien
FARBE_TEXT = "#212121"
FARBE_OK = "#2E7D32"           # Gruen
FARBE_FEHLER = "#C62828"       # Rot


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
    buf.write(f"# GridCheck Revisions-Export\n")
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
    """Audit-PDF im Corporate Design (Dunkellila / Hellgrau)."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
    )

    header = _audit_header()
    revs = lade_revisionen()

    primaer = colors.HexColor(FARBE_PRIMAER)
    primaer_hell = colors.HexColor(FARBE_PRIMAER_HELL)
    grau_hell = colors.HexColor(FARBE_GRAU_HELL)
    grau_mittel = colors.HexColor(FARBE_GRAU_MITTEL)
    text_col = colors.HexColor(FARBE_TEXT)
    ok_col = colors.HexColor(FARBE_OK)
    fehler_col = colors.HexColor(FARBE_FEHLER)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        topMargin=18 * mm, bottomMargin=18 * mm,
        leftMargin=18 * mm, rightMargin=18 * mm,
        title="GridCheck Audit-Report",
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "Title", parent=styles["Title"],
        fontName="Helvetica-Bold", fontSize=20,
        textColor=colors.white, alignment=0, leading=24,
    )
    subtitle_style = ParagraphStyle(
        "Subtitle", parent=styles["Normal"],
        fontName="Helvetica-Bold", fontSize=10,
        textColor=colors.white, leading=13,
    )
    h2_style = ParagraphStyle(
        "H2", parent=styles["Heading2"],
        fontName="Helvetica-Bold", fontSize=13,
        textColor=primaer, spaceAfter=6, spaceBefore=8,
    )
    label_style = ParagraphStyle(
        "Label", parent=styles["Normal"],
        fontName="Helvetica-Bold", fontSize=9,
        textColor=primaer, leading=12,
    )
    value_style = ParagraphStyle(
        "Value", parent=styles["Normal"],
        fontName="Helvetica", fontSize=9,
        textColor=text_col, leading=12,
    )
    mono_style = ParagraphStyle(
        "Mono", parent=styles["Normal"],
        fontName="Courier-Bold", fontSize=8,
        textColor=text_col, leading=11,
    )

    story = []

    # === Header-Banner (Dunkellila Box) ===
    banner_data = [
        [Paragraph("GridCheck", title_style)],
        [Paragraph("Revisionssicherer Audit-Report &middot; GoBD-konform", subtitle_style)],
    ]
    banner = Table(banner_data, colWidths=[doc.width])
    banner.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), primaer),
        ("LEFTPADDING", (0, 0), (-1, -1), 14),
        ("RIGHTPADDING", (0, 0), (-1, -1), 14),
        ("TOPPADDING", (0, 0), (0, 0), 12),
        ("BOTTOMPADDING", (0, -1), (-1, -1), 12),
        ("TOPPADDING", (0, 1), (-1, 1), 0),
    ]))
    story.append(banner)
    story.append(Spacer(1, 8 * mm))

    # === Status-Badge ===
    status_text = "CHAIN OK" if header["chain_ok"] else "CHAIN FEHLER"
    status_col = ok_col if header["chain_ok"] else fehler_col
    badge_style = ParagraphStyle(
        "Badge", parent=styles["Normal"],
        fontName="Helvetica-Bold", fontSize=12,
        textColor=colors.white, alignment=1, leading=16,
    )
    badge = Table([[Paragraph(status_text, badge_style)]], colWidths=[60 * mm])
    badge.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), status_col),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(badge)
    story.append(Spacer(1, 6 * mm))

    # === Audit-Metadaten Tabelle ===
    story.append(Paragraph("Audit-Metadaten", h2_style))

    meta_rows = [
        [Paragraph("Export-Timestamp", label_style), Paragraph(header["export_timestamp"], value_style)],
        [Paragraph("Schema-Version", label_style), Paragraph(str(header["schema_version"]), value_style)],
        [Paragraph("Anzahl Eintraege", label_style), Paragraph(str(header["anzahl_eintraege"]), value_style)],
        [Paragraph("Engine-Versionen", label_style), Paragraph(", ".join(header["engine_versions"]) or "-", value_style)],
        [Paragraph("Letzter Hash", label_style), Paragraph(header["letzter_hash"] or "-", mono_style)],
    ]
    meta_tbl = Table(meta_rows, colWidths=[45 * mm, doc.width - 45 * mm])
    meta_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), grau_hell),
        ("LINEBELOW", (0, 0), (-1, -2), 0.4, grau_mittel),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(meta_tbl)

    if header["chain_fehler"]:
        story.append(Spacer(1, 4 * mm))
        story.append(Paragraph("Chain-Fehler", h2_style))
        for f in header["chain_fehler"]:
            story.append(Paragraph(f"&bull; {f}", value_style))

    # === Revisions-Tabelle ===
    story.append(Spacer(1, 6 * mm))
    story.append(Paragraph(f"Revisionen ({len(revs)})", h2_style))

    if not revs:
        story.append(Paragraph("Keine Revisionen vorhanden.", value_style))
    else:
        head_style = ParagraphStyle(
            "TblHead", parent=styles["Normal"],
            fontName="Helvetica-Bold", fontSize=9,
            textColor=colors.white, leading=11,
        )
        cell_style = ParagraphStyle(
            "Cell", parent=styles["Normal"],
            fontName="Helvetica", fontSize=8,
            textColor=text_col, leading=10,
        )
        cell_mono = ParagraphStyle(
            "CellMono", parent=styles["Normal"],
            fontName="Courier", fontSize=7,
            textColor=text_col, leading=9,
        )

        data = [[
            Paragraph("Nr.", head_style),
            Paragraph("Timestamp", head_style),
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
            ("BACKGROUND", (0, 0), (-1, 0), primaer),
            ("LINEBELOW", (0, 0), (-1, 0), 1.0, primaer_hell),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LINEBELOW", (0, 1), (-1, -1), 0.25, grau_mittel),
        ]
        # Zebra-Streifen
        for i in range(1, len(data)):
            if i % 2 == 0:
                style_cmds.append(("BACKGROUND", (0, i), (-1, i), grau_hell))
        rev_tbl.setStyle(TableStyle(style_cmds))
        story.append(rev_tbl)

    # === Footer ===
    story.append(Spacer(1, 8 * mm))
    footer_style = ParagraphStyle(
        "Footer", parent=styles["Normal"],
        fontName="Helvetica-Bold", fontSize=7,
        textColor=primaer, alignment=1, leading=9,
    )
    story.append(Paragraph(
        f"GridCheck &middot; Audit-Report &middot; SHA-256 Hash-Chain &middot; Schema {header['schema_version']}",
        footer_style
    ))

    doc.build(story)
    return buf.getvalue()
