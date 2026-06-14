"""Tests fuer GET /api/v1/mastr/units (BL-GIS-003 Read-Skeleton).

Pflicht laut Auftrag:
- requires auth
- by-PLZ + paginiert
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from db.database import Base, get_db
from db.models import MastrUnit
from main import app
from services.mastr_import_service import PARSER_VERSION
from tests.postgres_test_utils import build_isolated_postgres_session_factory


@pytest.fixture
def client_with_db():
    _, session_factory, cleanup = build_isolated_postgres_session_factory(
        Base.metadata, label="mastr_api"
    )

    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(app)
    test_client._gridcheck_session_factory = session_factory  # type: ignore[attr-defined]
    try:
        yield test_client
    finally:
        app.dependency_overrides.pop(get_db, None)
        test_client.close()
        cleanup()


def _register_and_login(client: TestClient, email: str = "mastr-read@example.test") -> str:
    password = "Passwort123!"
    reg = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "role": "projektierer"},
    )
    assert reg.status_code == 200, reg.text
    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200, login.text
    return login.json()["access_token"]


def _seed_units(session_factory, *, plz: str = "10115", count: int = 3) -> None:
    with session_factory() as db:
        now = datetime.now(timezone.utc)
        for i in range(count):
            db.add(
                MastrUnit(
                    mastr_id=f"SEE-API-{plz}-{i:03d}",
                    unit_type="solar",
                    installed_capacity_kw=Decimal("12.500"),
                    plz=plz,
                    bundesland="Berlin",
                    latitude=Decimal("52.517037"),
                    longitude=Decimal("13.388860"),
                    dso_name="Stromnetz Berlin GmbH",
                    voltage_level="Niederspannung",
                    data_source="mastr",
                    data_class="A",
                    confidence=Decimal("0.95"),
                    raw_hash="a" * 64,
                    normalized_hash="b" * 64,
                    parser_version=PARSER_VERSION,
                    imported_at=now,
                )
            )
        db.commit()


def test_get_units_requires_auth(client_with_db):
    resp = client_with_db.get("/api/v1/mastr/units?plz=10115")
    assert resp.status_code == 401
    body = resp.json()
    assert body["detail"]["code"] in {"AUTH_REQUIRED", "AUTH_USER_INVALID"}


def test_get_units_by_plz_returns_paginated(client_with_db):
    _seed_units(client_with_db._gridcheck_session_factory, plz="10115", count=3)
    _seed_units(client_with_db._gridcheck_session_factory, plz="20095", count=2)

    token = _register_and_login(client_with_db)
    headers = {"Authorization": f"Bearer {token}"}

    resp = client_with_db.get(
        "/api/v1/mastr/units?plz=10115&limit=2&offset=0",
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["total"] == 3
    assert len(data["items"]) == 2
    assert data["limit"] == 2
    assert data["offset"] == 0
    assert all(item["plz"] == "10115" for item in data["items"])
    assert data["items"][0]["data_class"] == "A"
    assert "disclaimer" in data
    assert "Netzkapazitaet" in data["disclaimer"]

    resp2 = client_with_db.get(
        "/api/v1/mastr/units?plz=10115&limit=2&offset=2",
        headers=headers,
    )
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert len(data2["items"]) == 1
    assert data2["items"][0]["mastr_id"] != data["items"][0]["mastr_id"]


def test_get_units_requires_plz_or_coords(client_with_db):
    token = _register_and_login(client_with_db, email="mastr-need-filter@example.test")
    resp = client_with_db.get(
        "/api/v1/mastr/units",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422
    body = resp.json()
    assert body["detail"]["code"] == "MASTR_FILTER_REQUIRED"


def test_get_units_unit_type_filter(client_with_db):
    _seed_units(client_with_db._gridcheck_session_factory, plz="10115", count=2)
    with client_with_db._gridcheck_session_factory() as db:
        db.add(
            MastrUnit(
                mastr_id="SEE-WIND-1",
                unit_type="wind",
                installed_capacity_kw=Decimal("3000.000"),
                plz="10115",
                bundesland="Berlin",
                data_source="mastr",
                data_class="A",
                confidence=Decimal("0.95"),
                raw_hash="c" * 64,
                normalized_hash="d" * 64,
                parser_version=PARSER_VERSION,
                imported_at=datetime.now(timezone.utc),
            )
        )
        db.commit()

    token = _register_and_login(client_with_db, email="mastr-typefilter@example.test")
    resp = client_with_db.get(
        "/api/v1/mastr/units?plz=10115&unit_type=wind",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["unit_type"] == "wind"
