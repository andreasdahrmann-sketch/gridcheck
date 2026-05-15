from __future__ import annotations

from typing import Any

from core.errors import AnalysisError
from engine.revision import lade_revisionen, pruefe_integritaet


def verify_revisions_chain() -> dict[str, Any]:
    res = pruefe_integritaet()
    return {
        "ok": res["ok"],
        "anzahl": res["anzahl"],
        "fehler": res["fehler"],
        "engine_versions": res["engine_versions"],
    }


def count_revisions() -> dict[str, Any]:
    revs = lade_revisionen()
    if not revs:
        return {"anzahl": 0, "letzte_revisionsnummer": None, "letzter_hash": None}
    last = revs[-1]
    return {
        "anzahl": len(revs),
        "letzte_revisionsnummer": last.get("revisionsnummer"),
        "letzter_hash": last.get("hash"),
    }


def get_revision_by_hash(hash_value: str) -> dict[str, Any]:
    if len(hash_value) != 64 or not all(c in "0123456789abcdef" for c in hash_value.lower()):
        raise AnalysisError(
            code="REVISION_HASH_INVALID",
            message="Ungueltiger SHA-256 Hash (64 hex chars erforderlich)",
            hint="Bitte den vollen 64-stelligen Hash in Hex-Notation verwenden.",
            http_status=400,
        )

    revs = lade_revisionen()
    for r in revs:
        if r.get("hash") == hash_value.lower():
            return r

    raise AnalysisError(
        code="REVISION_NOT_FOUND",
        message="Revision nicht gefunden",
        hint="Pruefen Sie den Hash oder nutzen Sie /api/v1/revisions/count.",
        http_status=404,
    )
