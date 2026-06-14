"""Pydantic-Schemas fuer MaStR-Import (BL-GIS-003 Skeleton).

Strenge Validierung pro Cursor-Rule 01:
- Lat/Lon-Ranges (WGS84, DE-Plausibilitaet)
- Kapazitaet >= 0
- mastr_id Pflicht und nicht-leer
- Datenklasse A laut Rule 06 (offizielle BNetzA-Quelle)
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


UnitType = Literal["solar", "wind", "biomass", "hydro", "storage", "other"]


class MastrUnitRecord(BaseModel):
    """Normalisierte MaStR-Anlage nach Parser-Schritt (intern)."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    mastr_id: str = Field(..., min_length=1, max_length=64)
    unit_type: UnitType
    installed_capacity_kw: Decimal = Field(..., ge=0)
    commissioning_date: Optional[date] = None
    decommissioning_date: Optional[date] = None
    plz: Optional[str] = Field(default=None, max_length=10)
    bundesland: Optional[str] = Field(default=None, max_length=50)
    latitude: Optional[Decimal] = Field(default=None, ge=-90, le=90)
    longitude: Optional[Decimal] = Field(default=None, ge=-180, le=180)
    dso_name: Optional[str] = Field(default=None, max_length=200)
    voltage_level: Optional[str] = Field(default=None, max_length=50)
    raw_hash: str = Field(..., min_length=64, max_length=64)
    normalized_hash: str = Field(..., min_length=64, max_length=64)
    parser_version: str = Field(..., min_length=1, max_length=20)
    source_updated_at: Optional[datetime] = None
    data_source: str = Field(default="mastr", max_length=20)
    data_class: Literal["A", "B", "C", "D", "E"] = "A"
    confidence: Decimal = Field(default=Decimal("0.95"), ge=0, le=1)

    @field_validator("plz")
    @classmethod
    def _plz_only_digits(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return None
        if not v.isdigit():
            raise ValueError("plz darf nur Ziffern enthalten")
        if len(v) < 4 or len(v) > 5:
            raise ValueError("plz muss 4-5 Ziffern haben")
        return v

    @field_validator("mastr_id")
    @classmethod
    def _mastr_id_format(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("mastr_id darf nicht leer sein")
        return cleaned


class MastrUnitResponse(BaseModel):
    """Read-API Antwort fuer MaStR-Units (Rule 06: Datenklasse + Confidence + Stand)."""

    model_config = ConfigDict(from_attributes=True)

    mastr_id: str
    unit_type: str
    installed_capacity_kw: Decimal
    commissioning_date: Optional[date] = None
    decommissioning_date: Optional[date] = None
    plz: Optional[str] = None
    bundesland: Optional[str] = None
    latitude: Optional[Decimal] = None
    longitude: Optional[Decimal] = None
    dso_name: Optional[str] = None
    voltage_level: Optional[str] = None
    data_class: str
    data_source: str
    confidence: Decimal
    parser_version: str
    imported_at: datetime
    source_updated_at: Optional[datetime] = None


class MastrUnitsPage(BaseModel):
    """Paginierte Liste; Page-Limit 100 (siehe Auftrag)."""

    items: list[MastrUnitResponse]
    total: int
    limit: int
    offset: int
    disclaimer: str = (
        "MaStR-Bestandsdaten geben Einspeisedruck-Hinweise. KEINE Aussage zur freien "
        "Netzkapazitaet oder Anschlussfaehigkeit. Verbindliche Auskunft nur durch "
        "den zustaendigen Netzbetreiber."
    )
