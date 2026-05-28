# Perf-Baseline (BL-PERF-006)

Baseline-Setup und Mess-Vorgehen für Backend, Frontend und (optional) End-to-End.
Ziel: TIER-2-Performance-Entscheidungen (siehe `docs/ROADMAP_BACKLOG.md`
BL-PERF-001 … BL-PERF-005) basieren auf reproduzierbaren Zahlen statt
Schätzungen.

> **Status:** Setup geliefert (Commit folgt). Baseline-Runs (Backend-Bench
> + Frontend-Bundle) sind durch den Nutzer einmalig auszuführen — siehe
> [PowerShell-Befehlsblock unten](#einmaliger-bootstrap-powershell).

---

## 1. Zweck

- **TIER 1 ist gelandet** (`efdf9aa`): `lru_cache` auf `get_cable_params`,
  Jinja-Env-Cache + Shallow-Copy in `stakeholder_reports/renderer.py` und
  `pdf_builder.py`, expliziter DB-Pool, `optimizePackageImports=['lucide-react']`.
- **Vor TIER 2** brauchen wir Vergleichsdaten, sonst optimieren wir blind.
- Dieses Dokument hält fest: **wie** wird gemessen, **was** wird gemessen,
  **wann** muss neu gemessen werden, **wann** ist eine Regression blockierend.

---

## 2. Backend-Benchmarks

### 2.1 Setup (einmalig)

```powershell
cd C:\Users\andre\gridcheck\backend
pip install -r requirements-dev.txt
```

`requirements-dev.txt` enthält nur `pytest-benchmark`. Kein zusätzlicher
Profiler im Lockfile — `cProfile` ist Stdlib, wird ad-hoc verwendet.

### 2.2 Bench-Run

```powershell
cd C:\Users\andre\gridcheck\backend
pytest tests/perf/ --benchmark-only --benchmark-save=baseline_$(Get-Date -Format yyyyMMdd_HHmm)
```

- Output: `backend/.benchmarks/` (per `.gitignore` ausgeschlossen).
- Im normalen `pytest backend/tests/`-Lauf werden Perf-Tests
  **nicht** mit ausgeführt (siehe `backend/pytest.ini` →
  `norecursedirs = perf` und Skip-Logik in `backend/tests/perf/conftest.py`).
- Vergleich gegen vorherige Baseline:
  ```powershell
  pytest tests/perf/ --benchmark-only --benchmark-compare=baseline_initial
  ```

### 2.3 Gemessene Hot-Paths

| Test-Datei | Group | Gegenstand |
|------------|-------|-----------|
| `test_perf_cable_lookup.py` | `cable_lookup` | `engine.cable_database.get_cable_params` (3× pro Check, `lru_cache`-Wirkung) |
| `test_perf_grid_calc.py` | `grid_calc` | `engine.grid_calculation_v2.calculate_grid_connection` für 100 kW / 1 MW / 10 MW PV |
| `test_perf_pdf_render.py` | `pdf_render` | `engine.stakeholder_reports.pdf_builder.build_stakeholder_report_pdf` für `projektierer`, `vnb`, `invest` |

### 2.4 Ad-hoc `cProfile` (Hot-Path-Visualisierung)

Wenn ein Bench-Ergebnis auffällig ist, lokal Hotspots auflisten:

```powershell
cd C:\Users\andre\gridcheck\backend
python -m cProfile -o perf.prof -m pytest tests/perf/test_perf_pdf_render.py --benchmark-only -q
python -c "import pstats; pstats.Stats('perf.prof').sort_stats('cumulative').print_stats(40)"
```

`perf.prof` ist nicht im Repo (gitignored über `*.prof`).

---

## 3. Frontend-Bundle-Analyse

### 3.1 Setup

```powershell
cd C:\Users\andre\gridcheck\frontend
npm install
```

Dies installiert `@next/bundle-analyzer` (14.2.35, matching Next-Version)
und `cross-env`.

### 3.2 Bundle-Analyse

```powershell
cd C:\Users\andre\gridcheck\frontend
npm run build:analyze
```

Output:
- `frontend/.next/analyze/client.html`
- `frontend/.next/analyze/nodejs.html`
- `frontend/.next/analyze/edge.html`

(per `.gitignore` ausgeschlossen)

> `next.config.mjs` aktiviert den Analyzer nur, wenn `ANALYZE=true` gesetzt
> ist. Ist `@next/bundle-analyzer` nicht installiert (frischer Clone),
> baut Next weiterhin sauber durch — der Wrapper ist eine no-op und gibt
> nur eine Warnung aus.

### 3.3 Build-Profile (React Production Profiler)

```powershell
cd C:\Users\andre\gridcheck\frontend
npm run build:profile
```

Erlaubt React-DevTools-Profiler-Sessions gegen die Production-Build-Bundles
(z. B. für BL-PERF-001 `GridCheckForm.tsx`-Render-Reduktion).

---

## 4. End-to-End (Lighthouse, optional)

Leichtgewichtiger Smoke gegen Production-Deploy:

```powershell
npx lighthouse https://gridcheck.vercel.app/ --output html --output-path .\lighthouse-baseline.html --chrome-flags="--headless"
```

Pfad ist per `.gitignore` ausgeschlossen (`lighthouse-baseline.html`,
`frontend/lighthouse-*.html`). Lighthouse-CI als richtigen Pipeline-Job
ist Folgeaufgabe (BL-PERF-006-Akzeptanzkriterium ist eine
reproduzierbare lokale Suite, nicht CI-Integration).

---

## 5. Baseline-Tabelle

Nach jedem Bench-Lauf eintragen. Mean/Median/StdDev sind aus dem
pytest-benchmark-Output (`min/median/mean/stddev`, in ms). „Notizen" zeigt
Auffälligkeiten, Hardware-Wechsel, Hintergrundlast etc.

| Datum | Commit | Bench | Mean | Median | StdDev | Notizen |
|-------|--------|-------|------|--------|--------|---------|
| 2026-05-28 | `efdf9aa` + BL-PERF-002 (lokal, uncommitted) | `cable_lookup::hot_path` | 4.70 µs | 1.40 µs | 164.53 µs | StdDev hoch (Hintergrundlast?), Median ist robuster |
| 2026-05-28 | `efdf9aa` + BL-PERF-002 (lokal) | `cable_lookup::cold_then_warm` | 15.81 µs | 3.50 µs | 636.06 µs | Median 3.5 µs — `lru_cache`-Wirkung sichtbar |
| 2026-05-28 | `efdf9aa` + BL-PERF-002 (lokal) | `grid_calc::small` (100 kW) | 1235.51 µs | 219.40 µs | 4111.23 µs | Hoher StdDev — Re-Bench bei reduzierter Hintergrundlast empfohlen |
| 2026-05-28 | `efdf9aa` + BL-PERF-002 (lokal) | `grid_calc::medium` (1 MW) | 593.64 µs | 218.65 µs | 2118.29 µs | Median ~219 µs ist die belastbare Zahl |
| 2026-05-28 | `efdf9aa` + BL-PERF-002 (lokal) | `grid_calc::large` (10 MW) | 548.46 µs | 208.50 µs | 3266.65 µs | Median ~209 µs |
| 2026-05-28 | `efdf9aa` + BL-PERF-002 (lokal) | `pdf_render::projektierer` | 68.84 ms | 62.84 ms | 21.41 ms | StdDev ~31 % vom Mean → unzuverlässig, mehrere Runs |
| 2026-05-28 | `efdf9aa` + BL-PERF-002 (lokal) | `pdf_render::vnb` | 76.19 ms | 75.28 ms | 3.95 ms | StdDev sauber, belastbar |
| 2026-05-28 | `efdf9aa` + BL-PERF-002 (lokal) | `pdf_render::invest` | 60.46 ms | 57.65 ms | 22.20 ms | StdDev ~37 % vom Mean → unzuverlässig |

> **Hinweis:** Erste Baseline wurde *nach* lokaler Anwendung von BL-PERF-002 erzeugt. Der reine Effekt von BL-PERF-002 ist daher *nicht* aus diesem Run ableitbar; künftige Bench-Compares gegen `baseline_initial` messen Änderungen *gegenüber* diesem Stand.
> Mehrere `pdf_render`- und `grid_calc`-Tests zeigen StdDev > 20–30 % vom Mean → für TIER-2-Entscheidungen ggf. mit `--benchmark-min-rounds 50` re-bench oder Hintergrundlast reduzieren.

Frontend (manuell aus `client.html` ablesen — Initial-JS, Total-JS, größte
Chunks):

| Datum | Commit | Initial JS (kB gzipped) | Total JS (kB) | Top-3 Chunks | Notizen |
|-------|--------|-------------------------|---------------|--------------|---------|
| _YYYY-MM-DD_ | `efdf9aa` | _t.b.d._ | _t.b.d._ | _t.b.d._ | Baseline nach TIER 1 |

---

## 6. Wann re-bench?

- **Nach jedem Perf-PR** (TIER 2 oder TIER 3): vorher + nachher messen,
  Diff in PR-Beschreibung.
- **Vor jedem TIER-2-Refactor**: aktueller Stand als Anker.
- **Bei Next-/React-/Pydantic-/SQLAlchemy-Minor-Bump**: Sanity-Check, dass
  keine unerwartete Regression kommt (Toolchain-Matrix in
  `.cursor/rules/07-toolchain-versions.mdc`).
- **Bei größerem Engine-Refactor** (`grid_calculation_v2`,
  `stakeholder_reports/*`): immer vorher + nachher.

---

## 7. Regression-Blocking-Kriterium

- **> 20 % Verschlechterung im Mean** (oder Median) eines Hot-Path-Benchmarks
  gegen die letzte gespeicherte Baseline gilt als Regression und blockt den
  PR-Merge, bis entweder:
  1. die Ursache identifiziert und behoben ist,
  2. oder die Regression dokumentiert + bewusst akzeptiert wird
     (Eintrag in dieser Datei + Commit-Message-Begründung).
- StdDev > 30 % vom Mean → Messung ist unzuverlässig, mehrere Runs
  fahren und ggf. Hintergrundlast (Indexer, Antivirus) reduzieren.

---

## 8. Einmaliger Bootstrap (PowerShell)

Siehe Antwort des Setup-Subagenten / Commit-Message. Kurzfassung:

```powershell
cd C:\Users\andre\gridcheck

# Backend: dev-deps + Baseline-Run
cd backend
pip install -r requirements-dev.txt
pytest tests/perf/ --benchmark-only --benchmark-save=baseline_initial
cd ..

# Frontend: deps + Bundle-Analyse
cd frontend
npm install
$env:ANALYZE = "true"
npm run build
cd ..
```

Ergebnis-Pfade:
- `backend/.benchmarks/Linux-CPython-3.11-64bit/0001_baseline_initial.json`
  (Pfadstruktur abhängig von Plattform)
- `frontend/.next/analyze/client.html`, `nodejs.html`, `edge.html`

---

## 9. Verweise

- `.cursor/rules/05-workflow.mdc` (Revisionssicherheit, Schritt-für-Schritt-Arbeitsweise)
- `.cursor/rules/06-arbeitsweise-gridcheck.mdc` (eine Aufgabe zur Zeit)
- `.cursor/rules/07-toolchain-versions.mdc` (kein Major-Bump ohne ADR)
- `docs/ROADMAP_BACKLOG.md` → Abschnitt „Performance" (BL-PERF-001 … 006)
- Commit `efdf9aa` (TIER-1-Quick-Wins)
