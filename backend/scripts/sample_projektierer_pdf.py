#!/usr/bin/env python3
"""Erzeugt EIN minimal-realistisches Projektierer-Stakeholder-Sample-PDF ohne DB.

Zweck (Audit / Profil-Diagnose):
- Sichtprobe der ReportLab-Renderer-Pipeline fuer den Projektierer-Report
  ohne kompletten Engine-Lauf, ohne DB, ohne Auth.
- Keine echten Netzdaten, keine Kapazitaetsaussage, kein Audit-Eintrag in DB.

Aufruf (Repo-Root oder backend/):
  python backend/scripts/sample_projektierer_pdf.py
"""
from __future__ import annotations

import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[1]
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from engine.stakeholder_reports.pdf_builder import build_stakeholder_report_pdf
from engine.stakeholder_reports.projektierer import build_projektierer_report

OUTPUT_PATH = Path(
    r"C:\Users\andre\gridcheck\_audit\pdf_samples\projektierer_admin_sample.pdf"
)

PROJECT_NAME = "Solarpark Berlin Mitte"
PLZ = "10115"
ORT = "Berlin"
BUNDESLAND = "Berlin"
SCORE = 78
VERDICT = "B"
REVISION_HASH = "9f2a4c1e6d8b0237415a6c8d9e0f1122334455667788990011aabbccddeeff00"
GENERATED_AT = "2026-06-14T16:30:00+02:00"

WARNUNGEN = [
    "N-1-Reserve nur heuristisch eingeschaetzt; verbindliche Aussage erfordert verifizierte VNB-Daten.",
    "Trassenkorridor verlaeuft im Randbereich eines Schutzgebiets; Detailpruefung empfohlen.",
    "Bestehende Einspeisung im Umfeld nicht final bestaetigt - Kumulationseffekt moeglich.",
]

EMPFEHLUNGEN = [
    "Formelle Netzanschlussanfrage beim VNB stellen, um Sk'' und Restkapazitaet zu verifizieren.",
    "Zwei NVP-Varianten (20 kV, kuerzeste vs. risikoarme Trasse) parallel anfragen.",
    "Direktvermarktungs-/Bilanzkreisvertrag rechtzeitig vorbereiten (>= 100 kW AC).",
]

ANNAHMEN = [
    "cos phi = 0.95 (induktiv, MS-Standard)",
    "Gleichzeitigkeit = 1.00 (PV-Volleinspeisung)",
    "Leitungslaenge = 3.2 km, Annahme NA2XS2Y 240 mm^2",
    "Datenklasse C (modelliert / abgeleitet, oeffentliche Quellen)",
]

VARIANTEN = [
    "Variante A: 20-kV-Direktanschluss an naechstgelegene Schaltstation (~3.2 km, Trassenrisiko mittel).",
    "Variante B: 20-kV-Schleife ueber bestehenden Stationsstandort (~4.5 km, Trassenrisiko niedrig, BKZ hoeher).",
]

CONNECTION_VARIANTS = [
    {
        "label": "Variante A — Direktanschluss",
        "voltage_kv": 20.0,
        "voltage_label": "MS (20 kV)",
        "distance_km": 3.2,
        "confidence": "medium",
        "cost_risk": "medium",
        "route_risk": "medium",
        "comment": "Direktanschluss an Schaltstation Berlin-Mitte Nord.",
    },
    {
        "label": "Variante B — Stationsschleife",
        "voltage_kv": 20.0,
        "voltage_label": "MS (20 kV)",
        "distance_km": 4.5,
        "confidence": "medium",
        "cost_risk": "high",
        "route_risk": "low",
        "comment": "Schleife ueber bestehenden Stationsstandort, hoeherer BKZ.",
    },
]


