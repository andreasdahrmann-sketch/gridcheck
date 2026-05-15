"""
Revisionssicheres Audit-Log (GoBD-konform).
Version: revision-2.0.0
"""
from __future__ import annotations

import json
import os
import hashlib
import uuid
import tempfile
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

SCHEMA_VERSION = "2.0.0"
REVISIONS_PFAD = os.path.join("daten", "revisionen.jsonl")
LEGACY_PFAD = os.path.join("daten", "revisionen.json")


def _kanonisiere(daten: Dict[str, Any]) -> str:
    return json.dumps(daten, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _hash(daten: Dict[str, Any]) -> str:
    return hashlib.sha256(_kanonisiere(daten).encode("utf-8")).hexdigest()


def _ensure_dir() -> None:
    os.makedirs("daten", exist_ok=True)


def _migriere_legacy_falls_noetig() -> None:
    if os.path.exists(REVISIONS_PFAD):
        return
    if not os.path.exists(LEGACY_PFAD):
        return
    try:
        with open(LEGACY_PFAD, "r", encoding="utf-8") as f:
            alt = json.load(f)
        if not isinstance(alt, list):
            return
        _ensure_dir()
        with open(REVISIONS_PFAD, "w", encoding="utf-8") as f:
            for eintrag in alt:
                f.write(json.dumps(eintrag, ensure_ascii=False) + "\n")
        os.replace(LEGACY_PFAD, LEGACY_PFAD + ".migrated")
    except Exception:
        pass


def _letzter_hash() -> str:
    if not os.path.exists(REVISIONS_PFAD):
        return "GENESIS"
    last = "GENESIS"
    with open(REVISIONS_PFAD, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                eintrag = json.loads(line)
                last = eintrag.get("hash", last)
            except Exception:
                continue
    return last


def _zaehle_revisionen() -> int:
    if not os.path.exists(REVISIONS_PFAD):
        return 0
    n = 0
    with open(REVISIONS_PFAD, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                n += 1
    return n


def _atomares_append(eintrag: Dict[str, Any]) -> None:
    _ensure_dir()
    bestehend = ""
    if os.path.exists(REVISIONS_PFAD):
        with open(REVISIONS_PFAD, "r", encoding="utf-8") as f:
            bestehend = f.read()
    fd, tmp = tempfile.mkstemp(prefix=".rev_", dir="daten", text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            if bestehend:
                f.write(bestehend)
                if not bestehend.endswith("\n"):
                    f.write("\n")
            f.write(json.dumps(eintrag, ensure_ascii=False) + "\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, REVISIONS_PFAD)
    except Exception:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except Exception:
                pass
        raise


def speichere_revision(
    ergebnis: Dict[str, Any],
    dry_run: bool = False,
    engine_version: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Append-only Audit-Log mit Hash-Kette.
    dry_run=True: berechnet Hash, schreibt aber NICHT (fuer Tests).
    """
    _migriere_legacy_falls_noetig()

    prev = _letzter_hash()
    rev_nr = _zaehle_revisionen() + 1

    if engine_version is None:
        try:
            from engine.berechnung import ENGINE_VERSION as _EV
            engine_version = _EV
        except Exception:
            engine_version = "unknown"

    eintrag = {
        "revisionsnummer": rev_nr,
        "uuid": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "schema_version": SCHEMA_VERSION,
        "engine_version": engine_version,
        "previous_hash": prev,
        "daten": {
            "eingabe": ergebnis.get("eingabe", {}),
            "fazit": ergebnis.get("fazit", {}),
            "scores": ergebnis.get("scores", {}),
            "thermisch": ergebnis.get("thermisch", {}),
            "spannung": ergebnis.get("spannung", {}),
            "kurzschluss": ergebnis.get("kurzschluss", {}),
            "n1": ergebnis.get("n1", {}),
            "trafo": ergebnis.get("trafo", {}),
            "impedanz": ergebnis.get("impedanz", {}),
            "pqs": ergebnis.get("pqs", {}),
            "datenqualitaet": ergebnis.get("datenqualitaet", {}),
            "warnungen": ergebnis.get("warnungen", []),
            "empfehlungen": ergebnis.get("empfehlungen", []),
            "ki": ergebnis.get("ki", {}),
            "nb_check": ergebnis.get("nb_check", {}),
        },
    }

    h = _hash(eintrag)
    eintrag["hash"] = h

    meta = {
        "revisionsnummer": rev_nr,
        "uuid": eintrag["uuid"],
        "timestamp": eintrag["timestamp"],
        "schema_version": SCHEMA_VERSION,
        "engine_version": engine_version,
        "previous_hash": prev,
        "hash": h,
        "dry_run": dry_run,
    }

    if dry_run:
        return meta

    _atomares_append(eintrag)
    return meta


def lade_revisionen() -> List[Dict[str, Any]]:
    _migriere_legacy_falls_noetig()
    if not os.path.exists(REVISIONS_PFAD):
        return []
    out: List[Dict[str, Any]] = []
    with open(REVISIONS_PFAD, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except Exception:
                continue
    return out


def pruefe_integritaet() -> Dict[str, Any]:
    """Streaming-Verify der Hash-Kette."""
    fehler: List[str] = []
    engine_versions: Dict[str, int] = {}
    anzahl = 0
    prev = "GENESIS"

    if not os.path.exists(REVISIONS_PFAD):
        return {"ok": True, "anzahl": 0, "fehler": [], "engine_versions": {}}

    with open(REVISIONS_PFAD, "r", encoding="utf-8") as f:
        for i, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            anzahl += 1
            try:
                eintrag = json.loads(line)
            except Exception as e:
                fehler.append(f"Zeile {i}: JSON kaputt ({e})")
                continue

            ev = eintrag.get("engine_version", "unknown")
            engine_versions[ev] = engine_versions.get(ev, 0) + 1

            gespeicherter_hash = eintrag.get("hash")
            if eintrag.get("previous_hash") != prev:
                fehler.append(f"Zeile {i}: previous_hash-Bruch (erwartet {prev[:12]}, war {str(eintrag.get('previous_hash'))[:12]})")

            ohne_hash = {k: v for k, v in eintrag.items() if k != "hash"}
            recomputed = _hash(ohne_hash)
            if recomputed != gespeicherter_hash:
                fehler.append(f"Zeile {i}: Hash-Mismatch")

            prev = gespeicherter_hash or prev

    return {"ok": len(fehler) == 0, "anzahl": anzahl, "fehler": fehler, "engine_versions": engine_versions}
