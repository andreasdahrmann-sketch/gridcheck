#!/usr/bin/env python3
"""Run Alembic migrations at container start (Railway). Idempotent if already at head."""
from __future__ import annotations

import os
import subprocess
import sys

from sqlalchemy import create_engine, text


def _schema_ok() -> bool:
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        return False
    engine = create_engine(url)
    with engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_schema='public' AND table_name='users' "
                "AND column_name='password_hash'"
            )
        ).first()
        return row is not None


def main() -> int:
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        check=False,
        capture_output=True,
    )
    if result.returncode == 0:
        if _schema_ok():
            print("alembic upgrade head: OK")
            return 0
        print(
            "alembic upgrade head: keine Aenderung, aber Schema veraltet "
            "(evtl. `alembic stamp head` ohne Migration).",
            file=sys.stderr,
        )
        return 1
    out = result.stdout.decode("utf-8", errors="replace") + result.stderr.decode(
        "utf-8", errors="replace"
    )
    if "already exists" in out.lower() or "duplicatetable" in out.lower():
        print("alembic upgrade head: tables exist, stamping head")
        stamp = subprocess.run([sys.executable, "-m", "alembic", "stamp", "head"], check=False)
        return 0 if stamp.returncode == 0 else stamp.returncode
    print(out, file=sys.stderr)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
