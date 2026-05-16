# PDF-Report Abnahme (P1-T01)

## Abnahmekriterien

- Drei Stakeholder-Reports (`projektierer`, `vnb`, `invest`) erzeugen revisionssichere PDFs mit Audit-Metadaten.
- Pflichtfelder des kanonischen `gridcheck_report_data` sind vor PDF-Export validiert (`report_quality.py`).
- Keine verbindliche Netzanschlusszusage im Managementtext (Heuristik).
- Mindestens eine Warnung oder dokumentierte Annahme im Report.
- Stakeholder-Report enthält Disclaimers und Audit-/Revisionsbezug.

## Automatisierte Prüfung

### Backend-Unit-/Integrationstests

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests/test_report_quality.py tests/test_projektierer_report.py tests/test_stakeholder_reports_vnb_invest.py -q
```

Erwartung: alle Tests grün (Stand P1-T01: 44+ Report-Tests).

### Staging / Go-Live-Smoke (Realfall gegen laufende API)

```powershell
cd backend
.\.venv\Scripts\python.exe scripts/smoke_go_live.py --base-url https://api.example.com --email user@example.com --password 'Passwort123!'
```

Prüft u. a. `POST /api/v2/reports/projektierer?format=pdf` mit Bearer-Token (CSRF entfällt für Bearer).

Erfolg: HTTP 200, `Content-Type: application/pdf`, Body beginnt mit `%PDF`.

## Technische Umsetzung

| Komponente | Pfad |
|------------|------|
| Qualitätsgate | `backend/engine/stakeholder_reports/report_quality.py` |
| API-Einbindung (nur PDF) | `backend/api/v2_reports.py` → `REPORT_PDF_QUALITY_FAILED` |
| Frontend-Spiegel (optional) | `frontend/lib/reports/pre-pdf-checks.ts` |

HTML-Export bleibt ungeblockt; PDF-Export wird bei Qualitätsmängeln mit 422 abgewiesen.

## Hinweis

Dieser Report ist eine automatisierte technische Vorbewertung und ersetzt keine verbindliche Netzanschlussprüfung durch den zuständigen Netzbetreiber.
