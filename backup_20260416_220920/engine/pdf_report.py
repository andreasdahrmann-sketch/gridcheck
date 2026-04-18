from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from datetime import datetime
import os
import hashlib
import json

def erstelle_pdf(daten, dateiname=None):
    """Erstellt revisionssicheren PDF-Report aus Analysedaten"""
    
    if not dateiname:
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        rev_id = daten.get('revision_id', 'unbekannt')
        dateiname = f'daten/reports/GridCheck_Report_{rev_id}_{ts}.pdf'
    
    os.makedirs(os.path.dirname(dateiname), exist_ok=True)
    
    doc = SimpleDocTemplate(dateiname, pagesize=A4,
                           topMargin=20*mm, bottomMargin=20*mm,
                           leftMargin=15*mm, rightMargin=15*mm)
    
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='TitelGC', fontSize=18, spaceAfter=6,
                              textColor=colors.HexColor('#00b4d8'), fontName='Helvetica-Bold'))
    styles.add(ParagraphStyle(name='SubGC', fontSize=10, spaceAfter=12,
                              textColor=colors.HexColor('#667788')))
    styles.add(ParagraphStyle(name='SektionGC', fontSize=13, spaceAfter=6, spaceBefore=14,
                              textColor=colors.HexColor('#00b4d8'), fontName='Helvetica-Bold',
                              borderWidth=1, borderColor=colors.HexColor('#1e3a5f'), borderPadding=4))
    styles.add(ParagraphStyle(name='FazitGC', fontSize=12, fontName='Helvetica-Bold',
                              spaceAfter=10, spaceBefore=6, alignment=1))
    styles.add(ParagraphStyle(name='EmpfehlungGC', fontSize=9, spaceAfter=4,
                              leftIndent=10, bulletIndent=0))
    
    elemente = []
    
    # Header
    elemente.append(Paragraph('GridCheck Pro - Analysereport', styles['TitelGC']))
    elemente.append(Paragraph(
        f'Erstellt: {datetime.now().strftime("%d.%m.%Y %H:%M:%S")} | '
        f'Revision: {daten.get("revision_id", "n/a")}',
        styles['SubGC']))
    elemente.append(Spacer(1, 4*mm))
    
    # Fazit
    fazit = daten.get('fazit', '')
    if 'MACHBAR' in fazit:
        fazit_farbe = colors.HexColor('#064e3b')
    elif 'AUFLAGEN' in fazit:
        fazit_farbe = colors.HexColor('#713f12')
    else:
        fazit_farbe = colors.HexColor('#7f1d1d')
    
    fazit_stil = ParagraphStyle('FazitDyn', parent=styles['FazitGC'], textColor=fazit_farbe)
    elemente.append(Paragraph(f'FAZIT: {fazit}', fazit_stil))
    elemente.append(Spacer(1, 4*mm))
    
    # Eingabedaten
    e = daten.get('eingabe', {})
    elemente.append(Paragraph('Anschlussparameter', styles['SektionGC']))
    tab_eingabe = [
        ['Parameter', 'Wert'],
        ['Spannungsebene', str(e.get('spannungsebene', ''))],
        ['Nennspannung', f"{e.get('nennspannung', '')} kV"],
        ['Leistung', f"{e.get('leistung_mw', '')} MW"],
        ['cos phi', str(e.get('cos_phi', ''))],
        ['Anschlussart', str(e.get('anschlussart', ''))],
        ['Entfernung', f"{e.get('entfernung_km', '')} km"],
        ['Leitungstyp', str(e.get('leitungstyp', ''))],
        ['Parallele Systeme', str(e.get('parallele_systeme', ''))],
    ]
    elemente.append(_tabelle(tab_eingabe))
    
    # Thermische Analyse
    th = daten.get('thermisch', {})
    elemente.append(Paragraph('Thermische Analyse', styles['SektionGC']))
    tab_th = [
        ['Parameter', 'Wert'],
        ['Betriebsstrom', f"{th.get('i_pro_system_a', '')} A"],
        ['Grenzstrom', f"{th.get('i_max_a', '')} A"],
        ['Auslastung', f"{th.get('auslastung_prozent', '')} %"],
        ['Status', str(th.get('bewertung', ''))],
    ]
    elemente.append(_tabelle(tab_th))
    
    # Spannungsanalyse
    sp = daten.get('spannung', {})
    elemente.append(Paragraph('Spannungsanalyse', styles['SektionGC']))
    tab_sp = [
        ['Parameter', 'Wert'],
        ['Delta U', f"{sp.get('delta_u_prozent', '')} %"],
        ['Grenzwert', f"{sp.get('grenzwert_prozent', '')} %"],
        ['Status', str(sp.get('bewertung', ''))],
    ]
    elemente.append(_tabelle(tab_sp))
    
    # N-1 Analyse
    n1 = daten.get('n1', {})
    elemente.append(Paragraph('N-1 Sicherheit', styles['SektionGC']))
    tab_n1 = [
        ['Parameter', 'Wert'],
        ['N-1 sicher', 'JA' if n1.get('n1_sicher') else 'NEIN'],
        ['Auslastung bei N-1', f"{n1.get('n1_auslastung_prozent', '')} %"],
        ['Bewertung', str(n1.get('bewertung', ''))],
    ]
    elemente.append(_tabelle(tab_n1))
    
    # KI-Bewertung
    ki = daten.get('ki_bewertung', {})
    if ki:
        elemente.append(Paragraph('KI-Bewertung', styles['SektionGC']))
        tab_ki = [
            ['Parameter', 'Wert'],
            ['Konfidenz', f"{ki.get('konfidenz', '')} %"],
            ['Einschaetzung', str(ki.get('einschaetzung', ''))],
        ]
        elemente.append(_tabelle(tab_ki))
    
    # Empfehlungen
    empf = daten.get('empfehlungen', [])
    if empf:
        elemente.append(Paragraph('Empfehlungen', styles['SektionGC']))
        for em in empf:
            elemente.append(Paragraph(f'\u2022 {em}', styles['EmpfehlungGC']))
    
    elemente.append(Spacer(1, 10*mm))
    
    # Revisions-Hash
    hash_input = json.dumps(daten, sort_keys=True, default=str)
    rev_hash = hashlib.sha256(hash_input.encode()).hexdigest()[:16]
    elemente.append(Paragraph(
        f'Revisions-Hash: {rev_hash} | Dokument maschinell erstellt - GridCheck Pro v1.0',
        styles['SubGC']))
    
    doc.build(elemente)
    return dateiname, rev_hash


def _tabelle(daten_liste):
    """Erstellt formatierte Tabelle"""
    t = Table(daten_liste, colWidths=[70*mm, 90*mm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0d1b2a')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#00b4d8')),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#0a0f1e')),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#e0e0e0')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#1e3a5f')),
        ('PADDING', (0, 0), (-1, -1), 6),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#0a0f1e'), colors.HexColor('#111827')]),
    ]))
    return t
