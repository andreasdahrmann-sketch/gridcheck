"""
B.4 - Revisions-Verify-Endpoints (read-only)
B.6 - Export-Endpoints (CSV/JSON/PDF)

Externe Auditoren / Netzbetreiber koennen die Integritaet pruefen
und audit-taugliche Exporte erzeugen.
"""
from fastapi import APIRouter, HTTPException, Response
from engine.revision import pruefe_integritaet, lade_revisionen
from services.revisions_export import export_json, export_csv, export_pdf

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


# --- B.6 Export-Endpoints (vor /{hash_value} platziert wegen Routing-Prioritaet) ---

@router.get("/export/json")
def export_revisions_json():
    """Vollstaendiger JSON-Export mit Audit-Header."""
    return export_json()


@router.get("/export/csv")
def export_revisions_csv():
    """CSV-Export (Semikolon-getrennt, Excel-kompatibel)."""
    csv_text = export_csv()
    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="gridcheck_revisionen.csv"'},
    )


@router.get("/export/pdf")
def export_revisions_pdf():
    """Audit-taugliches PDF (Querformat, Hash-Chain-Tabelle)."""
    pdf_bytes = export_pdf()
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="gridcheck_revisions_audit.pdf"'},
    )


# --- Catch-all (muss am Ende stehen) ---

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
