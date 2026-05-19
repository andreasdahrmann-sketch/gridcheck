# OSM / Overpass — Fetch-Stub (Planung)

**Stand:** 2026-05-19  
**Status:** Nicht produktiv. Kein Import in `run_data_source_pipeline.py`.

## Zweck

OpenStreetMap liefert **Hinweise** auf Netzassets, Geometrien und Lagebeziehungen (Datenklasse **B**). OSM darf **niemals** als Quelle für freie Netzkapazität oder verbindliche Anschlussfähigkeit genutzt werden (`.cursor/rules/06-arbeitsweise-gridcheck.mdc`).

## Geplanter Ablauf (Worker, separat)

1. **Bounding Box** aus Projektstandort (PostGIS `ST_MakeEnvelope`, Puffer konservativ).
2. **Overpass-Query** (Beispiel — nur Substation/Power-`way`/`node`, kein Kapazitäts-Claim):

```text
[out:json][timeout:25];
(
  node["power"~"substation|transformer"]({{south}},{{west}},{{north}},{{east}});
  way["power"~"line|minor_line|cable"]({{south}},{{west}},{{north}},{{east}});
);
out body;
>;
out skel qt;
```

3. **Roh-Response** → `raw_hash` (SHA-256, kanonisches JSON).
4. **Normalisierung** → `asset_candidates` (Geometrie, Tags, **kein** `freie_kapazitaet_kw`).
5. **Snapshot** analog `DataSourceSnapshot` in `services/data_source_pipeline.py`:
   - `confidence_geometrisch`: 55–70 (Community-Quelle)
   - `confidence_technisch`: 40–55 (Tags unvollständig)
   - `validierungsstatus`: `PARTIAL` bis manuelle Stichprobe
   - `hinweis`: „OSM — keine Kapazitätsaussage“

## ENV (Vorschlag)

| Variable | Zweck |
|----------|--------|
| `OSM_OVERPASS_URL` | z. B. `https://overpass-api.de/api/interpreter` |
| `OSM_FETCH_TIMEOUT_SEC` | Default `25` |
| `OSM_RATE_LIMIT_PER_MIN` | Default `6` (Reverse-Proxy / Worker) |

## Tests (noch offen)

- Mock-Overpass-JSON → Parser liefert ≥1 Kandidat, **ohne** Kapazitätsfeld.
- Rate-Limit / Timeout → `validierungsstatus=ERROR`, Pipeline bricht Gesamt-ETL nicht ab.

## Verknüpfung

- Pipeline-Übersicht: [DATA_SOURCE_PIPELINE.md](./DATA_SOURCE_PIPELINE.md)
- Risiko R-08: [RISIKO_STATUS.md](./RISIKO_STATUS.md)
