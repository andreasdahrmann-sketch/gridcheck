# Stakeholder-PDF-Reports (Backend ReportLab)

GridCheck erzeugt **keine** clientseitigen jsPDF-Exports. Alle Stakeholder-PDFs laufen über:

1. **Frontend:** `exportStakeholderPdf()` → `POST /api/reports/{stakeholder}?format=pdf`
2. **Next.js Proxy:** `frontend/app/api/reports/[stakeholder]/route.ts`
3. **Backend:** `POST /api/v2/reports/{projektierer|vnb|invest}?format=pdf` (`backend/api/v2_reports.py`)
4. **PDF:** ReportLab in `backend/engine/stakeholder_reports/pdf_builder.py`

Datenquelle ist immer ein **serverseitig berechneter** Engine-Run (`analyze_request` oder `analysis_run_id`). Client-gelieferte `engine_result`-Payloads werden abgewiesen.

## Report-Typen und Inhalt

### Projektierer (`projektierer`)

Zielgruppe: Planer / Projektentwickler — technische Vorplanung und VNB-Vorbereitung.

| Abschnitt | Quelle |
|-----------|--------|
| Projektkern, N-1, Auflagen, Maßnahmen | `berechnung.py` |
| **Warnungen** | `warnungen` |
| **Technische Kenngrößen (Tabelle)** | `technical_details` + Thermik/Spannung |
| **Zeitplan (heuristisch)** | `grid_calculation_v2.projektierer_perspective.process_timeline` |
| **BKZ-Hinweis** | `projektierer_perspective.bkz_hint` |
| **EEG §9-Checkliste** | `grid_calculation_v2.eeg_feed_in_screening` |
| **Blindleistung-Checkliste** | `grid_calculation_v2.reactive_power_screening` |
| **grid_calculation_v2 Zeilen** | `projektierer_perspective`, Normen-Screening |
| Anschlussstrategie / Risiko | Projektprofil, Speicher, Trasse, Stakeholder |
| Normen-Snapshot | `compliance.get_normen_fuer_spannungsebene` |
| Transparenz / Disclaimers | `transparenz` |

Anlagentyp-Labels stammen aus `backend/engine/plant_types.py` (`plant_type_label` in `projektierer_perspective`).

### Netzbetreiber (`vnb`)

Zielgruppe: VNB-Vorprüfung — strukturierte Anfrage, keine Kapazitätszusage.

| Abschnitt | Quelle |
|-----------|--------|
| Checkliste-Netzbetreiber (Hinweistext) | statisch + fachlich |
| Strukturierte Anfrageprüfung | Antragskern, N-1, Netzdatenbasis |
| Technische Vorprüfung | thermisch / spannung / kurzschluss / N-1 |
| **Technische Kenngrößen — VNB-Prüfmatrix** | Screening-Spalte + Spalte **„VNB-Prüfung“** (offen für Bearbeitung) |
| Prozess-Zeitplan | `projektierer_perspective.process_timeline` (Referenz) |
| Status- / Prozesssicht, Auflagen | Engine + Scope |
| **Signatur / Freigabe (Formularfeld)** | statisches PDF-Layout (keine eSignatur) |
| Daten- / Auditrolle, Sichtbarkeitsgrenze | `datenqualitaet`, Revision |

### Invest / Management (`invest`)

Zielgruppe: Due Diligence — aggregierte KPIs, keine interne Netztiefe in der API.

| Abschnitt | Quelle |
|-----------|--------|
| **KPI-Zusammenfassung** | Entscheidung, Score, N-1-Klasse, Kostenband, Stakeholder-Fit |
| **Zeitplan-Indikation** | `process_timeline` (falls v2-Perspektive vorhanden) |
| Standortbewertung, Risikoanalyse | Eingabe + Engine |
| Kosten-Indikation / Bandbreite | `kosten` (Paket abhängig) |
| Due-Diligence-Checkliste, Portfolio-Sicht | Engine-Heuristiken |

## Disclaimer (alle Reports)

Jeder Export enthält mindestens:

- Vorläufige Analyse — **keine verbindliche Netzanschlusszusage**
- **Keine Kapazitätsgarantie** — freie Netzkapazität nur mit belastbarem VNB-Datenstand
- Zusätzliche Einträge aus `transparenz.disclaimers`

VNB-Reports betonen zusätzlich: keine Freigabe interner Netzkapazität. Invest-Reports: keine Roh-Feeder-/Impedanzdaten.

## PDF von `/projektierer` herunterladen

1. Öffnen: **`/projektierer`** (Projektierer-Modul mit `GridCheckForm`).
2. Einloggen (JWT erforderlich).
3. Projekt analysieren („Analyse starten“).
4. Button **„Projektreport PDF“** (bzw. `exportLabel` aus Stakeholder-Copy) — ruft `handlePdfExport` → `exportStakeholderPdf(..., "projektierer")` auf.
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

## Tests

```bash
cd backend && pytest tests/test_projektierer_report.py tests/test_stakeholder_reports_vnb_invest.py tests/test_gridcheck_report_mapper.py -q
cd frontend && npm run build
```

## Relevante Dateien

- `backend/engine/stakeholder_reports/content_blocks.py` — gemeinsame Extraktion
- `backend/engine/stakeholder_reports/projektierer.py` / `vnb.py` / `invest.py`
- `backend/engine/gridcheck_report_mapper.py` — kanonisches `gridcheck_report_data`
- `backend/services/visibility_service.py` — API-Sichtbarkeit (`technical_details`, `grid_calculation_v2`)
- `frontend/lib/api/analyze.ts` — `exportStakeholderPdf`
