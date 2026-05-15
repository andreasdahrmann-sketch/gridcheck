# Stakeholder-Report-Profile (Pre Gridcheck)

Dieses Dokument beschreibt die **kanonischen Report-Profile** und die **Zuordnung** zwischen Backend-Legacy-Typen, Frontend-Typen und API-Ausgaben.

## Ziele

- Gleiche fachliche Datenbasis (Engine-Output `berechne_netzanschluss`), unterschiedliche **Zielgruppe**, **Tonalitaet**, **Abschnittsreihenfolge** und **Tabellendichte**.
- Vertragliches JSON-Modell `GridcheckReportData` (TypeScript: `frontend/lib/reports`, Python-Adapter: `backend/engine/gridcheck_report_mapper.py`).
- Revisionssicherheit: Hashes und Report-Revisionen bleiben in bestehenden Pfaden (`RevisionRecord`, `ReportRevisionRecord`); das kanonische Payload ist zusaetzlich fuer UI/PDF-V2 nutzbar.

## Stakeholder-Typen (kanonisch)

| Kanonisch (`stakeholderType`) | Backend Report-HTML/PDF (`report_type`) | Fokus |
|------------------------------|------------------------------------------|--------|
| `project_developer` | `projektierer` | Handlung, Varianten, naechste Schritte |
| `grid_operator` | `vnb` | Pruefung, Tabellen, N-1-Screening, Zurueckhaltung |
| `investor` | `invest` | Risiko, CAPEX-Band, Szenarien, Due-Diligence |

Mapping-Funktion (Python): `stakeholder_type_for_legacy_report_type()` in `engine/gridcheck_report_mapper.py`.

## Profil-Metadaten

Die Profile (Abschnitte, Ton, Detailgrad) sind im Frontend als Konstanten definiert:

- `frontend/lib/reports/profiles/project-developer.profile.ts`
- `frontend/lib/reports/profiles/grid-operator.profile.ts`
- `frontend/lib/reports/profiles/investor.profile.ts`

Zentrale Auswahl: `getReportProfile(stakeholderType)`.

## API: Kanonisches Report-JSON

Bei **Report-Export** (`/v2/reports/projektierer|vnb|invest`, Format `html` oder `pdf`) wird `gridcheck_report_data` **vor** dem Schreiben der Report-Revision erzeugt und **in** `report_json` persistiert:

- Im Stakeholder-`report_data` (bzw. `report_data` in der JSON-Antwort) unter Schluessel `gridcheck_report_data`
- `report.reportId` entspricht der **Report-Revision-UUID** (`ReportRevisionRecord.uuid`), damit UI und Datenbank konsistent sind
- `persist_report_revision(..., revision_uuid=...)` erlaubt diese UUID vorab; siehe `engine/stakeholder_reports/renderer.py`

Bei **HTML** liefert die Antwort zusaetzlich die gleiche Struktur top-level als `gridcheck_report_data` (Alias zum eingebetteten Objekt).

Felder entsprechen dem TypeScript-Modul `frontend/lib/reports/types/gridcheck-report-data.ts`.

Hinweise zum aktuellen Adapter-Stand:

- **Anschlusskandidaten**: derzeit ein **Modellplatz** aus Eingabe (`entfernung_km`, Spannungsebene), bis OSM-/Kandidaten-Pipeline angebunden ist.
- **Koordinaten**: fehlen `project_location`-Koordinaten, setzt der Adapter einen **sichtbaren Warnhinweis** und Platzhalterwerte (nur Schema-Vollstaendigkeit).
- **Investor `curtailmentRisk`**: aus Erzeugungstyp und Trassenrisiko grob belegt.

## Validierung (Frontend)

- `validateReportForFinalization` / `runPrePdfQualityChecks` in `frontend/lib/reports/`.

Backend liefert ein **Entwurfs**-Payload (`report.status`: `draft`, `audit.immutable`: `false`), bis eine explizite Finalisierungsstufe eingefuehrt wird.

## Naechste Ausbaustufen

1. Engine-/Datenpipeline: mehrere `candidateConnectionPoints` aus realen Kandidaten.
2. Backend: optionales Pydantic-Schema spiegelnd zu TS fuer serverseitige Validierung.
3. PDF-Renderer: Sektionen aus `getReportProfile()` statt nur Kurz-PDF.
