"""MaStR-Import-Skeleton (BL-GIS-003, erstes Inkrement).

ETL-Pipeline: extract -> transform -> load.
- KEIN Live-Pull in diesem Inkrement; CSV-Datei als Eingabe (Fixture/lokale Datei).
- Fail-soft pro Zeile (rows_failed in Audit, KEIN globaler Abbruch).
- raw_hash + normalized_hash + parser_version sind Pflicht (Rule 06).
- Datenklasse A (offizielle BNetzA-Quelle) laut Rule 06.
- KEINE Aussage zur freien Netzkapazitaet (Rule 06).
"""
from __future__ import annotations

import csv
import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterable, Iterator, Optional

from pydantic import ValidationError
from sqlalchemy.orm import Session

from core.logging_setup import get_logger
from db.models import MastrImport, MastrUnit
from schemas.mastr import MastrUnitRecord


PARSER_VERSION = "mastr-csv-0.1.0"

# CSV-Spaltennamen orientiert an realer MaStR-Datenstruktur (Auftrag 6+7).
COL_MASTR_ID = "MaStR-Nr"
COL_UNIT_TYPE = "Anlagentyp"
COL_CAPACITY = "Bruttoleistung_kW"
COL_COMMISSIONING = "Inbetriebnahme"
COL_PLZ = "PLZ"
COL_BUNDESLAND = "Bundesland"
COL_LON = "Laengengrad"
COL_LAT = "Breitengrad"
COL_DSO = "Netzbetreiber"
COL_VOLTAGE = "Spannungsebene"

# Mapping deutsch -> normalisiert (interne Enum-Werte).
_UNIT_TYPE_MAP = {
    "solar": "solar",
    "solarstrom": "solar",
    "photovoltaik": "solar",
    "pv": "solar",
    "wind": "wind",
    "windenergie": "wind",
    "windkraft": "wind",
    "biomasse": "biomass",
    "biomass": "biomass",
    "biogas": "biomass",
    "wasser": "hydro",
    "wasserkraft": "hydro",
    "hydro": "hydro",
    "speicher": "storage",
    "stromspeicher": "storage",
    "batteriespeicher": "storage",
    "storage": "storage",
}

logger = get_logger("gridcheck.services.mastr_import")


@dataclass
class ImportStats:
    rows_total: int = 0
    rows_inserted: int = 0
    rows_updated: int = 0
    rows_skipped: int = 0
    rows_failed: int = 0
    errors: list[str] = field(default_factory=list)


@dataclass
class MastrImportRun:
    """Ergebnis-Objekt eines Importlaufs (Audit + Stats)."""

    id: str
    source_file: str
    parser_version: str
    started_at: datetime
    finished_at: Optional[datetime]
    status: str
    stats: ImportStats
    error_summary: Optional[str] = None


def _hash_row(payload: dict) -> str:
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class _SemicolonDialect(csv.Dialect):
    delimiter = ";"
    quotechar = '"'
    doublequote = True
    skipinitialspace = True
    lineterminator = "\n"
    quoting = csv.QUOTE_MINIMAL


def _detect_dialect(sample: str):
    try:
        return csv.Sniffer().sniff(sample, delimiters=";,\t")
    except csv.Error:
        return _SemicolonDialect


def extract(source_path: Path) -> Iterator[dict]:
    """Liest CSV streaming Zeile fuer Zeile (kein Komplett-Load)."""
    path = Path(source_path)
    if not path.is_file():
        raise FileNotFoundError(f"MaStR-Quelle fehlt: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        sample = fh.read(4096)
        fh.seek(0)
        dialect = _detect_dialect(sample)
        reader = csv.DictReader(fh, dialect=dialect)
        for row in reader:
            yield {(k or "").strip(): (v.strip() if isinstance(v, str) else v) for k, v in row.items()}


def _normalize_unit_type(raw: Optional[str]) -> str:
    if not raw:
        return "other"
    key = raw.strip().lower()
    return _UNIT_TYPE_MAP.get(key, "other")


def _parse_decimal(raw: Optional[str]) -> Optional[Decimal]:
    if raw is None or raw == "":
        return None
    cleaned = raw.replace(" ", "").replace(",", ".")
    try:
        return Decimal(cleaned)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"ungueltige Dezimalzahl '{raw}'") from exc


def _parse_date(raw: Optional[str]) -> Optional[date]:
    if not raw:
        return None
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"ungueltiges Datum '{raw}'")


