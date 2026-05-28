# Stakeholder-PDF-Reports (Backend ReportLab)

GridCheck erzeugt **keine** clientseitigen jsPDF-Exports. Alle Stakeholder-PDFs laufen über:

1. **Frontend:** `exportStakeholderPdf()` → `POST /api/reports/{stakeholder}?format=pdf`
2. **Next.js Proxy:** `frontend/app/api/reports/[stakeholder]/route.ts`
3. **Backend:** `POST /api/v2/reports/{projektierer|vnb|invest}?format=pdf` (`backend/api/v2_reports.py`)
4. **PDF:** ReportLab Platypus in `backend/engine/stakeholder_reports/pdf_builder.py`,
   visuelle Primitives in `backend/engine/stakeholder_reports/pdf_layout.py`.

Datenquelle ist immer ein **serverseitig berechneter** Engine-Run (`analyze_request` oder `analysis_run_id`). Client-gelieferte `engine_result`-Payloads werden abgewiesen.

## Visuelles System (Layout-Stand 2025-11)

Alle drei Stakeholder-PDFs teilen sich ein gemeinsames Layout-System:

| Element | Beschreibung |
|---------|--------------|
| Format | A4 Portrait, Platypus-Story (kein manueller Canvas) |
| Brand-Bar | Farbiger Header mit Wordmark + Titel + Subtitel; Stakeholder-Farbe |
| Stakeholder-Farben | Projektierer `#0F3460`, VNB `#1E40AF`, Invest `#7C3AED` |
| Meta-Strip | Report-ID, Version/Normstand, Paket, SHA-256 (16 Zeichen) unter dem Header |
| Heading H2 | Farbiger Text in Brand-Farbe, oberhalb mit Spacing |
| Tabellen | Header in Brand-Farbe, alternierende Zeilen `#F1F5F9` / `#EEF2FF` / `#F5F3FF` |
| Status-Badges | `●` in grün (`#16A34A`) / orange (`#D97706`) / rot (`#DC2626`) + Text |
| KPI-Kacheln (Invest) | 4er-Strip mit großem Wert, Label, Sublabel |
| Signaturboxen (VNB) | 3 nebeneinanderliegende Boxen mit Linie + „Datum, Ort / Stempel" |
| Footer | Disclaimer, `SHA-256 (Audit): xxxxxxxxxxxx`, Seite x, Report-ID — auf jeder Seite |

### Deterministischer Hash

`compute_footer_hash(report)` (in `pdf_builder.py`) berechnet eine SHA-256-Summe
über das Report-Payload, abzüglich selbst-referentieller Felder
(`audit_hash`, `report_revision*`, `report_generated_at`, `report_verify_path`).
Das macht den Footer-Hash über Re-Generierungen hinweg stabil und kann
unabhängig vom DB-`audit_hash` reproduziert werden.

## Report-Typen und Inhalt

### Projektierer (`projektierer`)

Zielgruppe: Planer / Projektentwickler — technische Vorplanung und VNB-Vorbereitung.

| Abschnitt | Quelle |
|-----------|--------|
| **Cover** (Projekt, Anlagentyp, Ort+PLZ, AC kW, DC kWp, Datum, Report-ID) | `eingabe` + `projektierer_perspective` |
| **Fazit-Box (A/B/C)** mit Begründung, farblich severity-codiert | `fazit.entscheidung` + `n1` |
| **KPI-Tabelle**: ΔU%, Iₖ, Thermik %, Querschnitt mm², N-1 — mit Norm + Status-Badge | `technical_details_table` + `projektierer_perspective` |
| **Annahmen & Confidence**: cos φ, Gleichzeitigkeit, EEG-Klasse, Q-Modus, Datenqualität, N-1 Datengrundlage | `projektierer_perspective` |
| **Plant-Context** (Label, AC/DC, Profilhinweis) | `plant_types.py` |
| **§9 EEG 2023 Checkliste** | `grid_calculation_v2.eeg_feed_in_screening` |
| **Zeitplan (heuristisch) + BKZ-Indikation** | `projektierer_perspective.process_timeline` + `bkz_hint` |
| **NVP-Empfehlung** | `projektierer_perspective.nvp_recommendation` |
| **Maßnahmen / Auflagen** | `empfohlene_massnahmen` + `auflagen` |
| **Norm-Referenzen** | `compliance.get_normen_fuer_spannungsebene` |
| **Disclaimer + Footer-Hash** | statisch + `compute_footer_hash` |

### Netzbetreiber (`vnb`)

Zielgruppe: VNB-Vorprüfung — strukturierte Anfrage und Entscheidungsvorlage, keine Kapazitätszusage.

| Abschnitt | Quelle |
|-----------|--------|
| **Antragsidentifikation** (Antragsteller, Standort, Anlagentyp, Leistung, Spannungsebene, Anschlussart, Datengrundlage, Datum) | `eingabe` |
| **Technische Antragsdaten (Screening)**: Kenngröße / Vorprüfwert / Norm / Screening-Badge / „VNB-Prüfung [ ]"-Spalte | `technical_review_table` |
| **VNB-Prüfcheckliste (10 Punkte)** mit „Geprüft"-Spalte und Bemerkungsfeld | statisch |
| **Status- / Prozesssicht** | `process_view` |
| **Hinweis zur VNB-Prüfung** (rechtlicher Standardtext) | `netzbetreiber_checkliste_hinweis` |
| **Entscheidungsblock** (3 ankreuzbare Optionen, ☐) | statisch |
| **Auflagen / Bedingungen** (8 linierte Zeilen) | statisch |
| **Freigabe / Unterschriften** (Antragsteller, VNB, Leitung) | statisch |
| **Disclaimer + Footer-Hash** | statisch + `compute_footer_hash` |

