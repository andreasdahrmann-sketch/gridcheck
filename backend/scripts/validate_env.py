#!/usr/bin/env python3
"""
Prueft Backend-.env vor Deploy (Auth, DB, optional Stripe/SMTP).

Beispiel:
  cd backend
  python scripts/validate_env.py
  python scripts/validate_env.py --env-file .env.prod.example --expect-prod
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]


def _load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        key, _, value = s.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


def _check(name: str, ok: bool, detail: str = "", *, required: bool = True) -> bool:
    tag = "OK" if ok else ("FAIL" if required else "WARN")
    suffix = f" — {detail}" if detail else ""
    print(f"[{tag}] {name}{suffix}")
    return ok or not required


def main() -> int:
    parser = argparse.ArgumentParser(description="GridCheck Backend ENV validation")
    parser.add_argument("--env-file", default=".env", help="Pfad zur .env (relativ zu backend/)")
    parser.add_argument(
        "--expect-prod",
        action="store_true",
        help="Prod-Pflichtfelder pruefen (APP_ENV prod/staging)",
    )
    args = parser.parse_args()

    env_path = BACKEND_ROOT / args.env_file
    if env_path.is_file():
        _load_dotenv(env_path)
        print(f"Lade {env_path}")
    else:
        print(f"Keine Datei {env_path} — nutze bereits gesetzte Umgebungsvariablen.")

    failures = 0
    app_env = os.getenv("APP_ENV", "dev").strip().lower()
    is_prod_like = args.expect_prod or app_env in {"prod", "production", "staging"}

    failures += 0 if _check("DATABASE_URL", bool(os.getenv("DATABASE_URL")), "PostgreSQL-URL") else 1
    failures += (
        0
        if _check(
            "JWT_SECRET",
            bool(os.getenv("JWT_SECRET")) and len(os.getenv("JWT_SECRET", "")) >= 32,
            "min. 32 Zeichen",
            required=is_prod_like,
        )
        else 1
    )
    failures += (
        0
        if _check(
            "JWT_REFRESH_SECRET",
            bool(os.getenv("JWT_REFRESH_SECRET"))
            and os.getenv("JWT_REFRESH_SECRET") != os.getenv("JWT_SECRET")
            and len(os.getenv("JWT_REFRESH_SECRET", "")) >= 32,
            "eigener Wert, min. 32 Zeichen",
            required=is_prod_like,
        )
        else 1
    )

    cors_ok = bool(os.getenv("CORS_ORIGINS") or os.getenv("CORS_ORIGIN_REGEX"))
    failures += 0 if _check("CORS_ORIGINS oder CORS_ORIGIN_REGEX", cors_ok, required=is_prod_like) else 1

    trusted = os.getenv("TRUSTED_HOSTS", "")
    failures += (
        0
        if _check("TRUSTED_HOSTS", bool(trusted), trusted[:80] if trusted else "leer", required=is_prod_like)
        else 1
    )

    stripe_key = os.getenv("STRIPE_SECRET_KEY", "").strip()
    stripe_prices = [
        ("STRIPE_PRICE_BASIC_ID", os.getenv("STRIPE_PRICE_BASIC_ID")),
        ("STRIPE_PRICE_PREMIUM_ID", os.getenv("STRIPE_PRICE_PREMIUM_ID")),
        ("STRIPE_PRICE_PROFESSIONAL_ID", os.getenv("STRIPE_PRICE_PROFESSIONAL_ID")),
    ]
    stripe_partial = bool(stripe_key) or any(p for _, p in stripe_prices if p)
    if stripe_partial and not stripe_key:
        failures += 0 if _check("STRIPE_SECRET_KEY", False, "fehlt, aber Price-IDs gesetzt") else 1
    else:
        _check("STRIPE_SECRET_KEY", bool(stripe_key), "optional — ohne Key kein Checkout", required=False)

    for label, val in stripe_prices:
        _check(label, bool(val) if stripe_key else True, "leer" if not val else "gesetzt", required=False)

    smtp_host = os.getenv("CONTACT_SMTP_HOST", "").strip()
    _check(
        "CONTACT_SMTP_*",
        bool(smtp_host) and smtp_host != "smtp.example.com",
        "optional — Kontaktformular",
        required=False,
    )

    if is_prod_like:
        try:
            sys.path.insert(0, str(BACKEND_ROOT))
            from core.config import load_settings

            load_settings()
            _check("load_settings()", True, "Pydantic/Stripe-Validierung")
        except Exception as exc:
            failures += 1
            _check("load_settings()", False, str(exc))

    if failures:
        print(f"\n{failures} Pflichtproblem(e). Siehe docs/RAILWAY_ENV_SETUP.md", file=sys.stderr)
        return 1
    print("\nENV-Pruefung bestanden (optionale WARNs beachten).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
