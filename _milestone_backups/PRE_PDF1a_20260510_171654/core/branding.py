"""
Adecarb Corporate Design - zentrale Branding-Konstanten und Helper.
Wiederverwendbar fuer alle PDF-Reports (Revisions-Audit, Netzanschluss-Check, ...).

Logo-Auto-Detection:
- Wenn assets/adecarb_logo.png existiert -> Bild-Logo
- Sonst -> Wordmark "ADECARB" als Fallback
"""
from __future__ import annotations

import os
from typing import Optional

# === Adecarb Farbpalette ===
PETROL = "#0B5563"          # Primary
PETROL_DARK = "#073E48"     # Hover/Akzent dunkel
ORANGE = "#F39200"          # Accent
ORANGE_DARK = "#C97600"

WEISS = "#FFFFFF"
GRAU_BG = "#F7F8F9"         # Section-Hintergrund hell
GRAU_LINIE = "#D6DBDF"      # Tabellenlinien
GRAU_ZEBRA = "#F0F2F4"      # Zebra-Stripes
TEXT = "#1F2A2E"            # Body-Text
TEXT_MUTED = "#5A6B70"

OK_GRUEN = "#2E7D32"
FEHLER_ROT = "#C62828"

# === Typo / Spacing ===
FONT_REGULAR = "Helvetica"
FONT_BOLD = "Helvetica-Bold"
FONT_MONO = "Courier"
FONT_MONO_BOLD = "Courier-Bold"

# === Logo ===
LOGO_DATEINAME = "adecarb_logo.png"
WORDMARK_TEXT = "GC"
PRODUKT_TEXT = "GridCheck"


def logo_pfad() -> Optional[str]:
    """Liefert Pfad zum Logo, falls vorhanden - sonst None (-> Wordmark-Fallback)."""
    kandidaten = [
        os.path.join("assets", LOGO_DATEINAME),
        os.path.join(os.path.dirname(__file__), "..", "assets", LOGO_DATEINAME),
    ]
    for p in kandidaten:
        if os.path.isfile(p):
            return os.path.abspath(p)
    return None


def build_header_banner(doc_width_mm: float, untertitel: str = "Audit-Report"):
    """
    Liefert eine Flowable (Table) als Header-Banner.
    Petrol-Hintergrund, Wordmark/Logo links, Untertitel rechts, Orange-Akzentlinie unten.
    """
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import Table, TableStyle, Paragraph, Image

    wordmark_style = ParagraphStyle(
        "Wordmark", fontName=FONT_BOLD, fontSize=22,
        textColor=colors.white, leading=26, leftIndent=0,
    )
    produkt_style = ParagraphStyle(
        "Produkt", fontName=FONT_REGULAR, fontSize=10,
        textColor=colors.HexColor(ORANGE), leading=12,
    )
    untertitel_style = ParagraphStyle(
        "Untertitel", fontName=FONT_BOLD, fontSize=12,
        textColor=colors.white, leading=14, alignment=2,  # rechtsbuendig
    )

    pfad = logo_pfad()
    if pfad:
        try:
            links = Image(pfad, width=40 * mm, height=12 * mm, kind="proportional")
        except Exception:
            links = Paragraph(WORDMARK_TEXT, wordmark_style)
    else:
        links = [
            Paragraph(WORDMARK_TEXT, wordmark_style),
            Paragraph(PRODUKT_TEXT, produkt_style),
        ]

    rechts = Paragraph(untertitel, untertitel_style)

    banner = Table(
        [[links, rechts]],
        colWidths=[doc_width_mm * 0.55, doc_width_mm * 0.45],
    )
    banner.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(PETROL)),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LINEBELOW", (0, 0), (-1, -1), 2.5, colors.HexColor(ORANGE)),
    ]))
    return banner


def footer_callback(canvas, doc):
    """Footer mit Seitennummer + Hash-Chain-Hinweis. Wird an doc.build(onFirstPage=, onLaterPages=) uebergeben."""
    from reportlab.lib import colors
    from reportlab.lib.units import mm

    canvas.saveState()
    breite, _ = doc.pagesize
    y = 10 * mm

    # Orange Akzentlinie
    canvas.setStrokeColor(colors.HexColor(ORANGE))
    canvas.setLineWidth(0.8)
    canvas.line(15 * mm, y + 6 * mm, breite - 15 * mm, y + 6 * mm)

    # Footer-Text
    canvas.setFont(FONT_REGULAR, 7.5)
    canvas.setFillColor(colors.HexColor(TEXT_MUTED))
    canvas.drawString(
        15 * mm, y,
        f"Adecarb {PRODUKT_TEXT}  -  SHA-256 Hash-Chain  -  GoBD-konform",
    )
    canvas.setFont(FONT_BOLD, 7.5)
    canvas.setFillColor(colors.HexColor(PETROL))
    canvas.drawRightString(
        breite - 15 * mm, y,
        f"Seite {doc.page}",
    )
    canvas.restoreState()

