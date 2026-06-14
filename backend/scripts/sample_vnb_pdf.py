#!/usr/bin/env python3
"""Erzeugt EIN minimal-realistisches VNB-Stakeholder-Sample-PDF ohne DB.

Zweck (Audit / Bypass-Diagnose):
- Sichtprobe der ReportLab-Renderer-Pipeline ohne kompletten Engine-Lauf.
- Keine echten Netzdaten, keine Kapazitaetsaussage, kein Audit-Eintrag.

Aufruf (Repo-Root oder backend/):
  python backend/scripts/sample_vnb_pdf.py
"""
from __future__ import annotations

import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[1]
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from engine.stakeholder_reports.pdf_builder import build_stakeholder_report_pdf
from engine.stakeholder_reports.vnb import build_vnb_report

OUTPUT_PATH = Path(r"C:\Users\andre\gridcheck\_audit\pdf_samples\vnb_admin_sample.pdf")

PROJECT_NAME = "Admin Testprojekt PV 1.2 MW"
PLZ = "10115"
ORT = "Berlin"
BUNDESLAND = "Berlin"
SCORE = 78
VERDICT = "B"
REVISION_HASH = "a1b2c3d4e5f6071829304a5b6c7d8e9f0011223344556677889900aabbccddee"
GENERATED_AT = "2026-06-14T16:00:00+02:00"

CONNECTION_VARIANTS = [
    {
        "label": "Variante A — Direktanschluss",
        "voltage_kv": 20.0,
        "voltage_label": "MS (20 kV)",
        "distance_km": 3.2,
        "confidence": "medium",
        "cost_risk": "medium",
        "route_risk": "medium",
        "comment": "Anschluss an Schaltstation Berlin-Mitte Nord (heuristisch).",
    },
    {
        "label": "Variante B — Stationsschleife",
        "voltage_kv": 20.0,
        "voltage_label": "MS (20 kV)",
        "distance_km": 4.5,
        "confidence": "medium",
        "cost_risk": "high",
        "route_risk": "low",
        "comment": "Schleife ueber bestehende Station, hoeherer BKZ.",
    },
]

WARNUNGEN = [
    "N-1-Reserve nur heuristisch eingeschaetzt; verbindliche Aussage erfordert verifizierte Netzbetreiberdaten.",
    "Trafo-Restkapazitaet nicht durch DSO bestaetigt; Annahme aus oeffentlichen Quellen.",
    "Trassenlaenge ueberschneidet potenziell schutzbeduerftiges Gebiet (Schnellscreening, kein Genehmigungsersatz).",
]

EMPFEHLUNGEN = [
    "Formelle Netzanschlussanfrage beim zustaendigen VNB einreichen, um Sk'' und Restkapazitaet zu verifizieren.",
    "Detailpruefung der NVP-Optionen am 20-kV-Anschlusspunkt durch Trassenstudie ergaenzen.",
    "Speicherbetriebsmodus mit VNB-TAB abstimmen (Q-Bereitstellung, Schwarzstartfaehigkeit ausgeschlossen).",
]

ANNAHMEN = [
    "cos phi = 0.95",
    "Gleichzeitigkeit = 1.00 (PV-Volleinspeisung)",
    "Leitungslaenge = 4.0 km, NA2XS2Y 240",
    "Datenklasse C (modelliert / abgeleitet)",
]


