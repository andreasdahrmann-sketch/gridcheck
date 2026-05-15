"""Regression: Stateless Engine unter POST /api/v1/analyze (kein projektname)."""
from __future__ import annotations

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)
URL = "/api/v1/analyze"


def _v2_payload(**overrides: object) -> dict:
    base: dict[str, object] = {
        "nennspannung": 20.0,
        "leistung_mw": 5.0,
        "leitungstyp": "NA2XS2Y240",
        "entfernung_km": 10.0,
        "anschlussart": "Einspeisung",
    }
    base.update(**{k: v for k, v in overrides.items()})
    return base


def _assert_kein_legacy_projektname_422(detail: object, response_text: str) -> None:
    if isinstance(detail, list):
        for item in detail:
            if isinstance(item, dict):
                loc = item.get("loc")
                if isinstance(loc, list):
                    joined = ".".join(str(x) for x in loc).lower()
                    assert "projektname" not in joined, response_text
    lowered = str(detail).lower()
    assert "field required" not in lowered or "projektname" not in lowered, response_text


def test_analyze_v2_route_bindet_engine_schema():
    """Gueltiges V2-JSON: Persist-422 (projektname) ist ein Routing-Bug."""
    r = client.post(URL, json=_v2_payload())
    detail = None
    try:
        detail = r.json().get("detail")
    except Exception:
        detail = None

    if r.status_code == 422:
        _assert_kein_legacy_projektname_422(detail, r.text)
        # Engine darf fachlich 422 liefern, aber nur im FEHLER-Format.
        assert isinstance(detail, dict), r.text
        assert detail.get("status") == "FEHLER", r.text
        return

    assert r.status_code == 200, r.text
    body = r.json()
    assert "status" in body


def test_openapi_listen_post_analyze_einmal_engine():
    """OpenAPI soll genau einen POST unter /api/v1/analyze (Engine) exponieren."""
    schema = client.get("/openapi.json").json()
    post_analyze = [
        path
        for path, ops in schema.get("paths", {}).items()
        if path.rstrip("/") == "/api/v1/analyze" and "post" in ops
    ]
    assert post_analyze == ["/api/v1/analyze"], post_analyze
