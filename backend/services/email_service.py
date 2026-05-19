from __future__ import annotations

import logging
import os
import smtplib
from email.message import EmailMessage

import httpx

from core.config import settings

logger = logging.getLogger(__name__)


def _smtp_host() -> str | None:
    return (os.getenv("SMTP_HOST") or os.getenv("CONTACT_SMTP_HOST") or "").strip() or None


def _resend_api_key() -> str | None:
    return os.getenv("RESEND_API_KEY", "").strip() or None


def _from_email() -> str:
    return (
        os.getenv("EMAIL_FROM", "").strip()
        or os.getenv("CONTACT_SMTP_USER", "").strip()
        or "noreply@gridcheck.de"
    )


def _delivery_configured() -> bool:
    return bool(_resend_api_key() or _smtp_host())


def _welcome_enabled() -> bool:
    raw = os.getenv("EMAIL_SEND_WELCOME", "true").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def send_transactional_email(
    *,
    to_email: str,
    subject: str,
    body: str,
    template: str,
) -> bool:
    """
    Transaktionale E-Mails (Registrierung, Passwort-Reset).

    - dev/test ohne Provider: strukturiertes Log (kein Fehler)
    - prod/staging: Resend (RESEND_API_KEY) oder SMTP (SMTP_HOST / CONTACT_SMTP_*)
    """
    normalized_to = to_email.strip().lower()
    if not normalized_to:
        return False

    if settings.app_env in {"dev", "test"} and not _delivery_configured():
        logger.info(
            "email_stub template=%s to=%s subject=%s body_preview=%s",
            template,
            normalized_to,
            subject,
            body[:240].replace("\n", " "),
        )
        return True

    if _resend_api_key():
        return _send_via_resend(
            to_email=normalized_to,
            subject=subject,
            body=body,
            template=template,
        )

    smtp_host = _smtp_host()
    if smtp_host:
        return _send_via_smtp(
            smtp_host=smtp_host,
            to_email=normalized_to,
            subject=subject,
            body=body,
            template=template,
        )

    logger.warning("email_skip template=%s reason=no_provider to=%s", template, normalized_to)
    return False


def _send_via_resend(*, to_email: str, subject: str, body: str, template: str) -> bool:
    api_key = _resend_api_key()
    if not api_key:
        return False

    payload = {
        "from": _from_email(),
        "to": [to_email],
        "subject": subject,
        "text": body,
    }
    try:
        response = httpx.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload,
            timeout=15.0,
        )
        response.raise_for_status()
        logger.info("email_sent provider=resend template=%s to=%s", template, to_email)
        return True
    except Exception:
        logger.exception("email_failed provider=resend template=%s to=%s", template, to_email)
        return False


def _send_via_smtp(*, smtp_host: str, to_email: str, subject: str, body: str, template: str) -> bool:
    smtp_port = int(os.getenv("SMTP_PORT") or os.getenv("CONTACT_SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER") or os.getenv("CONTACT_SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD") or os.getenv("CONTACT_SMTP_PASSWORD")

    email = EmailMessage()
    email["Subject"] = subject
    email["From"] = _from_email()
    email["To"] = to_email
    email.set_content(body)

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
            server.starttls()
            if smtp_user and smtp_password:
                server.login(smtp_user, smtp_password)
            server.send_message(email)
        logger.info("email_sent provider=smtp template=%s to=%s", template, to_email)
        return True
    except Exception:
        logger.exception("email_failed provider=smtp template=%s to=%s", template, to_email)
        return False


def send_welcome_email(*, to_email: str, full_name: str | None) -> bool:
    if not _welcome_enabled():
        logger.info("email_skip template=welcome reason=EMAIL_SEND_WELCOME=false to=%s", to_email)
        return True

    greeting = full_name.strip() if full_name and full_name.strip() else "Nutzerin/Nutzer"
    body = (
        f"Hallo {greeting},\n\n"
        "Ihr GridCheck-Konto wurde angelegt. Sie können sich jetzt anmelden und "
        "vorläufige Netzanschluss-Checks starten.\n\n"
        "Hinweis: GridCheck liefert keine verbindliche Netzanschlusszusage.\n\n"
        "Viele Grüße\nIhr GridCheck-Team"
    )
    return send_transactional_email(
        to_email=to_email,
        subject="Willkommen bei GridCheck",
        body=body,
        template="welcome",
    )


def send_password_reset_email(*, to_email: str, reset_url: str) -> bool:
    body = (
        "Sie haben eine Zurücksetzung Ihres GridCheck-Passworts angefordert.\n\n"
        f"Link (zeitlich begrenzt gültig): {reset_url}\n\n"
        "Falls Sie das nicht waren, ignorieren Sie diese E-Mail.\n\n"
        "Viele Grüße\nIhr GridCheck-Team"
    )
    return send_transactional_email(
        to_email=to_email,
        subject="GridCheck – Passwort zurücksetzen",
        body=body,
        template="password_reset",
    )
