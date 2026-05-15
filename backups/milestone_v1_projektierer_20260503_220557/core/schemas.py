from __future__ import annotations

from typing import Optional

from pydantic import Field

from api.analyze_v2 import AnalyzeRequest


class ProjektiererRequest(AnalyzeRequest):
    """Engine-Eingabe wie v2 plus Projektierer-Constraints (keine Engine-Pflichtfelder)."""

    budget_eur: Optional[float] = Field(default=None, ge=0)
    zeitfenster_monate: Optional[int] = Field(default=None, ge=1, le=600)
    flex_leistung: bool = False
    flex_zeitfenster: bool = False
    flex_standort: bool = False
