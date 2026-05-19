# Datenquellen-Pipeline (MaStR, SMARD, DWD, OSM-Plan)

**Stand:** 2026-05-19

## Status

| Quelle | Skript | Tests | Prod-Import | Datenklasse |
|--------|--------|-------|-------------|-------------|
| MaStR | `run_data_source_pipeline(["mastr"])` | `test_data_source_pipeline.py` | Nur mit `MASTR_EXPORT_URL` | A |
| SMARD | `["smard"]` | ja | API via `provider_smard` | A |
| DWD | `["dwd"]` | ja | Nur mit `DWD_SOURCE_URL` | A |
| OSM | — | — | **Nicht** in diesem Skript | B (nur Geometrie/Assets) |

**Fazit:** Pipeline ist **funktional als Snapshot-/Hash-Framework**, liefert ohne ENV oft `NOT_CONFIGURED`. Kein vollautomatischer GIS-/OSM-Import. **Keine Kapazitätsaussagen** aus öffentlichen Quellen ohne NB-Verifikation.

## Ingestion-Checkliste (jede Quelle)

Vor Freigabe eines Imports in Staging/Prod:

- [ ] **Herkunft** dokumentiert (`herkunft_url`, Lizenztext)
- [ ] **Rohdaten** gehasht (`raw_hash`), append-only Snapshot in `daten/datenquellen_snapshots.jsonl`
- [ ] **Normalisiert** gehasht (`normalized_hash`), Schema versioniert (`parser_version`)
- [ ] **Confidence** gesetzt (gesamt + technisch + geometrisch + kommerziell, 0–100)
- [ ] **Validierungsstatus** gesetzt (`OK` | `PARTIAL` | `NOT_CONFIGURED` | `ERROR`)
- [ ] **Datenklasse** A–E zugewiesen (siehe Projektregeln)
- [ ] **Kein** Feld `freie_kapazitaet` / „verfügbar“ ohne DSO-Quelle (Klasse D)
- [ ] Stichprobe: `record_count` plausibel, Fehlerfall getestet (Timeout, 404)
- [ ] OSM separat: [OSM_FETCH_STUB.md](./OSM_FETCH_STUB.md)

## Confidence-Felder (Kanonical)

Implementierung: `DataSourceSnapshot` in `backend/services/data_source_pipeline.py`.

| Feld | Bedeutung |
|------|-----------|
| `confidence_score` | Gesamtvertrauen für diese Snapshot-Zeile |
| `confidence_technisch` | Vollständigkeit/Qualität fachlicher Attribute |
| `confidence_geometrisch` | Lage/Geometrie (bei SMARD oft N/A → moderat) |
| `confidence_kommerziell` | Nutzbarkeit für Kosten-/Marktindikatoren |
| `validierungsstatus` | Verarbeitungszustand, nicht „Netz OK“ |
| `hinweis` | z. B. Fallback, ENV fehlt, Fehlerklasse |

**SMARD-Fallback:** bei nicht erreichbarer API → `PARTIAL`, niedrige Confidence, expliziter `hinweis`.

## Ausfuehren

```powershell
cd backend
.\.venv\Scripts\python.exe scripts\run_data_source_pipeline.py
```

Alternativ (Makefile):

```powershell
cd backend
make data-pipeline
```

Ausgabe: eine Zeile pro Quelle mit `validierungsstatus`, `record_count`, Hash-Prefix.

Snapshots: `backend/daten/datenquellen_snapshots.jsonl` (append-only).

## ENV (optional)

| Variable | Quelle |
|----------|--------|
| `MASTR_EXPORT_URL` | Marktstammdatenregister-Export |
| `DWD_SOURCE_URL` | DWD CDC |
| `OSM_OVERPASS_URL` | (geplant) siehe OSM-Stub |

## Pipeline-Status (Betrieb, ohne neues API)

| Prüfung | Befehl / Ort |
|---------|----------------|
| Letzte Snapshots | `Get-Content backend\daten\datenquellen_snapshots.jsonl -Tail 5` |
| Letzter Lauf | Konsolen-Output des Skripts |
| API erreichbar | `GET /health` auf Backend (Deploy-Version) |
| Vollständiger Ops-Status | **Geplant:** `GET /api/v1/ops/data-sources` (Admin) — noch nicht implementiert |

## Naechster Meilenstein (GIS)

- OSM/Overpass-ETL separat planen (eigener Worker, nicht `run_data_source_pipeline.py`).
- Siehe `docs/OSM_FETCH_STUB.md` und `docs/RISIKO_STATUS.md` R-08.

## Code-Referenz

- Service: `backend/services/data_source_pipeline.py`
- CLI: `backend/scripts/run_data_source_pipeline.py`
- Tests: `backend/tests/test_data_source_pipeline.py`
