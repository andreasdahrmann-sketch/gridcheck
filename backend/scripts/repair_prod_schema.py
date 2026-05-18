#!/usr/bin/env python3
"""Einmalig: Prod-DB mit falschem Alembic-Stamp reparieren (nur wenn keine echten Nutzerdaten)."""
from __future__ import annotations

import os
import subprocess
import sys

from sqlalchemy import create_engine, text


def _users_schema_ok(engine) -> bool:
    with engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_schema='public' AND table_name='users' AND column_name='password_hash'"
            )
        ).first()
        return row is not None


def main() -> int:
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        print("DATABASE_URL fehlt", file=sys.stderr)
        return 1
    if os.environ.get("ALLOW_DB_RESET") != "1":
        print("Setze ALLOW_DB_RESET=1 zum Bestaetigen (loescht alle Tabellen in public).", file=sys.stderr)
        return 1

    engine = create_engine(url)
    if _users_schema_ok(engine):
        print("Schema bereits OK (users.password_hash vorhanden).")
        return 0

    print("Altes/fehlerhaftes Schema erkannt — public schema wird neu aufgebaut.")
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
        conn.execute(text("GRANT ALL ON SCHEMA public TO public"))

    result = subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], check=False)
    if result.returncode != 0:
        return result.returncode
    if not _users_schema_ok(engine):
        print("Migration abgeschlossen, aber Schema-Check fehlgeschlagen.", file=sys.stderr)
        return 1
    print("repair_prod_schema: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
