# Datenquellen-Pipeline (MaStR, SMARD, DWD)

## Status

| Quelle | Skript | Tests | Prod-Import |
|--------|--------|-------|-------------|
| MaStR | `run_data_source_pipeline(["mastr"])` | `test_data_source_pipeline.py` | Nur mit `MASTR_EXPORT_URL` |
| SMARD | `["smard"]` | ja | API via `provider_smard` |
| DWD | `["dwd"]` | ja | Nur mit `DWD_SOURCE_URL` |
| OSM | — | — | **Nicht** in diesem Skript |

**Fazit:** Pipeline ist **funktional als Snapshot-/Hash-Framework**, liefert ohne ENV oft `NOT_CONFIGURED`. Kein vollautomatischer GIS-/OSM-Import.

## Ausfuehren

```powershell
cd backend
.\.venv\Scripts\python.exe scripts\run_data_source_pipeline.py
```

Ausgabe: eine Zeile pro Quelle mit `validierungsstatus`, `record_count`, Hash-Prefix.

Snapshots: `backend/daten/datenquellen_snapshots.jsonl` (append-only).

## ENV (optional)

| Variable | Quelle |
|----------|--------|
| `MASTR_EXPORT_URL` | Marktstammdatenregister-Export |
| `DWD_SOURCE_URL` | DWD CDC |

## Naechster Meilenstein (GIS)

- OSM/Overpass-ETL separat planen (eigener Worker, nicht `run_data_source_pipeline.py`).
- Siehe `docs/RISIKO_STATUS.md` R-08.
