# Architecture Decisions Log

| #   | Datum      | Entscheidung                                                | Begruendung                                          |
|-----|------------|-------------------------------------------------------------|------------------------------------------------------|
| 001 | 2026-05-02 | Getrennte Routen pro Stakeholder (/projektierer, /vnb, ...) | Saubere UX, klare Monetarisierung                    |
| 002 | 2026-05-02 | Phasenreihenfolge Projektierer -> VNB -> Invest             | Hoechste Nutzerzahl zuerst, dann hoechster Lizenzwert|
| 003 | 2026-05-02 | Killer Phase 1 = Was-waere-wenn-Optimierer schlank (Var. a) | MVP-Fokus, kein Verzetteln                           |
| 004 | 2026-05-02 | Stack: FastAPI + React/TS + SQLite                          | Bereits implementiert, kostenfrei                    |
| 005 | 2026-05-02 | Revisionssicherheit via SHA256 Hash-Chain                   | Kostenfrei, ausreichend fuer MVP                     |
| 006 | 2026-05-02 | Gemeinsame Core-Engine, rollenspezifische Layer             | Vermeidet Code-Duplikation                           |
| 007 | 2026-05-02 | AI liefert IMMER PowerShell-Befehle, nie rohe Markdown      | User arbeitet auf Windows PowerShell                 |
