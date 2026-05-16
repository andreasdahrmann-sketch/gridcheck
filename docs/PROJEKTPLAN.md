# GridCheck Projektplan
# Letzte Aktualisierung: 2026-04-13 07:03

| # | Bereich | Aufgabe | Status | Prio |
|---|---------|---------|--------|------|
| **PHASE 1: Backend fertigstellen** |||||
| 1.1 | Backend | FastAPI Server mit /api/analyze Endpoint | ✅ | 🔴 |
| 1.2 | Backend | Engine-Logik Python (Impedanz, Spannungsfall, Score) | ✅ | 🔴 |
| 1.3 | Backend | PLZ→Netzbetreiber Zuordnung | ⬜ | 🔴 |
| 1.4 | Backend | Defaults pro Kundentyp (Trafo, Sk, Fallbacks) | ✅ | 🔴 |
| 1.5 | Backend | Input-Validierung und Error-Handling | ✅ | 🔴 |
| **PHASE 2: Frontend↔Backend verbinden** |||||
| 2.1 | Frontend | API-Call an Backend statt lokaler Engine | ⬜ | 🔴 |
| 2.2 | Frontend | Loading-State und Error-Anzeige | ⬜ | 🟡 |
| 2.3 | Frontend | CORS konfigurieren | ✅ | 🔴 |
| **PHASE 3: Kernfeatures** |||||
| 3.1 | Frontend | PDF-Export | ⬜ | 🟡 |
| 3.2 | Backend | Ergebnis-Speicherung (SQLite/JSON) | ⬜ | 🟡 |
| 3.3 | Frontend | Ergebnis-Historie / Dashboard | ⬜ | 🟡 |
| 3.4 | Engine | Blindleistungs-Kompensation berechnen | ⬜ | 🟡 |
| 3.5 | Engine | Oberschwingungen (THD) Bewertung | ⬜ | 🟡 |
| **PHASE 4: Datenqualitaet** |||||
| 4.1 | Daten | Reale Netzbetreiber-Daten je PLZ-Gebiet | ⬜ | 🟡 |
| 4.2 | Daten | Reale Trafodaten (Standard-Ortsnetztrafos) | ⬜ | 🟡 |
| 4.3 | Daten | Leitungstypen-Katalog (NAYY, NYY etc.) | ⬜ | 🟡 |
| 4.4 | Engine | Confidence-Score auf Basis realer vs. geschaetzter Daten | ⬜ | 🟡 |
| **PHASE 5: Polish und Deploy** |||||
| 5.1 | Frontend | Responsive Design / Mobile | ⬜ | 🟢 |
| 5.2 | Frontend | Dark/Light Mode Toggle | ⬜ | 🟢 |
| 5.3 | Auth | Login / Multi-User | ⬜ | 🟢 |
| 5.4 | Deploy | Docker Compose (Frontend + Backend) | ⬜ | 🟢 |
| 5.5 | Deploy | CI/CD Pipeline | ⬜ | 🟢 |
| 5.6 | Legal | Disclaimer / Haftungsausschluss | ⬜ | 🟢 |
| **PHASE 6: Monetarisierung (Master-Backlog)** |||||
| 6.1 | Product | Paket-Features in Tickets schneiden (P1/P2/P3) | ⬜ | 🔴 |
| 6.2 | Product | Paket 1 MVP DoD finalisieren (kaufbar, klar abgegrenzt) | ⬜ | 🔴 |
| 6.3 | Product | Paket 2 Abhaengigkeiten definieren (Datenpipeline, Portfolio) | ⬜ | 🟡 |
| 6.4 | Product | Paket 3 Abhaengigkeiten definieren (Intake, Audit, Schnittstellen) | ⬜ | 🟡 |
| 6.5 | Sales | Preis-Hypothesen Paket 1 als Testplan aufsetzen | ⬜ | 🔴 |
| 6.6 | Sales | Preis-Hypothesen Paket 2/3 als Testplan aufsetzen | ⬜ | 🟡 |
| 6.7 | Ops | SLA-/Supportstufen als Angebotsbausteine spezifizieren | ⬜ | 🟡 |
| 6.8 | Product | Monetarisierungs-Metriken im Tracking verankern | ⬜ | 🟡 |

## Akzeptanzkriterien - Monetarisierung

