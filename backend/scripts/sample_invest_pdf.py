#!/usr/bin/env python3
"""Erzeugt EIN minimal-realistisches Invest-Stakeholder-Sample-PDF ohne DB.

Zweck (Audit / Profil-Diagnose):
- Sichtprobe der ReportLab-Renderer-Pipeline fuer den Invest-Report
  ohne kompletten Engine-Lauf, ohne DB, ohne Auth.
- Keine echten Netzdaten, keine Kapazitaetsaussage, kein Audit-Eintrag in DB.

Aufruf (Repo-Root oder backend/):
  python backend/scripts/sample_invest_pdf.py
"""
from __future__ import annotations

import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[1]
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from engine.stakeholder_reports.invest import build_invest_report
from engine.stakeholder_reports.pdf_builder import build_stakeholder_report_pdf

OUTPUT_PATH = Path(
    r"C:\Users\andre\gridcheck\_audit\pdf_samples\invest_admin_sample.pdf"
)

PROJECT_NAME = "Solarpark Berlin Mitte"
PLZ = "10115"
ORT = "Berlin"
BUNDESLAND = "Berlin"
SCORE = 68
VERDICT = "B"
REVISION_HASH = "8e2a4c1e6d8b0237415a6c8d9e0f1122334455667788990011aabbccddeeff00"
GENERATED_AT = "2026-06-14T17:00:00+02:00"

CONNECTION_VARIANTS = [
    {
        "label": "Variante A — Direktanschluss",
        "voltage_kv": 20.0,
        "voltage_label": "MS (20 kV)",
        "distance_km": 3.2,
        "confidence": "medium",
        "cost_risk": "medium",
        "route_risk": "medium",
        "comment": "Direktanschluss an Schaltstation, BKZ-Indikation moderat.",
    },
]


