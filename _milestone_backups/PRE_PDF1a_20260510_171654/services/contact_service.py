from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage

from fastapi import HTTPException


def send_contact_mail(*, sender_email: str, name: str, subject: str, message: str) -> None:
    smtp_host = os.getenv("CONTACT_SMTP_HOST")
    smtp_port = int(os.getenv("CONTACT_SMTP_PORT", "587"))
    smtp_user = os.getenv("CONTACT_SMTP_USER")
    smtp_password = os.getenv("CONTACT_SMTP_PASSWORD")
    recipient = os.getenv("CONTACT_TO_EMAIL")

    if not smtp_host or not recipient:
        raise HTTPException(
            status_code=500,
            detail={"code": "CONTACT_CONFIG_MISSING", "message": "Kontaktkanal nicht konfiguriert", "hint": "SMTP ENV setzen."},
        )

    email = EmailMessage()
    email["Subject"] = f"[GridCheck] {subject}"
    email["From"] = smtp_user or sender_email
    email["To"] = recipient
    email.set_content(f"Name: {name}\nE-Mail: {sender_email}\n\n{message}")

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
            server.starttls()
            if smtp_user and smtp_password:
                server.login(smtp_user, smtp_password)
            server.send_message(email)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail={"code": "CONTACT_DELIVERY_FAILED", "message": "Nachricht konnte nicht gesendet werden", "hint": "Bitte spaeter erneut versuchen."},
        ) from exc
