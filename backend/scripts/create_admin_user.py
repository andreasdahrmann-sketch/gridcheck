#!/usr/bin/env python3
"""
Internen Admin-Nutzer anlegen oder Passwort/Rolle aktualisieren.

Admin-Konten sind ueber /api/v1/auth/register gesperrt (ADMIN_SELF_REGISTRATION_FORBIDDEN).
Dieses Skript ist der vorgesehene Ops-Weg fuer Vorprovisionierung.

Ausfuehrung (Repo-Root oder backend/):
  # Passwort nur per ENV oder Argument — nie ins Repo committen
  $env:ADMIN_PASSWORD="Admin2026!"    # min. 8 Zeichen + Komplexitaet (internes Ops-Skript)
  python backend/scripts/create_admin_user.py

  python backend/scripts/create_admin_user.py --email admin@gridcheck.de --password-env ADMIN_PASSWORD

Railway (Production, einmalig):
  railway link -p <project> -s gridcheck -e production
  railway run python scripts/create_admin_user.py --email admin@gridcheck.de --password-env ADMIN_PASSWORD
  (ADMIN_PASSWORD vorher als temporaere Railway-Variable setzen oder interaktiv per lokalem ENV)

Hinweis: Login erlaubt min. 8 Zeichen; Anlage/Reset verlangt dieselbe Policy wie Register (12+ Zeichen).
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[1]
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from sqlalchemy.orm import Session

from core.auth import hash_password
from db.database import SessionLocal
from db.models import User
def validate_admin_provisioning_password(password: str) -> None:
    """Internal ops only: login floor (8+) with complexity, not public register (12+)."""
    has_upper = any(ch.isupper() for ch in password)
    has_lower = any(ch.islower() for ch in password)
    has_digit = any(ch.isdigit() for ch in password)
    has_special = any(not ch.isalnum() for ch in password)
    if len(password) < 8 or not (has_upper and has_lower and has_digit and has_special):
        raise ValueError(
            "Passwort erfuellt interne Admin-Anforderungen nicht: "
            "mindestens 8 Zeichen sowie Gross-/Kleinbuchstaben, Zahl und Sonderzeichen."
        )


def provision_admin_user(
    db: Session,
    *,
    email: str,
    password: str,
    full_name: str | None,
    update_password: bool,
) -> tuple[User, str]:
    """Create or update admin user. Returns (user, action)."""
    validate_admin_provisioning_password(password)
    normalized_email = email.strip().lower()
    user = db.query(User).filter(User.email == normalized_email).first()
    if user is None:
        user = User(
            email=normalized_email,
            password_hash=hash_password(password),
            role="admin",
            full_name=full_name,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user, "created"

    changed = False
    if user.role != "admin":
        user.role = "admin"
        changed = True
    if not user.is_active:
        user.is_active = True
        changed = True
    if full_name is not None and user.full_name != full_name:
        user.full_name = full_name
        changed = True
    if update_password:
        user.password_hash = hash_password(password)
        changed = True
    if changed:
        db.commit()
        db.refresh(user)
        return user, "updated"
    return user, "unchanged"


def main() -> int:
    parser = argparse.ArgumentParser(description="Admin-Nutzer intern vorprovisionieren.")
    parser.add_argument("--email", default=os.environ.get("ADMIN_EMAIL", "admin@gridcheck.de"))
    parser.add_argument(
        "--password-env",
        default="ADMIN_PASSWORD",
        help="Name der Umgebungsvariable mit dem Klartext-Passwort (Default: ADMIN_PASSWORD)",
    )
    parser.add_argument("--password", default=None, help="Passwort direkt (nicht fuer Shell-History empfohlen)")
    parser.add_argument("--full-name", default=os.environ.get("ADMIN_FULL_NAME", "GridCheck Admin"))
    parser.add_argument(
        "--update-password",
        action="store_true",
        help="Bestehenden Nutzer: Passwort setzen und Rolle admin erzwingen",
    )
    args = parser.parse_args()

    password = args.password or os.environ.get(args.password_env, "").strip()
    if not password:
        print(
            f"FEHLER: Passwort fehlt. Setze ${args.password_env} oder --password.",
            file=sys.stderr,
        )
        return 2

    db = SessionLocal()
    try:
        user, action = provision_admin_user(
            db,
            email=args.email,
            password=password,
            full_name=args.full_name,
            update_password=args.update_password,
        )
    except Exception as exc:
        print(f"FEHLER: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()

    print(f"[OK] Admin {action}: id={user.id} email={user.email} role={user.role}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
