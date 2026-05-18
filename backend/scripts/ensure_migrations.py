#!/usr/bin/env python3
"""Run Alembic migrations at container start (Railway). Idempotent if already at head."""
from __future__ import annotations

import subprocess
import sys


def main() -> int:
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        check=False,
        capture_output=True,
    )
    if result.returncode == 0:
        print("alembic upgrade head: OK")
        return 0
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
