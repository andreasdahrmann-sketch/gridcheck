#!/usr/bin/env python3
"""Freischaltung eines Netzbetreiber-Kontos (Admin/CLI).

Beispiel:
  cd backend
  python -m scripts.approve_netzbetreiber --user-id 42
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[1]
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from db.database import SessionLocal
from services.auth_service import approve_netzbetreiber


def main() -> int:
    parser = argparse.ArgumentParser(description="Netzbetreiber-Konto freischalten (vnb_verification_status=approved).")
    parser.add_argument("--user-id", type=int, required=True, help="ID des Benutzers (Rolle muss netzbetreiber sein).")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        user = approve_netzbetreiber(db, user_id=args.user_id)
    except Exception as exc:
        print(f"Fehler: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()

    print(
        f"OK: user_id={user.id} email={user.email} "
        f"vnb_verification_status={user.vnb_verification_status}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
