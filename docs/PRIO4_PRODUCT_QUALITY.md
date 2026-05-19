# PRIO 4 — Produkt-Qualität (Status)

**Stand:** 2026-05-19

| # | Aufgabe | Status | Dateien (Auszug) | Späteres Projekt |
|---|---------|--------|------------------|------------------|
| 1 | GIS/Netzdaten-Pipeline | **PARTIAL** | `docs/DATA_SOURCE_PIPELINE.md`, `docs/OSM_FETCH_STUB.md`, `backend/tests/test_data_source_pipeline.py` | OSM-Worker, PostGIS-Import, Ops-Endpoint `/api/v1/ops/data-sources` |
| 2 | Szenarienvergleich UI | **PARTIAL** | `frontend/app/projects/[id]/szenarien-vergleich/page.tsx`, `frontend/components/projects/ScenarioComparePanel.tsx`, `frontend/lib/scenario-compare-snapshots.ts`, `docs/SCENARIO_COMPARE.md` | Server-Run-History, User-Revision-API, Was-wäre-wenn |
| 3 | KI produktiv trainieren | **PARTIAL** | `docs/KI_TRAINING.md`, `backend/scripts/export_ki_feedback_dataset.py`, `backend/Makefile` | Echtes ML (Phase 2–4 in KI_TRAINING), GPU-Pipeline, Feature-Flag |
| 4 | Penetrationstest | **DONE** (Vorbereitung) | `docs/SECURITY_PENTEST_CHECKLIST.md` | Externer Pentest + Retest + Fix-Sprint |

## Legende

- **DONE** — Lieferziel für diese PRIO erfüllt (Doku oder MVP-Slice).
- **PARTIAL** — Fundament / MVP; Vollfeature braucht separates Epic.
- **BLOCKED** — Abhängigkeit fehlt (hier nicht verwendet).