def _build_engine_result() -> dict:
    return {
        "status": "OK",
        "scores": {
            "gesamt": SCORE,
            "voltage_match": 82,
            "distance": 70,
            "data_completeness": 65,
        },
        "fazit": {
            "entscheidung": VERDICT,
            "begruendung": "Vorpruefung positiv mit Auflagen (MS-Anschluss plausibel).",
            "text": "Anschluss vorlaeufig moeglich mit Auflagen; NVP-Variantenpruefung empfohlen.",
            "detail": "20-kV-MS-Anschluss am naechstgelegenen Schaltpunkt; N-1 nur heuristisch.",
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
            "antragsteller": "Admin (Audit-Sample, nicht abgerechnet)",
            "anlagentyp": "PV",
            "leistung_mw": 1.2,
            "nennspannung": 20,
            "anschlussart": "Einspeisung",
            "entfernung_km": 3.2,
            "leitungstyp": "NA2XS2Y240",
            "n1_datengrundlage": "planner_assumption",
            "cos_phi": 0.95,
            "project_location": {"latitude": 52.5320, "longitude": 13.3849},
        },
        "datenqualitaet": {
            "klasse": "C",
            "text": "Modellierte Annahmen (oeffentliche Quellen + Heuristik), keine VNB-verifizierten Werte.",
        },
        "n1": {
            "n1_klasse": "N1-1",
            "n1_sicher": False,
            "bewertung": "PRUEFEN",
            "detail_text": "Heuristisches N-1-Screening ohne verifizierte Topologie.",
            "topologie_text": "20-kV-Strang, Annahme einseitig versorgt.",
            "stufenbegruendung": "Stufe N1-1 (heuristisches Screening) wegen fehlender VNB-Daten.",
            "n1_konfidenz": 35,
        },
        "thermisch": {
            "bewertung": "OK",
            "text": "Thermische Auslastung der Annahmeleitung im plausiblen Band (~58%).",
        },
        "spannung": {
            "bewertung": "OK",
            "text": "Spannungsband eingehalten (dU ~ 1.4%).",
        },
        "kurzschluss": {
            "bewertung": "PRUEFEN",
            "text": "Sk'' aus oeffentlicher Quelle approximiert; bindende Aussage durch VNB ausstehend.",
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
        },
        "speicher_bewertung": {
            "summary": "Kein Speicher vorgesehen.",
        },
        "route_environment": {
            "summary": "Trassenfuehrung tangiert Randbereich Schutzgebiet; Detailpruefung empfohlen.",
            "risk_level": "mittel",
        },
        "stakeholder_bewertung": {
            "konflikt_summary": "Keine Anwohnerkonflikte gemeldet; Schutzgut Natur sensitiv.",
            "recommended_focus": "Trassen- und Naturschutzpruefung priorisieren.",
        },
        "transparenz": {
            "assumptions": ANNAHMEN,
            "confidence_notes": [
                "N-1-Aussage maximal N1-2 ohne verifizierte VNB-Daten.",
                "Score-Komponenten als Indikator, keine Kapazitaetsgarantie.",
                "Kostenband basiert auf BNetzA-Heuristik, +/- 30% plausibel.",
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
                "summary": "Anschluss MS plausibel; Detailprufung VNB erforderlich.",
            },
            "projektierer_perspective": {
                "plant_type": "pv_freiflaeche",
                "plant_type_label": "PV-Freiflaechenanlage",
                "ac_kw": 1200.0,
                "dc_kwp": 1380.0,
                "screening_power_kw": 1200.0,
                "feed_in_management_class": "direct_marketing",
                "cos_phi": 0.95,
                "simultaneity_factor": 1.0,
                "reactive_power_mode": "Q(U)",
                "delta_u_prozent": 1.4,
                "ik_referenz_ka": 12.5,
                "thermische_auslastung_prozent": 58,
                "querschnitt_mm2": 240,
                "n1_klasse": "N1-1",
                "n1_datengrundlage": "planner_assumption",
                "feed_in_profile_note": "Standardprofil PV ohne Curtailment-Annahme.",
                "process_timeline": {"estimated_total": "10-16 Wochen (heuristisch)"},
                "bkz_hint": {
                    "hint": "BKZ qualitativ mittlere Bandbreite (Standardlast/MS).",
                },
                "tab_disclaimer": {
                    "message": "TAB des zustaendigen VNB ist verbindlich; abweichende Anforderungen moeglich.",
                },
                "kumulation_warning": {
                    "message": "Kumulation mit benachbarter Einspeisung im 20-kV-Strang moeglich.",
                },
                "nvp_recommendation": {
                    "suggested_voltage_level": "MS",
                    "nearest_node_hint": "Schaltstation Berlin-Mitte Nord (~3.2 km)",
                    "disclaimer": "NVP-Hinweis heuristisch, finale Festlegung durch VNB.",
                },
            },
            "eeg_feed_in_screening": {
                "applicable": True,
                "feed_in_management_class": "direct_marketing",
                "hints": [
                    "Direktvermarktung erforderlich (>= 100 kW AC).",
                    "Fernsteuerbarkeit nach EEG 9 sicherstellen.",
                ],
            },
            "reactive_power_screening": {
                "applicable": True,
                "checklist": [
                    {"topic": "Q(U)-Kennlinie", "note": "TAB-Vorgaben des VNB beachten."},
                    {"topic": "cos phi-Bereich", "note": "Standard 0.95 ind/kap."},
                ],
            },
            "norm_references_applied": [
                {"reference": "VDE-AR-N 4110:2018-11"},
                {"reference": "DIN EN 60909"},
                {"reference": "EEG 9 (2023)"},
            ],
        },
    }


def _enrich_with_audit(report: dict) -> dict:
    """Setze Felder, die normalerweise vom Persistence-Layer ergaenzt werden,
    damit das Sample-PDF die Audit-Strip-Felder zeigt (Datum, Audit-Hash)."""
    report = dict(report)
    report["report_generated_at"] = GENERATED_AT
    report["audit_hash"] = REVISION_HASH
    report["report_revision_uuid"] = "00000000-0000-4000-8000-000000000001"
    return report


def main() -> int:
    engine_result = _build_engine_result()
    report = build_projektierer_report(engine_result)
    report = _enrich_with_audit(report)
    report["grid_calculation_v2"] = engine_result["grid_calculation_v2"]
    report["varianten"] = VARIANTEN

    pdf_bytes = build_stakeholder_report_pdf(report)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_bytes(pdf_bytes)

    print(f"WROTE: {OUTPUT_PATH}")
    print(f"BYTES: {len(pdf_bytes)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
