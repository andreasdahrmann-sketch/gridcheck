"""
Basisklasse fuer alle Stakeholder-Reports.
Erweiterung in MS PDF-1b: Formatters, Datenquellen, Transparenz, Disclaimer.
Erweiterung in MS PDF-1c: Engine-Output mit N-1-Level + Annahmen.
"""
from __future__ import annotations

import io
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Spacer

from core import branding as B


@dataclass
class ReportKontext:
    rolle: str
    request_data: dict[str, Any]
    result_data: dict[str, Any]
    project_id: int
    audit_id: Optional[int] = None
    checksum_sha256: Optional[str] = None
    timestamp_utc: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    )
    app_version: str = "unknown"
    pruefer_id: Optional[str] = None
    aktenzeichen: Optional[str] = None


class StakeholderReport(ABC):
    UNTERTITEL: str = "Report"

    def __init__(self, kontext: ReportKontext) -> None:
        self.k = kontext
        self.story: list[Any] = []

    def render(self) -> bytes:
        buf = io.BytesIO()
        doc = SimpleDocTemplate(
            buf, pagesize=A4,
            topMargin=15 * mm, bottomMargin=22 * mm,
            leftMargin=15 * mm, rightMargin=15 * mm,
            title=f"Adecarb GridCheck - {self.UNTERTITEL}",
            author="Adecarb",
        )
        self.story.append(B.build_header_banner(doc.width / mm, untertitel=self.UNTERTITEL))
        self.story.append(Spacer(1, 6 * mm))
        self._build_role_sections(doc)
        doc.build(self.story, onFirstPage=B.footer_callback, onLaterPages=B.footer_callback)
        return buf.getvalue()

    @abstractmethod
    def _build_role_sections(self, doc: SimpleDocTemplate) -> None:
        ...
