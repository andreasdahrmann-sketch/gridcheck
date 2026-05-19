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


class OsmNearbyAsset(BaseModel):
    """Ein OSM-Infrastrukturhinweis im Umkreis (keine Kapazitaetsaussage)."""

    type: str = Field(..., description="Normalisierter Asset-Typ, z. B. substation, transformer.")
    name: str | None = Field(default=None, description="Anzeigename aus OSM-Tags, falls vorhanden.")
    lat: float = Field(..., description="Breitengrad WGS84.")
    lon: float = Field(..., description="Laengengrad WGS84.")
    distance_m: float = Field(..., ge=0, description="Luftlinie zum Suchmittelpunkt in Metern.")
    osm_id: str | None = Field(default=None, description="OSM-Element-ID (node/way/relation).")
    tags_summary: str | None = Field(
        default=None,
        description="Kurzfassung relevanter OSM-Tags ohne Kapazitaets-Claims.",
    )


class OsmNearbyResponse(BaseModel):
    """Antwort fuer GET /api/v1/geo/osm-nearby."""

    center_lat: float
    center_lon: float
    radius_m: int = Field(..., ge=100, le=15_000)
    plz: str | None = Field(default=None, description="Optionale PLZ-Kontextangabe.")
    assets: List[OsmNearbyAsset] = Field(default_factory=list)
    source: str = Field(default="OSM", description="Datenquelle.")
    data_class: str = Field(default="B", description="Datenklasse gemaess Projektregeln.")
    confidence: str = Field(default="B", description="Confidence-Klasse der Gesamtaussage.")
    confidence_score: int = Field(default=60, ge=0, le=100)
    confidence_geometrisch: int = Field(default=60, ge=0, le=100)
    confidence_technisch: int = Field(default=45, ge=0, le=100)
    quelle: str = Field(..., description="Herkunft / Overpass-Instanz.")
    hinweis: str = Field(..., description="Fachlicher Hinweis ohne Kapazitaets-Claim.")
    disclaimer: str = Field(..., description="Rechtlicher/technischer Disclaimer.")
    validierungsstatus: str = Field(
        ...,
        description="OK | PARTIAL | ERROR — Verarbeitungszustand, nicht Netz-OK.",
    )
    fetched_at: str = Field(..., description="ISO-8601-Zeitstempel der Abfrage (UTC).")
    cache_hit: bool = Field(default=False, description="True, wenn Antwort aus In-Memory-Cache stammt.")
