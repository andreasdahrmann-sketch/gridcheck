# GridCheck Roadmap

## Sprint 1 - Projektierer-Modul (LAEUFT)
Ziel: /projektierer mit Was-waere-wenn-Optimierer (Variante a)

- [ ] Backend: Refactor in core/ + roles/projektierer.py
- [ ] Backend: Endpoint POST /api/v1/projektierer/analyze
- [ ] Backend: Optimizer-Logik (max. zulaessige Leistung + 2 Auflagen-Varianten)
- [ ] Frontend: Route /projektierer
- [ ] Frontend: ProjektiererForm.tsx (Budget, Zeitfenster, Flex-Flags)
- [ ] Frontend: ProjektiererResult.tsx (mit Optimizer-Sektion)
- [ ] Frontend: Landing / mit 3 Rollen-Karten (1 aktiv, 2 coming soon)
- [ ] PDF-Export Projektierer-spezifisch
- [ ] Test mit realem Beispiel
- [ ] Backup

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
