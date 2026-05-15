"""Pydantic v2 Schemas fuer Geo-/PLZ-Lookups.

Liefert eine vorlaeufige, heuristische Zuordnung PLZ -> Verteilnetzbetreiber-
Kandidaten. Es werden keine verbindlichen Aussagen ueber Zustaendigkeit oder
Netzkapazitaet gemacht. Datenquelle und Confidence sind Teil der Antwort.
"""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class VnbCandidate(BaseModel):
    """Ein moeglicher Verteilnetzbetreiber fuer eine PLZ."""

    name: str = Field(..., description="Vollstaendiger Firmenname")
    kuerzel: str = Field(..., description="Internes Kuerzel, stabil als Schluessel")
    snap_verfuegbar: bool = Field(
        ...,
        description="True, wenn der VNB ein oeffentliches SNAP-aehnliches "
                    "Online-Vorpruefungs-Portal anbietet (Stand siehe quelle).",
    )
    snap_url: Optional[str] = Field(
        default=None,
        description="Direktlink zum SNAP-Portal des VNB, sofern verifiziert.",
    )
    hinweis: Optional[str] = Field(
        default=None,
        description="Optionaler Zusatzhinweis, z. B. Konzernzugehoerigkeit.",
    )


class PlzLookupResponse(BaseModel):
    """Antwort fuer GET /api/v1/geo/plz/{plz}.

    Confidence ist absichtlich nur 'B-heuristisch'. Eine PLZ kann mehrere
    VNB-Gebiete schneiden (Stadtwerke vs. Flaechen-VNB). Endgueltige
    Zustaendigkeit liegt beim VNB selbst.
    """

    plz: str = Field(..., description="Normalisierte 5-stellige PLZ")
    bundesland_kandidaten: List[str] = Field(
        default_factory=list,
        description="Mutmassliche Bundeslaender. Mehrere moeglich an Grenzen.",
    )
    vnb_kandidaten: List[VnbCandidate] = Field(
        default_factory=list,
        description="Moegliche zustaendige Verteilnetzbetreiber. Reihenfolge "
                    "ohne Praeferenz.",
    )
    snap_verfuegbar: bool = Field(
        ...,
        description="True, wenn mindestens ein vnb_kandidat ein SNAP-Portal hat.",
    )
    confidence: str = Field(
        default="B-heuristisch",
        description="Confidence-Klasse der Zuordnung. 'B-heuristisch' = "
                    "PLZ-Praefix-basierend, nicht parzellengenau.",
    )
    quelle: str = Field(
        ...,
        description="Beschreibung der Datenquelle (kuratierter interner Mapping-Stand).",
    )
    stand: str = Field(
        ...,
        description="ISO-Datum des Datenstands (YYYY-MM-DD).",
    )
    hinweis: str = Field(
        ...,
        description="Disclaimer fuer den Konsumenten der API.",
    )
