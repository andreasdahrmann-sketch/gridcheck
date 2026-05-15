from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

import requests

from pricing.provider_smard import get_strompreis_eur_mwh

PARSER_VERSION = "pipeline-0.1.0"
SNAPSHOT_PFAD = os.path.join("daten", "datenquellen_snapshots.jsonl")


@dataclass(frozen=True)
class DataSourceSnapshot:
    name: str
    herkunft_url: str | None
    lizenz: str
    importzeitpunkt_utc: str
    aktualisierungsstand: str | None
    raw_hash: str
    normalized_hash: str
    parser_version: str
    confidence_score: int
    confidence_technisch: int
    confidence_geometrisch: int
    confidence_kommerziell: int
    validierungsstatus: str
    datenklasse: str
    record_count: int
    hinweis: str | None


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash_payload(payload: Any) -> str:
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _append_snapshot(snapshot: DataSourceSnapshot) -> None:
    os.makedirs("daten", exist_ok=True)
    with open(SNAPSHOT_PFAD, "a", encoding="utf-8") as f:
        f.write(json.dumps(asdict(snapshot), ensure_ascii=False) + "\n")


def _build_snapshot(
    *,
    name: str,
    herkunft_url: str | None,
    lizenz: str,
    datenklasse: str,
    raw_payload: Any,
    normalized_payload: Any,
    aktualisierungsstand: str | None,
    confidence: tuple[int, int, int, int],
    validierungsstatus: str,
    hinweis: str | None = None,
) -> DataSourceSnapshot:
    c_total, c_tech, c_geo, c_comm = confidence
    record_count = len(normalized_payload) if isinstance(normalized_payload, list) else 1
    return DataSourceSnapshot(
        name=name,
        herkunft_url=herkunft_url,
        lizenz=lizenz,
        importzeitpunkt_utc=_utc_now(),
        aktualisierungsstand=aktualisierungsstand,
        raw_hash=_hash_payload(raw_payload),
        normalized_hash=_hash_payload(normalized_payload),
        parser_version=PARSER_VERSION,
        confidence_score=c_total,
        confidence_technisch=c_tech,
        confidence_geometrisch=c_geo,
        confidence_kommerziell=c_comm,
        validierungsstatus=validierungsstatus,
        datenklasse=datenklasse,
        record_count=record_count,
        hinweis=hinweis,
    )


def _run_smard() -> DataSourceSnapshot:
    payload = get_strompreis_eur_mwh(use_cache=False)
    normalized = {
        "price_eur_mwh": payload.get("price_eur_mwh"),
        "source": payload.get("source"),
    }
    source_text = str(payload.get("source", ""))
    is_fallback = source_text.lower().startswith("fallback")
    return _build_snapshot(
        name="SMARD",
        herkunft_url="https://www.smard.de/",
        lizenz="Bundesnetzagentur Open Data (siehe SMARD-Nutzungsbedingungen)",
        datenklasse="A",
        raw_payload=payload,
        normalized_payload=normalized,
        aktualisierungsstand=None,
        confidence=(85, 90, 70, 85) if not is_fallback else (45, 55, 50, 35),
        validierungsstatus="OK" if not is_fallback else "PARTIAL",
        hinweis=None if not is_fallback else "SMARD nicht direkt erreichbar, Fallbackwert genutzt.",
    )


def _fetch_http_json(url: str, timeout_sec: int = 10) -> Any:
    resp = requests.get(url, timeout=timeout_sec)
    resp.raise_for_status()
    return resp.json()