def _build_engine_result() -> dict:
    return {
        "status": "OK",
        "scores": {"gesamt": SCORE, "voltage_match": 82, "distance": 70, "data_completeness": 60},
        "fazit": {
            "entscheidung": VERDICT,
            "begruendung": "Vorpruefung positiv mit Auflagen.",
            "text": "Anschluss vorlaeufig moeglich mit Auflagen; verifizierte VNB-Daten ausstehend.",
            "detail": "20-kV-MS-Anschluss plausibel; Sk''-/Trafo-Restkapazitaet noch nicht verifiziert.",
        },
        "warnungen": WARNUNGEN,
        "empfehlungen": EMPFEHLUNGEN,
        "annahmen": ANNAHMEN,
        "revision": {"hash": REVISION_HASH, "timestamp": GENERATED_AT},
        "eingabe": {
            "standort": PROJECT_NAME,
            "ort": ORT,
            "plz": PLZ,
            "bundesland": BUNDESLAND,
            "antragsteller": "Admin (Testlauf, nicht abgerechnet)",
            "anlagentyp": "PV",
            "leistung_mw": 1.2,
            "nennspannung": 20,
            "anschlussart": "Einspeisung",
            "entfernung_km": 4.0,
            "leitungstyp": "NA2XS2Y240",
            "n1_datengrundlage": "planner_assumption",
            "cos_phi": 0.95,
            "project_location": {"latitude": 52.5320, "longitude": 13.3849},
        },
        "datenqualitaet": {
            "klasse": "C",
            "text": "Modellierte Annahmen (oeffentliche Quellen + Heuristik), keine DSO-verifizierten Werte.",
        },
        "n1": {
            "n1_klasse": "N1-1",
            "n1_sicher": False,
            "bewertung": "PRUEFEN",
            "detail_text": "Heuristisches N-1-Screening ohne verifizierte Topologie.",
            "topologie_text": "20-kV-Strang, Annahme einseitig versorgt.",
            "stufenbegruendung": "Stufe N1-1 (heuristisches Screening) wegen fehlender DSO-Daten.",
        },
        "thermisch": {
            "bewertung": "OK",
            "text": "Thermische Auslastung der Annahmeleitung im plausiblen Band (~62%).",
        },
        "spannung": {
            "bewertung": "OK",
            "text": "Spannungsband eingehalten (dU ~ 1.6%).",
        },
        "kurzschluss": {
            "bewertung": "PRUEFEN",
            "text": "Sk'' aus oeffentlicher Quelle approximiert; bindende Aussage durch VNB ausstehend.",
            "rw_text": "Rueckwirkungen plausibel, formale Pruefung beim VNB erforderlich.",
        },
        "kosten": {
            "band_niedrig_eur": 350000,
            "band_basis_eur": 480000,
            "band_hoch_eur": 720000,
            "kosten_trasse_eur": 220000,
            "kosten_station_eur": 180000,
            "kosten_planung_eur": 60000,
            "kosten_genehmigung_eur": 40000,
            "konfidenz_prozent": 55,
            "hauptrisikotreiber": ["Trassenlaenge", "Schutzgebietsnaehe", "BKZ-Indikation"],
            "quelle": "BNetzA-Heuristik (oeffentlich)",
        },
        "connection_variants": CONNECTION_VARIANTS,
        "projektprofil": {
            "summary": "PV-Erzeugungsanlage, MS-Anschluss, Speicher als Eigennutzungs-Puffer.",
        },
        "speicher_bewertung": {
            "summary": "Kleiner Puffer (0.4 MWh), keine Netzdienstleistungen avisiert.",
        },
        "route_environment": {
            "summary": "Trassenfuehrung ueberlagert Randbereich Schutzgebiet; Detailpruefung empfohlen.",
        },
        "stakeholder_bewertung": {
            "konflikt_summary": "Keine Anwohnerkonflikte gemeldet; Schutzgut Natur sensitiv.",
            "recommended_focus": "Trassen- und Naturschutzpruefung priorisieren.",
        },
        "transparenz": {
            "confidence_notes": [
                "N-1-Aussage maximal N1-2 ohne verifizierte DSO-Daten.",
                "Score-Komponenten als Indikator, keine Kapazitaetsgarantie.",
            ],
            "disclaimers": [
                "Vorlaeufige Diagnose, keine Netzanschlusszusage.",
                "Freie Netzkapazitaet nur durch zustaendigen VNB feststellbar.",
            ],
        },
    }


def main() -> int:
    engine_result = _build_engine_result()
    report = build_vnb_report(engine_result)

    pdf_bytes = build_stakeholder_report_pdf(report)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_bytes(pdf_bytes)

    print(f"WROTE: {OUTPUT_PATH}")
    print(f"BYTES: {len(pdf_bytes)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
