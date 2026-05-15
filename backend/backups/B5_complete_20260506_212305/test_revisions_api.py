"""
B.5 - API-Tests fuer /api/v2/revisions/* (read-only, revisionssicher).
"""
import pytest
from fastapi.testclient import TestClient
from main import app
from engine.revision import speichere_revision

client = TestClient(app)


def _seed(n: int = 2):
    """Erzeugt n Revisionen, gibt Liste der Eintraege zurueck."""
    out = []
    for i in range(1, n + 1):
        r = speichere_revision(
            {"input": {"leistung_mw": float(i)}, "result": {"score": i}},
            engine_version="test-1.0.0",
        )
        out.append(r)
    return out


class TestVerifyEndpoint:
    def test_verify_leer(self, isolierte_revisionen):
        r = client.get("/api/v2/revisions/verify")
        assert r.status_code == 200
        body = r.json()
        assert body["ok"] is True
        assert body["anzahl"] == 0

    def test_verify_mit_eintraegen(self, isolierte_revisionen):
        _seed(3)
        r = client.get("/api/v2/revisions/verify")
        assert r.status_code == 200
        body = r.json()
        assert body["ok"] is True
        assert body["anzahl"] == 3


class TestCountEndpoint:
    def test_count(self, isolierte_revisionen):
        _seed(2)
        r = client.get("/api/v2/revisions/count")
        assert r.status_code == 200
        assert r.json()["anzahl"] == 2


class TestGetByHash:
    def test_404_bei_unbekanntem_hash(self, isolierte_revisionen):
        r = client.get("/api/v2/revisions/" + "0" * 64)
        assert r.status_code == 404

    def test_200_bei_echtem_hash(self, isolierte_revisionen):
        eintraege = _seed(2)
        h = eintraege[0]["hash"]
        r = client.get(f"/api/v2/revisions/{h}")
        assert r.status_code == 200
        body = r.json()
        assert body["hash"] == h
        assert body["revisionsnummer"] == 1
