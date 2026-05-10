"""
Compliance-Modul: Zentrale Verwaltung aller relevanten Normen, Richtlinien
und Gesetze fuer Netzanschluss, Netzplanung und Erzeugungsanlagen.

Pflicht laut Cursor Rule "Normen- & Richtlinien-Compliance":
- Jede Berechnung referenziert Norm + Stand
- Jeder PDF-Report weist verwendete Normen aus
- Keine Bewertung ohne nachvollziehbare normative Grundlage
"""
from compliance.norm_registry import (
    NORMEN,
    get_norm,
    get_normen_fuer_spannungsebene,
    APP_VERSION_NORMSTAND,
)

__all__ = [
    "NORMEN",
    "get_norm",
    "get_normen_fuer_spannungsebene",
    "APP_VERSION_NORMSTAND",
]