def transform(row: dict) -> MastrUnitRecord:
    """Normalisiert eine CSV-Zeile zu MastrUnitRecord (validiert via Pydantic)."""
    mastr_id = (row.get(COL_MASTR_ID) or "").strip()
    if not mastr_id:
        raise ValueError("mastr_id fehlt in Zeile")

    capacity = _parse_decimal(row.get(COL_CAPACITY))
    if capacity is None:
        raise ValueError("Bruttoleistung_kW fehlt")

    raw_payload = {
        "mastr_id": mastr_id,
        "unit_type_raw": row.get(COL_UNIT_TYPE),
        "capacity_kw_raw": row.get(COL_CAPACITY),
        "commissioning_raw": row.get(COL_COMMISSIONING),
        "plz_raw": row.get(COL_PLZ),
        "bundesland_raw": row.get(COL_BUNDESLAND),
        "lon_raw": row.get(COL_LON),
        "lat_raw": row.get(COL_LAT),
        "dso_raw": row.get(COL_DSO),
        "voltage_raw": row.get(COL_VOLTAGE),
    }
    raw_hash = _hash_row(raw_payload)

    plz_value = (row.get(COL_PLZ) or "").strip() or None
    bundesland_value = (row.get(COL_BUNDESLAND) or "").strip() or None
    dso_value = (row.get(COL_DSO) or "").strip() or None
    voltage_value = (row.get(COL_VOLTAGE) or "").strip() or None

    normalized_payload = {
        "mastr_id": mastr_id,
        "unit_type": _normalize_unit_type(row.get(COL_UNIT_TYPE)),
        "installed_capacity_kw": str(capacity),
        "commissioning_date": (
            _parse_date(row.get(COL_COMMISSIONING)).isoformat()
            if row.get(COL_COMMISSIONING)
            else None
        ),
        "plz": plz_value,
        "bundesland": bundesland_value,
        "latitude": (str(_parse_decimal(row.get(COL_LAT))) if row.get(COL_LAT) else None),
        "longitude": (str(_parse_decimal(row.get(COL_LON))) if row.get(COL_LON) else None),
        "dso_name": dso_value,
        "voltage_level": voltage_value,
    }
    normalized_hash = _hash_row(normalized_payload)

    return MastrUnitRecord(
        mastr_id=mastr_id,
        unit_type=_normalize_unit_type(row.get(COL_UNIT_TYPE)),
        installed_capacity_kw=capacity,
        commissioning_date=_parse_date(row.get(COL_COMMISSIONING)),
        plz=plz_value,
        bundesland=bundesland_value,
        latitude=_parse_decimal(row.get(COL_LAT)),
        longitude=_parse_decimal(row.get(COL_LON)),
        dso_name=dso_value,
        voltage_level=voltage_value,
        raw_hash=raw_hash,
        normalized_hash=normalized_hash,
        parser_version=PARSER_VERSION,
    )


def _upsert(db: Session, record: MastrUnitRecord) -> tuple[str, MastrUnit]:
    """UPSERT: gibt ('inserted'|'updated'|'skipped', row) zurueck."""
    existing: MastrUnit | None = db.query(MastrUnit).filter(MastrUnit.mastr_id == record.mastr_id).one_or_none()
    now = datetime.now(timezone.utc)
    if existing is None:
        unit = MastrUnit(
            mastr_id=record.mastr_id,
            unit_type=record.unit_type,
            installed_capacity_kw=record.installed_capacity_kw,
            commissioning_date=record.commissioning_date,
            decommissioning_date=record.decommissioning_date,
            plz=record.plz,
            bundesland=record.bundesland,
            latitude=record.latitude,
            longitude=record.longitude,
            dso_name=record.dso_name,
            voltage_level=record.voltage_level,
            data_source=record.data_source,
            data_class=record.data_class,
            confidence=record.confidence,
            raw_hash=record.raw_hash,
            normalized_hash=record.normalized_hash,
            parser_version=record.parser_version,
            imported_at=now,
            source_updated_at=record.source_updated_at,
        )
        db.add(unit)
        db.flush()
        return "inserted", unit

    if existing.raw_hash == record.raw_hash and existing.parser_version == record.parser_version:
        return "skipped", existing

    existing.unit_type = record.unit_type
    existing.installed_capacity_kw = record.installed_capacity_kw
    existing.commissioning_date = record.commissioning_date
    existing.decommissioning_date = record.decommissioning_date
    existing.plz = record.plz
    existing.bundesland = record.bundesland
    existing.latitude = record.latitude
    existing.longitude = record.longitude
    existing.dso_name = record.dso_name
    existing.voltage_level = record.voltage_level
    existing.data_source = record.data_source
    existing.data_class = record.data_class
    existing.confidence = record.confidence
    existing.raw_hash = record.raw_hash
    existing.normalized_hash = record.normalized_hash
    existing.parser_version = record.parser_version
    existing.imported_at = now
    existing.source_updated_at = record.source_updated_at
    db.flush()
    return "updated", existing


