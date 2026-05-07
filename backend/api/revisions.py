"""
B.4 - Revisions-Verify-Endpoints (read-only)
B.6 - Export-Endpoints (CSV/JSON/PDF)

Externe Auditoren / Netzbetreiber koennen die Integritaet pruefen
und audit-taugliche Exporte erzeugen.
"""
from fastapi import APIRouter, HTTPException, Response
from core.errors import AnalysisError
from services.revisions_service import (
    count_revisions as svc_count_revisions,
    get_revision_by_hash as svc_get_revision_by_hash,
    verify_revisions_chain,
)
from services.revisions_export import export_json, export_csv, export_pdf

router = APIRouter(prefix="/revisions", tags=["revisions"])


@router.get("/verify")
def verify_chain():
    """Prueft die komplette Hash-Chain auf Integritaet."""
    return verify_revisions_chain()


@router.get("/count")
def count_revisions():
    """Schnelle Anzahl + letzte Revisionsnummer."""
    return svc_count_revisions()


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
    try:
        return svc_get_revision_by_hash(hash_value)
    except AnalysisError as e:
        raise HTTPException(status_code=e.http_status, detail=e.to_dict())
