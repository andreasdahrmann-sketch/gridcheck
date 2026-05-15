from __future__ import annotations

import io

from fastapi.testclient import TestClient

from db.database import Base, get_db
from main import app
from tests.postgres_test_utils import build_isolated_postgres_session_factory


def build_client() -> TestClient:
    _, TestingSessionLocal, cleanup = build_isolated_postgres_session_factory(Base.metadata, label="site_markers")

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    client._gridcheck_cleanup = cleanup  # type: ignore[attr-defined]
    return client


def _close_client(client: TestClient) -> None:
    app.dependency_overrides.clear()
    client.close()
    client._gridcheck_cleanup()  # type: ignore[attr-defined]


def _register_and_login(client: TestClient, email: str, password: str = "Passwort123!") -> dict:
    reg = client.post("/api/v1/auth/register", json={"email": email, "password": password, "role": "projektierer"})
    assert reg.status_code == 200, reg.text
    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200, login.text
    return login.json()


def test_site_marker_create_list_and_photo(tmp_path, monkeypatch, isolierte_revisionen):
    client = build_client()
    try:
        from api import site_markers as site_markers_api

        monkeypatch.setattr(site_markers_api, "UPLOAD_DIR", str(tmp_path / "site_markers"))
        tokens = _register_and_login(client, "marker-owner@example.com")
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}

        created = client.post(
            "/api/v1/site-markers",
            headers=headers,
            data={
                "asset_type": "ortsnetztrafo",
                "location_source": "gps",
                "latitude": "52.520008",
                "longitude": "13.404954",
            },
            files={"photo": ("marker.jpg", io.BytesIO(b"fake-jpeg-content"), "image/jpeg")},
        )

        assert created.status_code == 201, created.text
        body = created.json()
        assert body["asset_type"] == "ortsnetztrafo"
        assert body["location_source"] == "gps"
        assert body["verification_status"] == "unverified"
        assert body["photo_file_name"] == "marker.jpg"
        assert body["photo_mime_type"] == "image/jpeg"
        assert body["revision_hash"]

        listed = client.get("/api/v1/site-markers", headers=headers)
        assert listed.status_code == 200, listed.text
        assert [item["id"] for item in listed.json()] == [body["id"]]

        photo = client.get(body["photo_api_path"], headers=headers)
        assert photo.status_code == 200, photo.text
        assert photo.headers["content-type"] == "image/jpeg"
        assert photo.content == b"fake-jpeg-content"
    finally:
        _close_client(client)


def test_site_marker_rejects_invalid_upload_and_scopes_access(tmp_path, monkeypatch, isolierte_revisionen):
    client = build_client()
    try:
        from api import site_markers as site_markers_api

        monkeypatch.setattr(site_markers_api, "UPLOAD_DIR", str(tmp_path / "site_markers"))
        owner_tokens = _register_and_login(client, "marker-access-owner@example.com")
        viewer_tokens = _register_and_login(client, "marker-access-viewer@example.com")
        owner_headers = {"Authorization": f"Bearer {owner_tokens['access_token']}"}
        viewer_headers = {"Authorization": f"Bearer {viewer_tokens['access_token']}"}

        created = client.post(
            "/api/v1/site-markers",
            headers=owner_headers,
            data={
                "asset_type": "umspannwerk",
                "location_source": "manual",
                "latitude": "50.110924",
                "longitude": "8.682127",
            },
            files={"photo": ("marker.png", io.BytesIO(b"fake-png-content"), "image/png")},
        )
        assert created.status_code == 201, created.text
        marker_path = created.json()["photo_api_path"]

        foreign_list = client.get("/api/v1/site-markers", headers=viewer_headers)
        assert foreign_list.status_code == 200, foreign_list.text
        assert foreign_list.json() == []

        forbidden_photo = client.get(marker_path, headers=viewer_headers)
        assert forbidden_photo.status_code == 403, forbidden_photo.text
        assert forbidden_photo.json()["detail"]["code"] == "SITE_MARKER_FORBIDDEN"

        invalid_upload = client.post(
            "/api/v1/site-markers",
            headers=owner_headers,
            data={
                "asset_type": "schaltstation",
                "location_source": "manual",
                "latitude": "48.137154",
                "longitude": "11.576124",
            },
            files={"photo": ("marker.txt", io.BytesIO(b"not-an-image"), "text/plain")},
        )
        assert invalid_upload.status_code == 415, invalid_upload.text
        assert invalid_upload.json()["detail"]["code"] == "SITE_MARKER_PHOTO_TYPE_NOT_ALLOWED"
    finally:
        _close_client(client)
