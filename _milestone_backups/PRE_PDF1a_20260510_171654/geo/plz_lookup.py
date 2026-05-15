"""Service-Layer fuer PLZ -> VNB-Kandidaten-Lookup.

Liest einmalig den kuratierten Datensatz `data/plz_vnb_snap.json` ein und
liefert eine validierte `PlzLookupResponse` zurueck.

Designprinzipien (laut .cursor/rules/00-gridcheck.mdc):
- Keine Kapazitaetsaussage. Nur Zuordnung PLZ -> moegliche VNB.
- Quelle, Stand und Confidence wandern in jede Antwort.
- Keine stille Annahme: PLZ ohne Treffer liefert leere Listen + Hinweis.
- Keine Businesslogik im Router; diese Datei ist die Single Source.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from core.errors import AnalysisError

from .schemas import PlzLookupResponse, VnbCandidate

_DATA_PATH = Path(__file__).parent / "data" / "plz_vnb_snap.json"


@lru_cache(maxsize=1)
def _load_dataset() -> dict[str, Any]:
    """Laedt die JSON-Datenbasis genau einmal pro Prozess."""
    if not _DATA_PATH.exists():
        raise RuntimeError(f"PLZ-VNB-Datensatz nicht gefunden: {_DATA_PATH}")
    with _DATA_PATH.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if "plz_prefix" not in data or "vnb" not in data:
        raise RuntimeError("PLZ-VNB-Datensatz hat unerwartete Struktur.")
    return data


def _normalize_plz(raw: str) -> str:
    """Pruefe Format und liefere genormte 5-stellige PLZ.

    Wirft AnalysisError(422), wenn das Format nicht stimmt. Bewusst streng:
    deutsche PLZ sind exakt 5 Ziffern.
    """
    if raw is None:
        raise AnalysisError(
            code="PLZ_INVALID",
            message="PLZ fehlt.",
            hint="Erwartet werden 5 Ziffern, z. B. 04109.",
            http_status=422,
        )
    candidate = str(raw).strip()
    if len(candidate) != 5 or not candidate.isdigit():
        raise AnalysisError(
            code="PLZ_INVALID",
            message=f"PLZ '{raw}' ist ungueltig.",
            hint="Erwartet werden genau 5 Ziffern, z. B. 04109.",
            http_status=422,
        )
    return candidate


def lookup_plz(raw_plz: str) -> PlzLookupResponse:
    """Liefert die VNB-Kandidaten fuer eine PLZ.

    Ablauf:
    1. PLZ normalisieren (genau 5 Ziffern).
    2. Praefix (erste 2 Ziffern) im kuratierten Mapping nachschlagen.
    3. Zugehoerige VNB-Kuerzel auf vollstaendige Eintraege ausrollen.
    4. `snap_verfuegbar` als Oder-Verknuepfung der VNB-Kandidaten setzen.
    """
    plz = _normalize_plz(raw_plz)
    data = _load_dataset()

    prefix = plz[:2]
    prefix_entry = data["plz_prefix"].get(prefix, {"bundesland": [], "vnb": []})

    bundesland_kandidaten = list(prefix_entry.get("bundesland", []) or [])
    vnb_kuerzel = list(prefix_entry.get("vnb", []) or [])

    vnb_dict = data["vnb"]
    vnb_kandidaten: list[VnbCandidate] = []
    for kuerzel in vnb_kuerzel:
        entry = vnb_dict.get(kuerzel)
        if entry is None:
            continue
        vnb_kandidaten.append(
            VnbCandidate(
                name=entry["name"],
                kuerzel=entry["kuerzel"],
                snap_verfuegbar=bool(entry.get("snap_verfuegbar", False)),
                snap_url=entry.get("snap_url"),
                hinweis=entry.get("hinweis"),
            )
        )

    snap_verfuegbar = any(v.snap_verfuegbar for v in vnb_kandidaten)

    return PlzLookupResponse(
        plz=plz,
        bundesland_kandidaten=bundesland_kandidaten,
        vnb_kandidaten=vnb_kandidaten,
        snap_verfuegbar=snap_verfuegbar,
        confidence=data.get("confidence_default", "B-heuristisch"),
        quelle=data["quelle"],
        stand=data["stand"],
        hinweis=data["hinweis"],
    )
