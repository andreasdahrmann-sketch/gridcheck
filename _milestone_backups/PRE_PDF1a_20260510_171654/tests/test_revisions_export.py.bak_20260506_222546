"""B.6 - Tests fuer Revisions-Export (CSV/JSON/PDF)."""
import json
import pytest
from fastapi.testclient import TestClient

from main import app
from engine.revision import speichere_revision
from services.revisions_export import export_json, export_csv, export_pdf


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def chain_mit_3(monkeypatch, tmp_path):
    """Patched Pfad + 3 Eintraege."""
    pfad = tmp_path / "revisionen.jsonl"
    from engine import revision as rm
    monkeypatch.setattr(rm, "REVISIONS_PFAD", str(pfad))
    for i in range(3):
        speichere_revision(
            {"input": {"i": i}, "result": {"score": i * 10}},
            engine_version="test-1.0",
        )
    return pfad


# ===================== Service-Layer Tests =====================

class TestExportJson:
    def test_leer(self, monkeypatch, tmp_path):
        from engine import revision as rm
        monkeypatch.setattr(rm, "REVISIONS_PFAD", str(tmp_path / "leer.jsonl"))
        data = export_json()
        assert data["audit"]["anzahl_eintraege"] == 0
        assert data["audit"]["chain_ok"] is True
        assert data["revisionen"] == []

    def test_mit_eintraegen(self, chain_mit_3):
        data = export_json()
        assert data["audit"]["anzahl_eintraege"] == 3
        assert data["audit"]["chain_ok"] is True
        assert len(data["revisionen"]) == 3
        assert data["audit"]["letzter_hash"] is not None


class TestExportCsv:
    def test_leer_hat_header(self, monkeypatch, tmp_path):
        from engine import revision as rm
        monkeypatch.setattr(rm, "REVISIONS_PFAD", str(tmp_path / "leer.jsonl"))
        csv_text = export_csv()
        assert "revisionsnummer" in csv_text
        assert "hash" in csv_text
        assert csv_text.count("\n") == 1  # nur Header

    def test_mit_eintraegen(self, chain_mit_3):
        csv_text = export_csv()
        zeilen = csv_text.strip().split("\n")
        assert len(zeilen) == 4  # Header + 3
        assert "test-1.0" in csv_text


class TestExportPdf:
    def test_leer_erzeugt_pdf(self, monkeypatch, tmp_path):
        from engine import revision as rm
        monkeypatch.setattr(rm, "REVISIONS_PFAD", str(tmp_path / "leer.jsonl"))
        pdf = export_pdf()
        assert pdf.startswith(b"%PDF-")
        assert len(pdf) > 1000

    def test_mit_eintraegen(self, chain_mit_3):
        pdf = export_pdf()
        assert pdf.startswith(b"%PDF-")
        assert len(pdf) > 2000


# ===================== API-Endpoint Tests =====================

class TestExportEndpoints:
    def test_json_endpoint(self, client, chain_mit_3):
        r = client.get("/api/v2/revisions/export/json")
        assert r.status_code == 200
        body = r.json()
        assert body["audit"]["anzahl_eintraege"] == 3
        assert len(body["revisionen"]) == 3

    def test_csv_endpoint(self, client, chain_mit_3):
        r = client.get("/api/v2/revisions/export/csv")
        assert r.status_code == 200
        assert "text/csv" in r.headers["content-type"]
        assert "attachment" in r.headers.get("content-disposition", "")
        assert "revisionsnummer" in r.text

    def test_pdf_endpoint(self, client, chain_mit_3):
        r = client.get("/api/v2/revisions/export/pdf")
        assert r.status_code == 200
        assert r.headers["content-type"] == "application/pdf"
        assert r.content.startswith(b"%PDF-")

    def test_export_routes_kollidieren_nicht_mit_hash_lookup(self, client, chain_mit_3):
        """Sicherstellen: /export/json wird nicht als hash-lookup interpretiert."""
        r = client.get("/api/v2/revisions/export/json")
        assert r.status_code == 200  # nicht 400 (ungueltiger hash)