- 6.1 gilt als fertig, wenn fuer jedes Paket mindestens 5 umsetzbare Tickets mit eindeutiger Abnahmebedingung vorliegen.
- 6.2 gilt als fertig, wenn Paket 1 Scope/No-Scope, Preisrahmen und Verkaufsargumente dokumentiert und intern freigegeben sind.
- 6.3 gilt als fertig, wenn technische Gates fuer Paket 2 (Datenverfuegbarkeit, Modellguete, Reportumfang) als Checkliste vorliegen.
- 6.4 gilt als fertig, wenn technische Gates fuer Paket 3 (RBAC, Audit, Intake-Flow, Schnittstellen) als Checkliste vorliegen.
- 6.5/6.6 gelten als fertig, wenn pro Paket mindestens 3 Preisannahmen mit Zielsegment, KPI und Auswertungsfenster definiert sind.
- 6.7 gilt als fertig, wenn Bronze/Silber/Gold-SLA mit Reaktionszeiten und Leistungsumfang spezifiziert ist.
- 6.8 gilt als fertig, wenn KPI-Definitionen (Conversion, ARPA, Churn, Nutzungsintensitaet) in einem Tracking-Dokument hinterlegt sind.

## Referenz

- Detailkonzept der Pakete: `docs/monetarisierungspakete.md`

## Ticket-Schnitt je Paket (6.1)

## Execution-Reihenfolge (Now / Next / Later)

- NOW: P1-T01, P1-T02, P1-T05, P1-T04, P1-T03
- NEXT: P2-T01, P2-T02, P2-T03, P2-T05, P2-T04
- LATER: P3-T01, P3-T02, P3-T03, P3-T04, P3-T05

### Paket 1 - Project Developer (MVP, kaufbar)

- [x] P1-T01: Ergebnis-PDF finalisieren (Pflichtfelder, Warnungen, Disclaimer, Audit-ID/Hash)
  - Abnahme: PDF enthaelt alle Pflichtbloecke; Backend-Qualitaetsgate + 44+ Report-Tests; Realfall-Smoke via `scripts/smoke_go_live.py` (siehe `docs/PDF_REPORT_ABNAHME.md`).
- [NOW] P1-T02: Paket-1 Scope im UI/Onboarding klar markieren (inkl. No-Scope)
  - Abnahme: Featuregrenzen sind an mindestens 2 Kundenkontaktpunkten sichtbar.
- [NOW] P1-T03: Analyse-Limits fuer Paket 1 (pro Zeitraum / Fair Use) technisch vorbereiten
  - Abnahme: Limit-Konfiguration vorhanden und bei Ueberschreitung nachvollziehbare Meldung.
- [NOW] P1-T04: Paket-1 Angebotsseite/Infosektion in App dokumentieren
  - Abnahme: Funktionen + Nutzen + Disclaimer sind konsistent mit `monetarisierungspakete.md`.
- [NOW] P1-T05: KPI-Basis fuer Paket 1 erfassen (Conversion, Wiederholungsquote)
  - Abnahme: Events definiert, dokumentiert und mindestens in Dev pruefbar.

### Paket 2 - Storage / Investment Intelligence

- [NEXT] P2-T01: CAPEX-/Timeline-/Risiko-Modell als fachliches Schema spezifizieren
  - Abnahme: Feldkatalog inkl. Einheiten, Annahmen und Datenquellen ist freigegeben.
- [NEXT] P2-T02: Szenariorechnungen fuer Speicher-/Invest-Cases definieren
  - Abnahme: Mindestens 3 Standardszenarien mit Input/Output und Grenzen dokumentiert.
- [NEXT] P2-T03: Portfoliovergleich-Datenmodell und Aggregationslogik beschreiben
  - Abnahme: Tabellen- und API-Entwurf liegen vor, inkl. Beispielauswertung.
- [NEXT] P2-T04: Management-Report Struktur (1-Pager + Detailanhang) spezifizieren
  - Abnahme: Report-Template mit Pflichtkennzahlen und Risikoblatt ist abgestimmt.
- [NEXT] P2-T05: Regionenranking-Methodik (Scoring + Datenqualitaet) definieren
  - Abnahme: Gewichtung, Confidence-Logik und Disclaimer sind dokumentiert.

### Paket 3 - Grid Operator Suite

- [LATER] P3-T01: Intake-Workflow (Eingang -> Vorpruefung -> Priorisierung -> Fallakte) modellieren
  - Abnahme: Prozessdiagramm und API-Schritte sind eindeutig beschrieben.
- [LATER] P3-T02: Rollen-/Rechte-Matrix fuer VNB-Organisationen finalisieren
  - Abnahme: RBAC-Matrix inkl. kritischer Berechtigungen ist verabschiedet.
- [LATER] P3-T03: Audit-Trail-Anforderungen fuer Betreiberpruefung konkretisieren
  - Abnahme: Pflichtfelder, Unveraenderlichkeit und Exportformat sind definiert.
- [LATER] P3-T04: Schnittstellenbedarf (CSV/API/Webhook) priorisieren
  - Abnahme: Top-3 Integrationen mit Datenvertrag und Sicherheitsanforderungen liegen vor.
- [LATER] P3-T05: Internes Dashboard fuer Fallpriorisierung als MVP spezifizieren
  - Abnahme: KPI-Set, Filterlogik und Drilldown-Anforderungen sind dokumentiert.
