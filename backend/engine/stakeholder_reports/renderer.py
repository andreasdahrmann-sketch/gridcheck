from __future__ import annotations

import hashlib
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

REPORT_REV_PATH = os.path.join("daten", "report_revisionen.jsonl")
REPORT_SCHEMA_VERSION = "1.0.0"


def _canonical(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256(obj: Any) -> str:
    return hashlib.sha256(_canonical(obj).encode("utf-8")).hexdigest()


def _template_env() -> Environment:
    base_dir = Path(__file__).resolve().parent / "templates"
    return Environment(
        loader=FileSystemLoader(str(base_dir)),
        autoescape=select_autoescape(["html", "xml"]),
    )


def render_from_template(template_filename: str, report_data: dict[str, Any]) -> str:
    env = _template_env()
    tpl = env.get_template(template_filename)
    return tpl.render(report=report_data)


def render_projektierer_html(report_data: dict[str, Any]) -> str:
    return render_from_template("projektierer.html.j2", report_data)


def render_vnb_html(report_data: dict[str, Any]) -> str:
    return render_from_template("vnb.html.j2", report_data)


def render_invest_html(report_data: dict[str, Any]) -> str:
    return render_from_template("invest.html.j2", report_data)


def _last_hash(path: str) -> str:
    if not os.path.exists(path):
        return "GENESIS"
    last = "GENESIS"
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                last = json.loads(line).get("hash", last)
            except Exception:
                continue
    return last


def persist_report_revision(
    report_data: dict[str, Any],
    html: str,
    engine_revision_hash: str | None,
    report_type: str = "projektierer",
) -> dict[str, Any]:
    os.makedirs("daten", exist_ok=True)
    previous = _last_hash(REPORT_REV_PATH)
    payload = {
        "revisionsnummer": int(datetime.now(timezone.utc).timestamp() * 1000),
        "uuid": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "schema_version": REPORT_SCHEMA_VERSION,
        "report_type": report_type,
        "previous_hash": previous,
        "engine_revision_hash": engine_revision_hash,
        "daten": {"report": report_data, "html": html},
    }
    payload_hash = _sha256(payload)
    payload["hash"] = payload_hash
    with open(REPORT_REV_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    return {
        "hash": payload_hash,
        "uuid": payload["uuid"],
        "timestamp": payload["timestamp"],
        "engine_revision_hash": engine_revision_hash,
    }

