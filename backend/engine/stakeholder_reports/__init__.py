"""
Stakeholder-spezifische PDF-Reports (Projektierer, Netzbetreiber,
Endkunde/Investor, Parkbetreiber).

Done-Gate Sprint 1 (verbindlich pro Report):
1. Pflichtinhalte (Eingaben, Standort, Leistung, Score)
2. Transparenzblock (Annahmen, Unsicherheiten, Warnungen)
3. Revisionssicherheit (Hash, UTC, App-Version, Norm-Version)
4. Datenquellen-Block (Quellen + Stand)
5. N-1 deklariert (Level + Aussagegrenzen)
6. Disclaimer
7. Formatqualitaet (Einheiten konsistent)
8. Realfall-Test
9. Smoke-Test
10. Meilenstein-Sicherung
"""
from engine.stakeholder_reports.base import StakeholderReport, ReportKontext

__all__ = ["StakeholderReport", "ReportKontext"]
