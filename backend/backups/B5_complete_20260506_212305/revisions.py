"""
B.4 - Revisions-Verify-Endpoints (read-only)

Externe Auditoren / Netzbetreiber koennen die Integritaet der
Revisionskette pruefen, ohne Code-Zugriff zu benoetigen.

Auth: offen in B.4 (read-only, keine PII).
      Wird in Phase C abgesichert.
"""
from fastapi import APIRouter, HTTPException
from engine.revision import pruefe_integritaet, lade_revisionen

router = APIRouter(prefix="/api/v2/revisions", tags=["revisions"])


@router.get("/verify")
def verify_chain():
    """Prueft die komplette Hash-Chain auf Integritaet."""
    res = pruefe_integritaet()
    return {
        "ok": res["ok"],
        "anzahl": res["anzahl"],
        "fehler": res["fehler"],
        "engine_versions": res["engine_versions"],
    }


@router.get("/count")
def count_revisions():
    """Schnelle Anzahl + letzte Revisionsnummer."""
    revs = lade_revisionen()
    if not revs:
        return {"anzahl": 0, "letzte_revisionsnummer": None, "letzter_hash": None}
    last = revs[-1]
    return {
        "anzahl": len(revs),
        "letzte_revisionsnummer": last.get("revisionsnummer"),
        "letzter_hash": last.get("hash"),
    }


@router.get("/{hash_value}")
def get_revision_by_hash(hash_value: str):
    """Holt einen Revisionseintrag per vollem SHA-256."""
    if len(hash_value) != 64 or not all(c in "0123456789abcdef" for c in hash_value.lower()):
        raise HTTPException(status_code=400, detail="Ungueltiger SHA-256 Hash (64 hex chars erforderlich)")

    revs = lade_revisionen()
    for r in revs:
        if r.get("hash") == hash_value.lower():
            return r
    raise HTTPException(status_code=404, detail="Revision nicht gefunden")
