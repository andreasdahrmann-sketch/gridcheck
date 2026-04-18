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