### Invest / Management (`invest`)

Zielgruppe: Due-Diligence-Sicht — aggregierte KPIs, keine interne Netztiefe.

| Abschnitt | Quelle |
|-----------|--------|
| **Hero**: großer Score + Fazit-Badge + kuratierter Empfehlungstext | `kpi_summary` / `scores`, `fazit`, `recommended_focus` |
| **4 KPI-Kacheln**: Anschlussleistung, GridCheck-Score, Kosten-Schätzung, Zeitrahmen | `kosten`, `process_timeline` |
| **Chancen / Risiken** (zwei-spaltig, kuratiert) | `risk_overview`, `portfolio_view` |
| **Eckdaten-Tabelle** | `eingabe` |
| **Kostenbandbreite (Detail)** (optional, paketabhängig) | `cost_band` |
| **Nächste Schritte** | `empfohlene_massnahmen` + Top-KPI |
| **Disclaimer + Sichtbarkeitsgrenze** | `visibility_boundary_note` + statisch |

## Disclaimer (alle Reports)

Jeder Export enthält mindestens:

- Vorläufige Diagnose — **keine verbindliche Netzanschlusszusage**
- **Keine Kapazitätsgarantie** — freie Netzkapazität nur mit belastbarem VNB-Datenstand
- **N-1 maximal bis N1-2 ohne verifizierte VNB-Daten**
- Zusätzliche Einträge aus `transparenz.disclaimers`

VNB-Reports betonen zusätzlich: keine Freigabe interner Netzkapazität.
Invest-Reports: keine Roh-Feeder-/Impedanzdaten.

## PDF von `/projektierer` herunterladen

1. Öffnen: **`/projektierer`** (Projektierer-Modul mit `GridCheckForm`).
2. Einloggen (JWT erforderlich).
3. Projekt analysieren („Analyse starten").
4. Button **„Projektreport PDF"** (bzw. `exportLabel` aus Stakeholder-Copy) — ruft `handlePdfExport` → `exportStakeholderPdf(..., "projektierer")` auf.
5. Der Browser lädt `gridcheck-projektierer-{scope}.pdf` herunter.

Technische Details und `grid_calculation_v2` erscheinen in der UI nach der Analyse (sofern die Engine sie liefert); der PDF-Export nutzt denselben Run über `analysis_run_id`, wenn vorhanden.

**API direkt (mit Bearer-Token):**

```http
POST /api/v2/reports/projektierer?format=pdf
Content-Type: application/json

{"analysis_run_id": 123}
```

oder mit frischer Berechnung:

```http
{"analyze_request": { "nennspannung": 20, "leistung_mw": 5, ... }}
```

Analog für `/api/v2/reports/vnb?format=pdf` und `/api/v2/reports/invest?format=pdf`.

## Beispiel-PDFs (Seed-Skript)

```bash
cd backend
python scripts/seed_example_and_export_pdf.py --skip-db
```

Erzeugt für jedes Demo-Szenario je drei PDFs unter `reports/`:

```
reports/gridcheck-projektierer-demo-pv-ms-auflagen.pdf
reports/gridcheck-vnb-demo-pv-ms-auflagen.pdf
reports/gridcheck-invest-demo-pv-ms-auflagen.pdf
reports/example-gridcheck-report.pdf   # Kopie des primären Projektierer-Reports
reports/example-seed-manifest.json
```

Ohne `--skip-db` werden zusätzlich Demo-Nutzer, Projekte und Analyse-Runs angelegt
(Login `demo.seed@gridcheck.example`).

## Tests

```bash
cd backend
pytest tests/test_projektierer_report.py tests/test_stakeholder_reports_vnb_invest.py tests/test_gridcheck_report_mapper.py -q
cd ../frontend && npm run build
```

Neu hinzugekommen:

- `test_projektierer_pdf_has_report_id_and_disclaimer` — parst das PDF mit `pypdf`,
  prüft Seitenanzahl ≥ 2, Vorkommen von `Report-ID`, `Vorläufige Diagnose`, `SHA-256`.
- `test_projektierer_pdf_hash_is_deterministic` — gleicher Input ⇒ gleicher Hash.
- `test_vnb_pdf_contains_decision_block_and_signatures` — prüft Entscheidungsblock,
  Auflagenfeld und Unterschriften-Bereich.
- `test_invest_pdf_contains_score_and_kpis` — prüft Hero-Score, KPI-Kacheln, Eckdaten
  und Chancen/Risiken.

Abhängigkeit hinzu: `pypdf>=4.3.0` (siehe `backend/requirements.txt`).

## Relevante Dateien

- `backend/engine/stakeholder_reports/pdf_builder.py` — High-Quality Builder (3 Stories, Hash, Footer)
- `backend/engine/stakeholder_reports/pdf_layout.py` — Layout-Primitives (Palette, alt_table, kpi_strip, signature_block, lined_field, decision_picks, summary_box, brand_header, make_footer_callback)
- `backend/engine/stakeholder_reports/content_blocks.py` — gemeinsame Extraktion aus Engine-Ergebnissen
- `backend/engine/stakeholder_reports/projektierer.py` / `vnb.py` / `invest.py` — Stakeholder-DTOs
- `backend/engine/gridcheck_report_mapper.py` — kanonisches `gridcheck_report_data`
- `backend/services/visibility_service.py` — API-Sichtbarkeit (`technical_details`, `grid_calculation_v2`)
- `frontend/lib/api/analyze.ts` — `exportStakeholderPdf`
