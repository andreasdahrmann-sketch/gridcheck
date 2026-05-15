"""
B.6 - Revisions-Export (CSV / JSON / PDF).

Reine Business-Logik, FastAPI-unabhaengig.
Liefert immer einen Audit-Header mit Integritaetsstatus.
"""
from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Tuple

from engine.revision import lade_revisionen, pruefe_integritaet, SCHEMA_VERSION


def _audit_header() -> Dict[str, Any]:
    """Gemeinsamer Audit-Header fuer alle Exporte."""
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
    """Vollstaendiger JSON-Export mit Audit-Header + alle Eintraege."""
    return {
        "audit": _audit_header(),
        "revisionen": lade_revisionen(),
    }


def export_csv() -> str:
    """Flache CSV: rev_nr, timestamp, engine_version, hash, previous_hash."""
    revs = lade_revisionen()
    buf = io.StringIO()
    writer = csv.writer(buf, delimiter=";", quoting=csv.QUOTE_MINIMAL)
    writer.writerow([
        "revisionsnummer", "timestamp", "engine_version",
        "schema_version", "hash", "previous_hash", "uuid",
    ])
    for r in revs:
        writer.writerow([
            r.get("revisionsnummer", ""),
            r.get("timestamp", ""),
            r.get("engine_version", ""),
            r.get("schema_version", ""),
            r.get("hash", ""),
            r.get("previous_hash", ""),
            r.get("uuid", ""),
        ])
    return buf.getvalue()


def export_pdf() -> bytes:
    """Audit-tauglicher PDF-Report mit Header, Integritaets-Bestaetigung, Tabelle."""
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
    )

    header = _audit_header()
    revs = lade_revisionen()

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=landscape(A4),
        leftMargin=15 * mm, rightMargin=15 * mm,
        topMargin=15 * mm, bottomMargin=15 * mm,
        title="GridCheck Revisions-Audit-Report",
    )

    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=styles["Heading1"], fontSize=16, spaceAfter=8)
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], fontSize=12, spaceAfter=6)
    body = styles["BodyText"]

    story: List[Any] = []

    # --- Titel ---
    story.append(Paragraph("GridCheck — Revisions-Audit-Report", h1))
    story.append(Paragraph(
        f"Erzeugt: {header['export_timestamp']}<br/>"
        f"Schema-Version: {header['schema_version']}",
        body,
    ))
    story.append(Spacer(1, 6 * mm))

    # --- Integritaets-Box ---
    status_text = "INTEGER" if header["chain_ok"] else "MANIPULATION ERKANNT"
    status_color = colors.HexColor("#0a7d2c") if header["chain_ok"] else colors.HexColor("#b71c1c")

    integ_data = [
        ["Status der Hash-Chain:", status_text],
        ["Anzahl Eintraege:", str(header["anzahl_eintraege"])],
        ["Letzter Hash (SHA-256):", (header["letzter_hash"] or "-")[:32] + "..." if header["letzter_hash"] else "-"],
        ["Engine-Versionen:", ", ".join(f"{k}:{v}" for k, v in (header["engine_versions"] or {}).items()) or "-"],
    ]
    if header["chain_fehler"]:
        integ_data.append(["Fehler:", "; ".join(header["chain_fehler"][:3])])

    t_integ = Table(integ_data, colWidths=[55 * mm, 200 * mm])
    t_integ.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f0f0f0")),
        ("TEXTCOLOR", (1, 0), (1, 0), status_color),
        ("FONTNAME", (1, 0), (1, 0), "Helvetica-Bold"),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.grey),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t_integ)
    story.append(Spacer(1, 8 * mm))

    # --- Revisionstabelle ---
    story.append(Paragraph("Revisionskette (chronologisch)", h2))

    if not revs:
        story.append(Paragraph("<i>Keine Revisionen vorhanden.</i>", body))
    else:
        rows = [["#", "Timestamp (UTC)", "Engine", "Hash (kurz)", "Prev (kurz)"]]
        for r in revs:
            rows.append([
                str(r.get("revisionsnummer", "")),
                str(r.get("timestamp", ""))[:19],
                str(r.get("engine_version", ""))[:18],
                str(r.get("hash", ""))[:16] + "...",
                (str(r.get("previous_hash", ""))[:16] + "...") if r.get("previous_hash") else "GENESIS",
            ])
        t = Table(rows, colWidths=[15 * mm, 50 * mm, 40 * mm, 70 * mm, 70 * mm], repeatRows=1)
        t.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME", (0, 1), (-1, -1), "Courier"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f4e79")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7f7f7")]),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.append(t)

    # --- Footer ---
    story.append(Spacer(1, 8 * mm))
    story.append(Paragraph(
        "<i>Dieser Report ist GoBD-konform. Die Hash-Chain ist append-only und manipulationssicher. "
        "Verifikation jederzeit moeglich via GET /api/v2/revisions/verify</i>",
        body,
    ))

    doc.build(story)
    return buf.getvalue()