def load(
    records: Iterable[MastrUnitRecord],
    *,
    db: Session,
    stats: ImportStats,
) -> ImportStats:
    """Persistiert validierte Records (UPSERT auf mastr_id)."""
    for record in records:
        try:
            action, _ = _upsert(db, record)
            if action == "inserted":
                stats.rows_inserted += 1
            elif action == "updated":
                stats.rows_updated += 1
            else:
                stats.rows_skipped += 1
        except Exception as exc:  # fail-soft pro Zeile
            stats.rows_failed += 1
            stats.errors.append(f"load:{record.mastr_id}:{type(exc).__name__}:{exc}")
            logger.warning("mastr_load_failed", mastr_id=record.mastr_id, error=str(exc))
    return stats


def _iter_validated(rows: Iterator[dict], stats: ImportStats) -> Iterator[MastrUnitRecord]:
    """Wendet transform() fail-soft pro Zeile an."""
    for row in rows:
        stats.rows_total += 1
        try:
            yield transform(row)
        except (ValueError, ValidationError) as exc:
            stats.rows_failed += 1
            mastr_id = (row.get(COL_MASTR_ID) or "<unknown>").strip()
            stats.errors.append(f"transform:{mastr_id}:{type(exc).__name__}:{exc}")
            logger.warning("mastr_transform_failed", mastr_id=mastr_id, error=str(exc))


def run_mastr_import(
    source_path: Path,
    *,
    db_session: Session,
    dry_run: bool = False,
) -> MastrImportRun:
    """Public Entry: legt Audit-Eintrag an, ruft ETL, finalisiert Status.

    dry_run=True: liest + validiert, schreibt aber KEINE Units in die DB
    und legt KEINEN mastr_imports-Audit an (lokales Smoke-Run-Feature).
    """
    started_at = datetime.now(timezone.utc)
    run_id = str(uuid.uuid4())
    stats = ImportStats()

    if dry_run:
        # Nur extract + validate, kein DB-Write.
        list(_iter_validated(extract(Path(source_path)), stats))
        finished_at = datetime.now(timezone.utc)
        status = "success" if stats.rows_failed == 0 else "failed"
        return MastrImportRun(
            id=run_id,
            source_file=str(source_path),
            parser_version=PARSER_VERSION,
            started_at=started_at,
            finished_at=finished_at,
            status=status + "_dry_run",
            stats=stats,
            error_summary="; ".join(stats.errors[:5]) if stats.errors else None,
        )

    audit = MastrImport(
        id=run_id,
        started_at=started_at,
        parser_version=PARSER_VERSION,
        source_file=str(source_path),
        status="running",
    )
    db_session.add(audit)
    db_session.flush()

    try:
        load(_iter_validated(extract(Path(source_path)), stats), db=db_session, stats=stats)
        finished_at = datetime.now(timezone.utc)
        audit.finished_at = finished_at
        audit.rows_total = stats.rows_total
        audit.rows_inserted = stats.rows_inserted
        audit.rows_updated = stats.rows_updated
        audit.rows_skipped = stats.rows_skipped
        audit.rows_failed = stats.rows_failed
        audit.status = "failed" if stats.rows_failed > 0 and stats.rows_inserted + stats.rows_updated == 0 else "success"
        audit.error_summary = "; ".join(stats.errors[:5]) if stats.errors else None
        db_session.commit()
    except Exception as exc:
        finished_at = datetime.now(timezone.utc)
        db_session.rollback()
        failed_audit = MastrImport(
            id=run_id,
            started_at=started_at,
            finished_at=finished_at,
            parser_version=PARSER_VERSION,
            source_file=str(source_path),
            rows_total=stats.rows_total,
            rows_inserted=0,
            rows_updated=0,
            rows_skipped=0,
            rows_failed=max(stats.rows_failed, 1),
            status="failed",
            error_summary=f"{type(exc).__name__}: {exc}",
        )
        db_session.add(failed_audit)
        db_session.commit()
        logger.error("mastr_import_aborted", run_id=run_id, error=str(exc))
        raise

    logger.info(
        "mastr_import_finished",
        run_id=run_id,
        status=audit.status,
        rows_total=audit.rows_total,
        rows_inserted=audit.rows_inserted,
        rows_updated=audit.rows_updated,
        rows_skipped=audit.rows_skipped,
        rows_failed=audit.rows_failed,
    )

    return MastrImportRun(
        id=run_id,
        source_file=str(source_path),
        parser_version=PARSER_VERSION,
        started_at=started_at,
        finished_at=finished_at,
        status=audit.status,
        stats=stats,
        error_summary=audit.error_summary,
    )
