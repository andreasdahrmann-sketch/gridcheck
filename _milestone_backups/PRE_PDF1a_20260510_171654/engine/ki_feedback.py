from __future__ import annotations

import hashlib
import json
import os
import tempfile
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

FEEDBACK_SCHEMA_VERSION = "1.0.0"
KI_FEEDBACK_PFAD = os.path.join("daten", "ki_feedback.jsonl")

_ENTSCHEIDUNGS_MAPPING = {"A": 2, "B": 1, "C": 0}


def _ensure_dir() -> None:
    os.makedirs("daten", exist_ok=True)


def _kanonisiere(daten: Dict[str, Any]) -> str:
    return json.dumps(daten, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _hash(daten: Dict[str, Any]) -> str:
    return hashlib.sha256(_kanonisiere(daten).encode("utf-8")).hexdigest()


def _letzter_hash() -> str:
    if not os.path.exists(KI_FEEDBACK_PFAD):
        return "GENESIS"
    last = "GENESIS"
    with open(KI_FEEDBACK_PFAD, "r", encoding="utf-8") as f:
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


def _zaehle_eintraege() -> int:
    if not os.path.exists(KI_FEEDBACK_PFAD):
        return 0
    n = 0
    with open(KI_FEEDBACK_PFAD, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                n += 1
    return n


def _atomares_append(eintrag: Dict[str, Any]) -> None:
    _ensure_dir()
    bestehend = ""
    if os.path.exists(KI_FEEDBACK_PFAD):
        with open(KI_FEEDBACK_PFAD, "r", encoding="utf-8") as f:
            bestehend = f.read()

    fd, tmp = tempfile.mkstemp(prefix=".ki_fb_", dir="daten", text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            if bestehend:
                f.write(bestehend)
                if not bestehend.endswith("\n"):
                    f.write("\n")
            f.write(json.dumps(eintrag, ensure_ascii=False) + "\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, KI_FEEDBACK_PFAD)
    except Exception:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except Exception:
                pass
        raise


def _normalisiere_entscheidung(value: Any) -> Optional[str]:
    if isinstance(value, dict):
        value = value.get("entscheidung")
    if value is None:
        return None
    v = str(value).strip().upper()
    if v in _ENTSCHEIDUNGS_MAPPING:
        return v
    return None


def speichere_ki_feedback(
    *,
    ki_entscheidung: Any,
    nb_entscheidung: Any,
    kommentar: Optional[str] = None,
    revision_hash: Optional[str] = None,
    score_gesamt: Optional[float] = None,
    quelle: str = "netzbetreiber",
    dry_run: bool = False,
) -> Dict[str, Any]:
    ki_norm = _normalisiere_entscheidung(ki_entscheidung)
    nb_norm = _normalisiere_entscheidung(nb_entscheidung)
    if ki_norm is None or nb_norm is None:
        raise ValueError("ki_entscheidung und nb_entscheidung muessen A/B/C sein.")

    prev = _letzter_hash()
    nr = _zaehle_eintraege() + 1
    payload = {
        "feedback_nummer": nr,
        "uuid": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "schema_version": FEEDBACK_SCHEMA_VERSION,
        "previous_hash": prev,
        "daten": {
            "ki_entscheidung": ki_norm,
            "nb_entscheidung": nb_norm,
            "kommentar": kommentar,
            "revision_hash": revision_hash,
            "score_gesamt": score_gesamt,
            "quelle": quelle,
        },
    }
    payload["hash"] = _hash(payload)

    meta = {
        "feedback_nummer": nr,
        "uuid": payload["uuid"],
        "timestamp": payload["timestamp"],
        "schema_version": FEEDBACK_SCHEMA_VERSION,
        "previous_hash": prev,
        "hash": payload["hash"],
        "dry_run": dry_run,
    }
    if dry_run:
        return meta

    _atomares_append(payload)
    return meta


def lade_ki_feedback() -> List[Dict[str, Any]]:
    if not os.path.exists(KI_FEEDBACK_PFAD):
        return []
    out: List[Dict[str, Any]] = []
    with open(KI_FEEDBACK_PFAD, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except Exception:
                continue
    return out


def berechne_kalibrierung() -> Dict[str, Any]:
    eintraege = lade_ki_feedback()
    paare: List[tuple[int, int]] = []
    for e in eintraege:
        daten = e.get("daten", {})
        ki = _normalisiere_entscheidung(daten.get("ki_entscheidung"))
        nb = _normalisiere_entscheidung(daten.get("nb_entscheidung"))
        if ki is None or nb is None:
            continue
        paare.append((_ENTSCHEIDUNGS_MAPPING[ki], _ENTSCHEIDUNGS_MAPPING[nb]))

    if not paare:
        return {
            "samples": 0,
            "trefferquote": 0.0,
            "durchschnittlicher_fehler": 0.0,
            "kalibrierungsfaktor": 1.0,
            "status": "NO_FEEDBACK",
        }

    abs_errors = [abs(ki - nb) for ki, nb in paare]
    signed_errors = [ki - nb for ki, nb in paare]
    exact_hits = sum(1 for e in abs_errors if e == 0)
    disagreement_rate = sum(1 for e in abs_errors if e > 0) / len(abs_errors)
    avg_abs_err = sum(abs_errors) / len(abs_errors)
    avg_signed_err = sum(signed_errors) / len(signed_errors)

    # Konservative Kalibrierung: bei mehr Abweichung sinkt KI-Konfidenz.
    base_penalty = min(0.25, (avg_abs_err * 0.15) + (disagreement_rate * 0.2))
    faktor = max(0.75, round(1.0 - base_penalty, 4))

    return {
        "samples": len(paare),
        "trefferquote": round(exact_hits / len(paare), 4),
        "durchschnittlicher_fehler": round(avg_abs_err, 4),
        "bias": round(avg_signed_err, 4),
        "kalibrierungsfaktor": faktor,
        "status": "CALIBRATED",
    }


def pruefe_integritaet() -> Dict[str, Any]:
    """Verifiziert die Hash-Kette von daten/ki_feedback.jsonl."""
    fehler: List[str] = []
    anzahl = 0
    prev = "GENESIS"

    if not os.path.exists(KI_FEEDBACK_PFAD):
        return {"ok": True, "anzahl": 0, "fehler": []}

    with open(KI_FEEDBACK_PFAD, "r", encoding="utf-8") as f:
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

            gespeicherter_hash = eintrag.get("hash")
            if eintrag.get("previous_hash") != prev:
                fehler.append(
                    f"Zeile {i}: previous_hash-Bruch (erwartet {prev[:12]}, war {str(eintrag.get('previous_hash'))[:12]})"
                )

            ohne_hash = {k: v for k, v in eintrag.items() if k != "hash"}
            recomputed = _hash(ohne_hash)
            if recomputed != gespeicherter_hash:
                fehler.append(f"Zeile {i}: Hash-Mismatch")

            prev = gespeicherter_hash or prev

    return {"ok": len(fehler) == 0, "anzahl": anzahl, "fehler": fehler}
