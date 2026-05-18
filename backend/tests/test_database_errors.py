from __future__ import annotations

from sqlalchemy.exc import ProgrammingError

from main import _database_error_payload


def test_database_error_payload_detects_missing_schema() -> None:
    exc = ProgrammingError("SELECT", {}, Exception('relation "users" does not exist'))
    payload = _database_error_payload(exc)
    assert payload["code"] == "DATABASE_SCHEMA_MISSING"
    assert "migriert" in payload["message"]


def test_database_error_payload_generic_connection() -> None:
    exc = ProgrammingError("SELECT", {}, Exception("could not connect to server"))
    payload = _database_error_payload(exc)
    assert payload["code"] == "DATABASE_UNAVAILABLE"
    assert "Verbindung" in payload["message"]
