"""Tests fuer MaStR-Import-Skeleton (BL-GIS-003).

Pflicht-Cases laut Auftrag:
- extract liefert Zeilen
- transform akzeptiert valide Zeile
- transform lehnt ungueltige Latitude ab
- load inserts/updates/skips je nach raw_hash
- run() schreibt Audit
- run() fail-soft auf bad row
- dry-run schreibt keine DB-Writes
"""
from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import ValidationError

from db.database import Base
from db.models import MastrImport, MastrUnit
from services.mastr_import_service import (
    PARSER_VERSION,
    ImportStats,
    extract,
    load,
    run_mastr_import,
    transform,
)
from tests.postgres_test_utils import build_isolated_postgres_session_factory


FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "mastr_sample.csv"


def _valid_row(**overrides) -> dict:
    base = {
        "MaStR-Nr": "SEE900000099001",
        "Anlagentyp": "Solar",
        "Bruttoleistung_kW": "12.345",
        "Inbetriebnahme": "2021-04-15",
        "PLZ": "10115",
        "Bundesland": "Berlin",
        "Laengengrad": "13.388860",
        "Breitengrad": "52.517037",
        "Netzbetreiber": "Stromnetz Berlin GmbH",
        "Spannungsebene": "Niederspannung",
    }
    base.update(overrides)
    return base


@pytest.fixture
def db_session_factory():
    _, session_factory, cleanup = build_isolated_postgres_session_factory(
        Base.metadata, label="mastr_import"
    )
    try:
        yield session_factory
    finally:
        cleanup()


def test_extract_yields_rows():
    rows = list(extract(FIXTURE_PATH))
    assert len(rows) == 10
    assert rows[0]["MaStR-Nr"] == "SEE900000000001"
    assert rows[0]["Anlagentyp"].lower() == "solar"


def test_transform_handles_valid_row():
    row = _valid_row()
    rec = transform(row)
    assert rec.mastr_id == "SEE900000099001"
    assert rec.unit_type == "solar"
    assert rec.installed_capacity_kw == Decimal("12.345")
    assert rec.plz == "10115"
    assert rec.bundesland == "Berlin"
    assert rec.latitude == Decimal("52.517037")
    assert rec.longitude == Decimal("13.388860")
    assert rec.parser_version == PARSER_VERSION
    assert len(rec.raw_hash) == 64
    assert len(rec.normalized_hash) == 64
    assert rec.data_class == "A"
    assert rec.confidence == Decimal("0.95")


def test_transform_rejects_invalid_latitude():
    row = _valid_row(Breitengrad="123.456")
    with pytest.raises(ValidationError):
        transform(row)


def test_transform_rejects_invalid_date():
    row = _valid_row(Inbetriebnahme="NICHT_DATUM")
    with pytest.raises(ValueError):
        transform(row)


def test_transform_rejects_missing_capacity():
    row = _valid_row(Bruttoleistung_kW="")
    with pytest.raises(ValueError):
        transform(row)


def test_load_inserts_new_records(db_session_factory):
    rec = transform(_valid_row(**{"MaStR-Nr": "SEE-INS-001"}))
    stats = ImportStats()
    with db_session_factory() as db:
        load([rec], db=db, stats=stats)
        db.commit()
        assert stats.rows_inserted == 1
        assert stats.rows_updated == 0
        assert stats.rows_skipped == 0
        assert db.query(MastrUnit).count() == 1


def test_load_continues_after_row_flush_error(db_session_factory):
    overflowing = transform(
        _valid_row(
            **{
                "MaStR-Nr": "SEE-OVERFLOW-001",
                "Bruttoleistung_kW": "100000000000.000",
            }
        )
    )
    valid = transform(_valid_row(**{"MaStR-Nr": "SEE-AFTER-ERROR-001"}))
    stats = ImportStats()

    with db_session_factory() as db:
        load([overflowing, valid], db=db, stats=stats)
        db.commit()

        assert stats.rows_failed == 1
        assert stats.rows_inserted == 1
        assert db.query(MastrUnit).count() == 1
        assert db.query(MastrUnit).one().mastr_id == "SEE-AFTER-ERROR-001"


def test_load_updates_on_raw_hash_diff(db_session_factory):
    rec1 = transform(_valid_row(**{"MaStR-Nr": "SEE-UPD-001"}))
    rec2 = transform(
        _valid_row(**{"MaStR-Nr": "SEE-UPD-001", "Bruttoleistung_kW": "999.000"})
    )
    assert rec1.raw_hash != rec2.raw_hash
    stats = ImportStats()
    with db_session_factory() as db:
        load([rec1], db=db, stats=stats)
        db.commit()
        load([rec2], db=db, stats=stats)
        db.commit()
        assert stats.rows_inserted == 1
        assert stats.rows_updated == 1
        unit = db.query(MastrUnit).one()
        assert unit.installed_capacity_kw == Decimal("999.000")


def test_load_skips_when_hash_unchanged(db_session_factory):
    rec = transform(_valid_row(**{"MaStR-Nr": "SEE-SKIP-001"}))
    stats = ImportStats()
    with db_session_factory() as db:
        load([rec], db=db, stats=stats)
        db.commit()
        load([rec], db=db, stats=stats)
        db.commit()
        assert stats.rows_inserted == 1
        assert stats.rows_updated == 0
        assert stats.rows_skipped == 1


def test_run_logs_import_audit(db_session_factory):
    with db_session_factory() as db:
        run = run_mastr_import(FIXTURE_PATH, db_session=db)
    with db_session_factory() as db2:
        audits = db2.query(MastrImport).all()
        assert len(audits) == 1
        audit = audits[0]
        assert audit.id == run.id
        assert audit.parser_version == PARSER_VERSION
        assert str(FIXTURE_PATH) in audit.source_file
        assert audit.rows_total == 10
        assert audit.finished_at is not None


def test_run_fail_soft_on_bad_row(db_session_factory):
    """Zeile 10 enthaelt 'NICHT_DATUM' im Inbetriebnahme-Feld -> fail-soft."""
    with db_session_factory() as db:
        run = run_mastr_import(FIXTURE_PATH, db_session=db)
    assert run.stats.rows_total == 10
    assert run.stats.rows_failed >= 1
    assert run.stats.rows_inserted >= 8
    assert run.error_summary is not None
    assert run.status == "success"


def test_dry_run_no_db_writes(db_session_factory):
    run = run_mastr_import(FIXTURE_PATH, db_session=None, dry_run=True)  # type: ignore[arg-type]
    assert run.status.endswith("dry_run")
    assert run.stats.rows_total == 10
    with db_session_factory() as db:
        assert db.query(MastrUnit).count() == 0
        assert db.query(MastrImport).count() == 0
