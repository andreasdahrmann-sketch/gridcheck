from __future__ import annotations

from typing import Any, Optional


class AnalysisError(Exception):
    """Fachliche oder Engine-Validierungsfehler mit HTTP-Mapping."""

    def __init__(
        self,
        *,
        code: str,
        message: str,
        hint: Optional[str] = None,
        http_status: int = 422,
    ) -> None:
        self.code = code
        self.message = message
        self.hint = hint
        self.http_status = http_status
        super().__init__(message)

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code, "message": self.message, "hint": self.hint}