def _build_engine_result() -> dict:
    return {
        "status": "OK",
        "scores": {
            "gesamt": SCORE,
            "voltage_match": 75,
            "distance": 60,
            "data_completeness": 55,
        },
        "fazit": {
            "entscheidung": VERDICT,
            "begruendung": "Investitions-Sicht: positiv mit Watchpoints.",
            "text": "Risiko-/Kostenprofil im akzeptablen Band; DD kann fortgesetzt werden.",
            "detail": "Hauptwatchpoints: Trassenlaenge, BKZ und Genehmigungsstand.",
        },
        "warnungen": [
            "N-1-Reserve heuristisch; verbindliche Aussage steht aus.",
            "Trasse nahe Schutzgebiet, Genehmigungsrisiko erhoehen.",
            "Bestehende Einspeisung im Umfeld nicht final bestaetigt.",
        ],
        "empfehlungen": [
            "Netzanschlussanfrage beim VNB initiieren; Sk''-/Trafo-Restkapazitaet verifizieren.",
            "Trassen-DD mit Umweltverband fruehzeitig abstimmen.",
            "Genehmigungspfad und Foerderfenster (EEG/Direktvermarktung) parallel sichern.",
        ],
        "annahmen": [
            "cos phi = 0.95",
            "Gleichzeitigkeit = 1.00",
            "Leitungslaenge = 3.2 km, Annahme NA2XS2Y 240",
            "Datenklasse C (modelliert)",
        ],
        "revision": {"hash": REVISION_HASH, "timestamp": GENERATED_AT},
        "eingabe": {
            "standort": PROJECT_NAME,
            "ort": ORT,
            "plz": PLZ,
            "bundesland": BUNDESLAND,
            "antragsteller": "Admin (Audit-Sample, nicht abgerechnet)",
            "anlagentyp": "PV",
            "leistung_mw": 1.2,
            "nennspannung": 20,
            "anschlussart": "Einspeisung",
            "entfernung_km": 3.2,
            "leitungstyp": "NA2XS2Y240",
            "n1_datengrundlage": "planner_assumption",
            "cos_phi": 0.95,
            "projektreife": "planung",
            "baugenehmigung_vorhanden": False,
            "project_location": {"latitude": 52.5320, "longitude": 13.3849},
        },
        "datenqualitaet": {
            "klasse": "C",
            "text": "Modellierte Annahmen, keine VNB-verifizierten Werte.",
        },
        "n1": {
            "n1_klasse": "N1-1",
            "n1_sicher": False,
            "bewertung": "PRUEFEN",
            "detail_text": "Heuristisches N-1-Screening ohne verifizierte Topologie.",
            "topologie_text": "20-kV-Strang, Annahme einseitig versorgt.",
            "stufenbegruendung": "Stufe N1-1 wegen fehlender VNB-Daten.",
            "n1_konfidenz": 35,
        },
        "thermisch": {"bewertung": "OK", "text": "Thermische Auslastung im plausiblen Band (~58%)."},
        "spannung": {"bewertung": "OK", "text": "Spannungsband eingehalten (dU ~ 1.4%)."},
        "kurzschluss": {"bewertung": "PRUEFEN", "text": "Sk'' approximiert, VNB-Aussage offen."},
        "kosten": {
            "band_niedrig_eur": 350000,
            "band_basis_eur": 480000,
            "band_hoch_eur": 720000,
            "investition_gesamt_eur": 480000,
            "kosten_trasse_eur": 220000,
            "kosten_station_eur": 180000,
            "kosten_planung_eur": 60000,
            "kosten_genehmigung_eur": 40000,
            "konfidenz_prozent": 55,
            "quelle": "BNetzA-Heuristik (oeffentlich)",
            "band_annahmen": [
                "Bandbreite statt Punktwert.",
                "Indexierung 2026 ohne Tagesvolatilitaet.",
            ],
            "hauptrisikotreiber": [
                "Trassenlaenge",
                "Schutzgebietsnaehe",
                "BKZ-Indikation",
            ],
        },
        "connection_variants": CONNECTION_VARIANTS,
        "projektprofil": {
            "summary": "PV-Erzeugungsanlage 1.2 MW, MS-Anschluss, kein Speicher.",
            "max_export_kw": 1200.0,
            "total_installed_kw": 1200.0,
            "is_hybrid": False,
            "component_count": 1,
        },
        "speicher_bewertung": {"summary": "Kein Speicher vorgesehen."},
        "route_environment": {
            "summary": "Trasse tangiert Schutzgebiet; Detailpruefung empfohlen.",
            "risk_level": "mittel",
        },
        "stakeholder_bewertung": {
            "konflikt_summary": "Keine Anwohnerkonflikte; Schutzgut Natur sensitiv.",
            "recommended_focus": "Trassen- und Naturschutzpruefung priorisieren.",
            "netzbetreiber_score": 60.0,
            "projektierer_score": 70.0,
            "umsetzung_score": 55.0,
            "konflikt_level": "mittel",
        },
        "transparenz": {
            "assumptions": [
                "Bandbreite statt Punktwert.",
                "Datenklasse C — vorlaeufige Annahme.",
            ],
            "confidence_notes": [
                "Score-Komponenten als Indikator, keine Kapazitaetsgarantie.",
                "Worst/Best als transparenter Stress-Spread.",
            ],
            "disclaimers": [
                "Vorlaeufige Diagnose, keine Netzanschlusszusage.",
                "Freie Netzkapazitaet nur durch zustaendigen VNB feststellbar.",
            ],
        },
        "grid_calculation_v2": {
            "calculation_version": "grid_calc_v2-2026.06",
            "feasibility": {
                "status": "ok_with_conditions",
                "summary": "Anschluss MS plausibel; Detailpruefung erforderlich.",
            },
            "projektierer_perspective": {
                "plant_type": "pv_freiflaeche",
                "plant_type_label": "PV-Freiflaechenanlage",
                "ac_kw": 1200.0,
                "process_timeline": {"estimated_total": "10-16 Wochen (heuristisch)"},
                "nvp_recommendation": {
                    "suggested_voltage_level": "MS",
                    "nearest_node_hint": "Schaltstation Berlin-Mitte Nord (~3.2 km)",
                    "disclaimer": "NVP-Hinweis heuristisch, finale Festlegung durch VNB.",
                },
            },
        },
    }


def _enrich_with_audit(report: dict) -> dict:
    report = dict(report)
    report["report_generated_at"] = GENERATED_AT
    report["audit_hash"] = REVISION_HASH
    report["report_revision_uuid"] = "00000000-0000-4000-8000-000000000002"
    return report


def main() -> int:
    engine_result = _build_engine_result()
    report = build_invest_report(engine_result)
    report = _enrich_with_audit(report)

    pdf_bytes = build_stakeholder_report_pdf(report)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_bytes(pdf_bytes)

    print(f"WROTE: {OUTPUT_PATH}")
    print(f"BYTES: {len(pdf_bytes)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
