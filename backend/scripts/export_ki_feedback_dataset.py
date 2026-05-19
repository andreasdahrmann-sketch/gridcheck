"""
Export-Stub: KI-Feedback + Metadaten fuer Offline-Auswertung (Phase 1 Roadmap).

Ersetzt keine deterministische Engine. Erfordert DATABASE_URL und migrierte DB.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# backend/ als CWD vorausgesetzt
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text


def main() -> int:
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        print("ERROR: DATABASE_URL nicht gesetzt.", file=sys.stderr)
        return 1

    out_dir = Path("daten/exports")
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    out_path = out_dir / f"ki_feedback_{stamp}.jsonl"

    engine = create_engine(database_url)
    query = text(
        """
        SELECT feedback_nummer, timestamp, revision_hash, schema_version, data_json, hash
        FROM ki_feedback_records
        ORDER BY feedback_nummer
        """
    )

    count = 0
    with engine.connect() as conn, out_path.open("w", encoding="utf-8") as fh:
        for row in conn.execute(query).mappings():
            record = {
                "feedback_nummer": row["feedback_nummer"],
                "timestamp": row["timestamp"].isoformat() if row["timestamp"] else None,
                "revision_hash": row["revision_hash"],
                "schema_version": row["schema_version"],
                "data_json": row["data_json"],
                "hash": row["hash"],
            }
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
            count += 1

    print(f"OK: {count} Zeilen -> {out_path}")
    print("Hinweis: Human-Review-Gate vor ML-Auswertung — siehe docs/KI_TRAINING.md Abschnitt 10.3")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
