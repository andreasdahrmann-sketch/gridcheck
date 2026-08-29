# GridCheck Roadmap

> Stand: 2026-06-14 (HEAD `f3a2d99`).
> Gesamtstand und offene Punkte: `docs/PROJECT_STATUS.md` (massgeblich).
> Sequenzierte Folgestories (BL-NB-*, BL-GIS-*, BL-PERF-*): `docs/ROADMAP_BACKLOG.md`.
>
> Legende: `[x]` erledigt und verifiziert, `[~]` funktional erfuellt, aber abweichend
> vom urspruenglichen Plan umgesetzt, `[ ]` offen.

## Sprint 1 - Projektierer-Modul (weitgehend erledigt)
Ziel: /projektierer mit Was-waere-wenn-Optimierer (Variante a)

- [x] Backend: Refactor in core/ + roles/projektierer.py (`backend/roles/projektierer.py`, importiert in `backend/api/v1_projektierer.py`)
- [x] Backend: Endpoint POST /api/v1/projektierer/analyze (`APIRouter(prefix="/api/v1/projektierer")` + `@router.post("/analyze")`)
- [x] Backend: Optimizer-Logik (max. zulaessige Leistung + 2 Auflagen-Varianten) (`backend/engine/optimizer.py`, `backend/tests/test_optimizer.py`)
- [x] Frontend: Route /projektierer (`frontend/app/projektierer/page.tsx`)
- [~] Frontend: ProjektiererForm.tsx (Budget, Zeitfenster, Flex-Flags) — (abweichend: keine eigene Komponente; die Rollenseite rendert `GridCheckForm` mit `forcedCustomerType="projektierer"`, `frontend/app/projektierer/page.tsx` Z. 92)
- [~] Frontend: ProjektiererResult.tsx (mit Optimizer-Sektion) — (abweichend: ebenfalls ueber `GridCheckForm` geloest, keine eigene Result-Komponente)
- [~] Frontend: Landing / mit 3 Rollen-Karten (1 aktiv, 2 coming soon) — (weiter als geplant: in `frontend/app/page.tsx` stehen alle drei Karten auf `status: "Aktiv"` und verlinken auf `/projektierer`, `/vnb`, `/invest`)
- [x] PDF-Export Projektierer-spezifisch (`backend/engine/stakeholder_reports/projektierer.py` + `templates/projektierer.html.j2`)
- [x] Test mit realem Beispiel (`backend/tests/test_v1_projektierer_analyze.py`, `backend/tests/test_demo_scenarios.py`)
- [ ] Backup — offen, nicht verifizierbar: `_milestone_backups/` liegt nicht im Working Tree (per `.gitignore` ausgeschlossen); `DECISIONS.md` referenziert einen Dump vom 2026-05-13

## Sprint 2 - VNB-Modul
- [ ] /vnb Route + Form + Result
- [ ] N-1-Auflagen-Generator (VDE-AR-N 4110/4120-Textbausteine)
- [ ] Bestandsnetz-Daten-Upload (CSV/JSON)
- [ ] Pruefprotokoll-PDF

## Sprint 3 - Invest-Modul
- [ ] /invest Route + Form + Result
- [ ] Curtailment-Prognose
- [ ] ROI-Sensitivitaetsmatrix
- [ ] Bankfaehiger 1-Pager

## Sprint 4 - KI-Layer
- [ ] Feedback-Loop (reale Bescheide eingeben)
- [ ] ML-Modell (sklearn) fuer Confidence-Verbesserung
- [ ] Audit-Trail je Empfehlung

## Sprint 5 - Multi-VNB-Vergleich
- [ ] VNB-Profile-DB
- [ ] Standort-Vergleichs-View