def _run_mastr() -> DataSourceSnapshot:
    # MaStR hat keinen stabilen, anonymen Standard-Export-Endpunkt fuer MVP.
    # Falls URL gesetzt ist, wird sie genutzt; sonst bewusst "NOT_CONFIGURED".
    export_url = os.getenv("MASTR_EXPORT_URL", "").strip() or None
    if not export_url:
        payload = {"status": "not_configured", "records": []}
        return _build_snapshot(
            name="MaStR",
            herkunft_url="https://www.marktstammdatenregister.de/",
            lizenz="BNetzA / MaStR (siehe Nutzungsbedingungen)",
            datenklasse="A",
            raw_payload=payload,
            normalized_payload=[],
            aktualisierungsstand=None,
            confidence=(20, 25, 20, 15),
            validierungsstatus="NOT_CONFIGURED",
            hinweis="MASTR_EXPORT_URL nicht gesetzt.",
        )

    data = _fetch_http_json(export_url)
    records = data if isinstance(data, list) else data.get("records", [])
    normalized = [
        {
            "id": r.get("id"),
            "energietraeger": r.get("energietraeger"),
            "leistung_kw": r.get("leistung_kw"),
            "plz": r.get("plz"),
            "status": r.get("status"),
        }
        for r in records
        if isinstance(r, dict)
    ]
    return _build_snapshot(
        name="MaStR",
        herkunft_url=export_url,
        lizenz="BNetzA / MaStR (siehe Nutzungsbedingungen)",
        datenklasse="A",
        raw_payload=data,
        normalized_payload=normalized,
        aktualisierungsstand=None,
        confidence=(80, 80, 75, 80),
        validierungsstatus="OK",
    )


def _run_dwd() -> DataSourceSnapshot:
    # DWD-CDC bietet offene Daten; URL konfigurierbar fuer konkretes Dataset.
    dwd_url = os.getenv("DWD_SOURCE_URL", "").strip() or None
    if not dwd_url:
        payload = {"status": "not_configured", "records": []}
        return _build_snapshot(
            name="DWD",
            herkunft_url="https://opendata.dwd.de/",
            lizenz="DWD Open Data (Deutschlandlizenz Namensnennung)",
            datenklasse="A",
            raw_payload=payload,
            normalized_payload=[],
            aktualisierungsstand=None,
            confidence=(20, 20, 25, 15),
            validierungsstatus="NOT_CONFIGURED",
            hinweis="DWD_SOURCE_URL nicht gesetzt.",
        )

    data = _fetch_http_json(dwd_url)
    records = data if isinstance(data, list) else data.get("records", [])
    normalized = [
        {
            "station_id": r.get("station_id"),
            "datum": r.get("datum"),
            "temperatur_c": r.get("temperatur_c"),
            "wind_ms": r.get("wind_ms"),
            "strahlung_wm2": r.get("strahlung_wm2"),
        }
        for r in records
        if isinstance(r, dict)
    ]
    return _build_snapshot(
        name="DWD",
        herkunft_url=dwd_url,
        lizenz="DWD Open Data (Deutschlandlizenz Namensnennung)",
        datenklasse="A",
        raw_payload=data,
        normalized_payload=normalized,
        aktualisierungsstand=None,
        confidence=(78, 75, 85, 60),
        validierungsstatus="OK",
    )


def run_data_source_pipeline(sources: list[str] | None = None) -> list[DataSourceSnapshot]:
    selected = [s.lower() for s in (sources or ["mastr", "smard", "dwd"])]
    out: list[DataSourceSnapshot] = []
    for source in selected:
        try:
            if source == "mastr":
                snap = _run_mastr()
            elif source == "smard":
                snap = _run_smard()
            elif source == "dwd":
                snap = _run_dwd()
            else:
                continue
        except Exception as e:  # bewusst robust: Pipeline laeuft weiter
            snap = _build_snapshot(
                name=source.upper(),
                herkunft_url=None,
                lizenz="unbekannt",
                datenklasse="B",
                raw_payload={"error": str(e)},
                normalized_payload=[],
                aktualisierungsstand=None,
                confidence=(10, 10, 10, 10),
                validierungsstatus="ERROR",
                hinweis=f"Quelle konnte nicht verarbeitet werden: {type(e).__name__}",
            )
        _append_snapshot(snap)
        out.append(snap)
    return out

