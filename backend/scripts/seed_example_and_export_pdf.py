#!/usr/bin/env python3
"""
Beispieldaten (Demo-Szenarien) in die DB laden und Stakeholder-PDFs erzeugen.

Ausfuehrung (Repo-Root oder backend/):
  python backend/scripts/seed_example_and_export_pdf.py
  python backend/scripts/seed_example_and_export_pdf.py --skip-db
  python backend/scripts/seed_example_and_export_pdf.py --output-dir reports

Keine Kapazitaetsgarantien — nutzt dieselben Demo-Payloads wie tests/test_demo_scenarios.py.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# backend/ auf sys.path (Skript liegt unter backend/scripts/)
_BACKEND = Path(__file__).resolve().parents[1]
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from engine.revision import speichere_revision
from engine.stakeholder_reports.invest import build_invest_report
from engine.stakeholder_reports.pdf_builder import build_stakeholder_report_pdf
from engine.stakeholder_reports.projektierer import build_projektierer_report
from engine.stakeholder_reports.vnb import build_vnb_report
from services.v1_analysis_service import run_v1_analysis

DEMO_SEED_EMAIL = "demo.seed@gridcheck.example"
DEMO_SEED_PASSWORD = "DemoSeed2026!"

# Abgestimmt mit frontend/components/DemoCaseLoader.tsx und tests/test_demo_scenarios.py
EXAMPLE_SCENARIOS: list[dict[str, Any]] = [
    {
        "id": "demo-pv-ms-auflagen",
        "label": "PV 5 MW / MS – vorläufig C (Screening)",
        "project": {
            "name": "[Demo] PV 5 MW Leipzig",
            "plz": "04109",
            "ort": "Leipzig",
            "typ": "solar",
            "leistung_kw": 5000.0,
            "description": "Freiflaechen-PV; Demo ohne verifizierte Netzbetreiberdaten.",
        },
        "engine_input": {
            "anlagentyp": "PV",
            "p_kw": 5000,
            "leistung_mw": 5.0,
            "plz": "04109",
            "ort": "Leipzig",
            "anschlussart": "Einspeisung",
            "cos_phi": 0.95,
            "nennspannung": 20,
            "entfernung_km": 2.0,
            "leitungstyp": "NA2XS2Y240",
            "parallele_systeme": 2,
            "topologie": "ring_offen",
            "redundanz": True,
            "trafo_s_mva": 25.0,
            "sk_mva": 250.0,
            "restkapazitaet_ms_mva": 10.0,
        },
    },
    {
        "id": "demo-bess-grenzwertig",
        "label": "BESS 10 MW / MS – vorläufig C (Trafo)",
        "project": {
            "name": "[Demo] BESS 10 MW Hannover",
            "plz": "30159",
            "ort": "Hannover",
            "typ": "batterie",
            "leistung_kw": 10000.0,
            "description": "Grosser Speicher; Demo-Szenario Trafo-Engpass.",
        },
        "engine_input": {
            "anlagentyp": "BESS",
            "p_kw": 10000,
            "leistung_mw": 10.0,
            "plz": "30159",
            "ort": "Hannover",
            "anschlussart": "Speicher",
            "cos_phi": 0.95,
            "nennspannung": 20,
            "entfernung_km": 3.0,
            "leitungstyp": "NA2XS2Y240",
            "topologie": "ring_offen",
            "redundanz": True,
            "sk_mva": 250.0,
            "restkapazitaet_ms_mva": 8.0,
            "umspannwerk": {
                "trafos": [
                    {"sn_mva": 10.0, "belastung_aktuell_mw": 9.0},
                    {"sn_mva": 10.0, "belastung_aktuell_mw": 9.0},
                ],
            },
        },
    },
    {
        "id": "demo-nogo-thermik",
        "label": "PV 250 kW / NS – vorläufig C (Thermik)",
        "project": {
            "name": "[Demo] PV 250 kW Dortmund",
            "plz": "44137",
            "ort": "Dortmund",
            "typ": "solar",
            "leistung_kw": 250.0,
            "description": "NS-Stich mit thermischem Engpass; Demo No-Go.",
        },
        "engine_input": {
            "anlagentyp": "PV",
            "p_kw": 250,
            "leistung_mw": 0.25,
            "plz": "44137",
            "ort": "Dortmund",
            "anschlussart": "Einspeisung",
            "cos_phi": 0.95,
            "nennspannung": 0.4,
            "entfernung_km": 0.3,
            "leitungstyp": "NAYY150",
            "topologie": "stich",
            "redundanz": False,
        },
    },
]


def _run_scenario(scenario: dict[str, Any]) -> dict[str, Any]:
    result = run_v1_analysis(dict(scenario["engine_input"]))
    if result.get("status") == "FEHLER":
        raise RuntimeError(
            f"{scenario['id']}: Berechnung fehlgeschlagen: {result.get('fehler', result)}"
        )
    revision = speichere_revision(result, engine_version="seed-example-data")
    result["revision"] = {"hash": revision["hash"]}
    return result


def _write_pdf(report: dict[str, Any], path: Path) -> int:
    pdf_bytes = build_stakeholder_report_pdf(report)
    if not pdf_bytes.startswith(b"%PDF"):
        raise RuntimeError(f"Kein gueltiges PDF fuer {path.name}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(pdf_bytes)
    return len(pdf_bytes)


def _seed_database(scenarios: list[dict[str, Any]], results: list[dict[str, Any]]) -> dict[str, Any]:
    from sqlalchemy.orm import Session

    from db.database import SessionLocal
    from db.models import User
    from services.auth_service import register_user
    from services.billing_service import persist_completed_analysis_run
    from services.project_service import create_project

    db: Session = SessionLocal()
    summary: dict[str, Any] = {"email": DEMO_SEED_EMAIL, "projects": [], "analysis_run_ids": []}
    try:
        user = db.query(User).filter(User.email == DEMO_SEED_EMAIL).first()
        if user is None:
            user = register_user(
                db,
                email=DEMO_SEED_EMAIL,
                password=DEMO_SEED_PASSWORD,
                role="projektierer",
                full_name="Demo Seed Nutzer",
            )
            print(f"[DB] Nutzer angelegt: {DEMO_SEED_EMAIL}")
        else:
            print(f"[DB] Nutzer vorhanden: {DEMO_SEED_EMAIL} (id={user.id})")

        for scenario, result in zip(scenarios, results, strict=True):
            meta = scenario["project"]
            project = create_project(
                db,
                user,
                name=meta["name"],
                plz=meta["plz"],
                typ=meta["typ"],
                leistung_kw=float(meta["leistung_kw"]),
                description=meta.get("description"),
            )
            request_payload = dict(scenario["engine_input"])
            request_payload["project_id"] = project.id
            run = persist_completed_analysis_run(
                db,
                user,
                request_payload=request_payload,
                result_payload=result,
                source="seed_example",
                project_id=project.id,
            )
            summary["projects"].append(
                {
                    "id": project.id,
                    "name": project.name,
                    "scenario_id": scenario["id"],
                    "entscheidung": (result.get("fazit") or {}).get("entscheidung"),
                }
            )
            summary["analysis_run_ids"].append(run.id)
            print(
                f"[DB] Projekt {project.id} + Analyse-Lauf {run.id} "
                f"({scenario['id']}, Entscheidung={(result.get('fazit') or {}).get('entscheidung')})"
            )
        return summary
    finally:
        db.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Demo-Daten seeden und PDF-Reports erzeugen.")
    parser.add_argument(
        "--output-dir",
        default="reports",
        help="Zielordner fuer PDFs (relativ zum Repo-Root, Default: reports)",
    )
    parser.add_argument(
        "--skip-db",
        action="store_true",
        help="Nur PDFs erzeugen, keine Datenbank befuellen",
    )
    parser.add_argument(
        "--primary-id",
        default="demo-pv-ms-auflagen",
        help="Szenario-ID fuer example-gridcheck-report.pdf",
    )
    args = parser.parse_args()

    repo_root = _BACKEND.parent
    out_dir = Path(args.output_dir)
    if not out_dir.is_absolute():
        out_dir = repo_root / out_dir

    results: list[dict[str, Any]] = []
    pdf_paths: list[Path] = []

    print("=== GridCheck Beispieldaten + PDF ===")
    stakeholder_builders: dict[str, Any] = {
        "projektierer": build_projektierer_report,
        "vnb": build_vnb_report,
        "invest": build_invest_report,
    }
    for scenario in EXAMPLE_SCENARIOS:
        print(f"[Analyse] {scenario['id']} …")
        result = _run_scenario(scenario)
        results.append(result)
        entscheidung = (result.get("fazit") or {}).get("entscheidung", "?")
        for stakeholder, builder in stakeholder_builders.items():
            report = builder(result)
            pdf_name = f"gridcheck-{stakeholder}-{scenario['id']}.pdf"
            size = _write_pdf(report, out_dir / pdf_name)
            if stakeholder == "projektierer":
                pdf_paths.append(out_dir / pdf_name)
            print(
                f"[PDF/{stakeholder}] {out_dir / pdf_name} "
                f"({size} bytes, Entscheidung={entscheidung})"
            )

    primary = next((s for s in EXAMPLE_SCENARIOS if s["id"] == args.primary_id), EXAMPLE_SCENARIOS[0])
    primary_idx = EXAMPLE_SCENARIOS.index(primary)
    primary_path = out_dir / "example-gridcheck-report.pdf"
    primary_path.write_bytes(
        (out_dir / f"gridcheck-projektierer-{primary['id']}.pdf").read_bytes()
    )
    print(f"[PDF] Hauptreport: {primary_path}")

    manifest = {
        "scenarios": [
            {
                "id": s["id"],
                "label": s["label"],
                "pdfs": {
                    stakeholder: str(out_dir / f"gridcheck-{stakeholder}-{s['id']}.pdf")
                    for stakeholder in ("projektierer", "vnb", "invest")
                },
                "entscheidung": (results[i].get("fazit") or {}).get("entscheidung"),
                "revision_hash": (results[i].get("revision") or {}).get("hash"),
            }
            for i, s in enumerate(EXAMPLE_SCENARIOS)
        ],
        "primary_pdf": str(primary_path),
    }

    if not args.skip_db:
        try:
            db_summary = _seed_database(EXAMPLE_SCENARIOS, results)
            manifest["database"] = db_summary
            manifest["login"] = {
                "email": DEMO_SEED_EMAIL,
                "password_hint": "Siehe Skript DEMO_SEED_PASSWORD (nur lokal/Dev)",
            }
        except Exception as exc:
            print(f"[WARN] DB-Seed fehlgeschlagen: {exc}", file=sys.stderr)
            print("[WARN] PDFs wurden trotzdem erzeugt. Postgres + alembic pruefen.", file=sys.stderr)
    else:
        print("[SKIP] Datenbank-Seed (--skip-db)")

    manifest_path = out_dir / "example-seed-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[OK] Manifest: {manifest_path}")
    print(f"\nOeffnen: {primary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
