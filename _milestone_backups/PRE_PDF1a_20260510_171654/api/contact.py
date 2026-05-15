from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from core.rate_limit import enforce_rate_limit
from services.contact_service import send_contact_mail

router = APIRouter(prefix="/api/v1/contact", tags=["contact"])


class ContactRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    email: str = Field(..., min_length=5, max_length=254)
    subject: str = Field(..., min_length=3, max_length=140)
    message: str = Field(..., min_length=10, max_length=4000)
    website: str | None = Field(default=None, max_length=200)


@router.post("")
def submit_contact(req: ContactRequest, request: Request) -> dict[str, str]:
    if req.website:
        return {"status": "ok"}
    email_key = req.email.strip().lower()
    client_ip = request.client.host if request.client else "unknown"
    enforce_rate_limit(f"contact:email:{email_key}", limit=5, window_seconds=300)
    enforce_rate_limit(f"contact:ip:{client_ip}", limit=20, window_seconds=300)
    send_contact_mail(sender_email=req.email, name=req.name, subject=req.subject, message=req.message)
    return {"status": "ok"}
