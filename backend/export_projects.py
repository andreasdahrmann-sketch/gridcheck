"""Einmal-Export der bestehenden Test-Projekte als JSON-Demos."""
import json
from datetime import datetime
from pathlib import Path
from db.database import SessionLocal
from db.models import Project

OUTPUT = Path(__file__).parent / "projects_test_export.json"

def export():
    db = SessionLocal()
    try:
        projects = db.query(Project).all()
        data = []
        for p in projects:
            row = {}
            for col in p.__table__.columns:
                val = getattr(p, col.name)
                if isinstance(val, datetime):
                    val = val.isoformat()
                row[col.name] = val
            data.append(row)

        OUTPUT.write_text(
            json.dumps(data, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8"
        )
        print(f"OK - {len(data)} Projekte exportiert nach: {OUTPUT}")
    finally:
        db.close()

if __name__ == "__main__":
    export()
