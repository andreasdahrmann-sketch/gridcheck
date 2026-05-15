"""Tests fuer KI-Feedback-Loop und Kalibrierungs-Endpoint."""
from __future__ import annotations

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_feedback_happy_path(isolierte_ki_feedback):
    payload = {
        "ki_entscheidung": "A",
        "nb_entscheidung": "B",
        "kommentar": "VNB fordert Auflagen nach Detailpruefung.",
        "score_gesamt": 78,
        "quelle": "netzbetreiber",
    }
    r = client.post("/api/v1/ki/feedback", json=payload)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "OK"
    assert body["feedback"]["feedback_nummer"] == 1
    assert body["kalibrierung"]["samples"] == 1
    assert body["kalibrierung"]["kalibrierungsfaktor"] < 1.0


def test_feedback_validation_error_returns_422(isolierte_ki_feedback):
    payload = {
        "ki_entscheidung": "A",
        "nb_entscheidung": "X",
        "quelle": "netzbetreiber",
    }
    r = client.post("/api/v1/ki/feedback", json=payload)
    assert r.status_code == 422


def test_get_calibration_no_feedback(isolierte_ki_feedback):
    r = client.get("/api/v1/ki/calibration")
    assert r.status_code == 200
    body = r.json()
    assert body["samples"] == 0
    assert body["kalibrierungsfaktor"] == 1.0
    assert body["status"] == "NO_FEEDBACK"


def test_verify_chain_empty_ok(isolierte_ki_feedback):
    r = client.get("/api/v1/ki/verify")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["anzahl"] == 0
    assert body["fehler"] == []


def test_verify_chain_with_entries_ok(isolierte_ki_feedback):
    client.post(
        "/api/v1/ki/feedback",
        json={"ki_entscheidung": "A", "nb_entscheidung": "A", "quelle": "netzbetreiber"},
    )
    client.post(
        "/api/v1/ki/feedback",
        json={"ki_entscheidung": "B", "nb_entscheidung": "C", "quelle": "audit"},
    )

    r = client.get("/api/v1/ki/verify")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["anzahl"] == 2


def test_count_empty(isolierte_ki_feedback):
    r = client.get("/api/v1/ki/count")
    assert r.status_code == 200
    body = r.json()
    assert body["anzahl"] == 0
    assert body["letzte_feedback_nummer"] is None
    assert body["letzter_hash"] is None


def test_count_and_get_by_hash(isolierte_ki_feedback):
    r1 = client.post(
        "/api/v1/ki/feedback",
        json={"ki_entscheidung": "A", "nb_entscheidung": "A", "quelle": "netzbetreiber"},
    )
    assert r1.status_code == 200, r1.text
    h = r1.json()["feedback"]["hash"]

    rc = client.get("/api/v1/ki/count")
    assert rc.status_code == 200
    cb = rc.json()
    assert cb["anzahl"] == 1
    assert cb["letzte_feedback_nummer"] == 1
    assert cb["letzter_hash"] == h

    rg = client.get(f"/api/v1/ki/{h}")
    assert rg.status_code == 200, rg.text
    gb = rg.json()
    assert gb["hash"] == h
    assert gb["feedback_nummer"] == 1


def test_get_by_hash_invalid_and_not_found(isolierte_ki_feedback):
    r_bad = client.get("/api/v1/ki/abc")
    assert r_bad.status_code == 400
    assert r_bad.json()["detail"]["code"] == "KI_FEEDBACK_HASH_INVALID"

    r_nf = client.get("/api/v1/ki/" + ("0" * 64))
    assert r_nf.status_code == 404
    assert r_nf.json()["detail"]["code"] == "KI_FEEDBACK_NOT_FOUND"
