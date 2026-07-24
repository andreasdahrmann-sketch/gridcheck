"""Tests fuer KI-Feedback-Loop und Kalibrierungs-Endpoint."""
from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from db.database import SessionLocal
from db.models import Project, ProjectMember, User
from engine.revision import speichere_revision
from main import app
from services.auth_service import approve_netzbetreiber

client = TestClient(app)


def _auth_identity(*, admin: bool = False, verified_vnb: bool = True) -> dict[str, str | int]:
    email = f"ki-feedback-{uuid.uuid4().hex}@example.com"
    role = "netzbetreiber" if verified_vnb and not admin else "projektierer"
    reg = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Passwort123!", "role": role},
    )
    assert reg.status_code == 200, reg.text
    user_id = reg.json()["id"]
    if admin or verified_vnb:
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.email == email).first()
            assert user is not None
            if admin:
                user.role = "admin"
                db.commit()
            else:
                approve_netzbetreiber(db, user_id=user.id)
        finally:
            db.close()
    login = client.post("/api/v1/auth/login", json={"email": email, "password": "Passwort123!"})
    assert login.status_code == 200, login.text
    return {
        "email": email,
        "user_id": user_id,
        "headers": {"Authorization": f"Bearer {login.json()['access_token']}"},
    }


def _auth_headers(*, admin: bool = False) -> dict[str, str]:
    return _auth_identity(admin=admin)["headers"]  # type: ignore[return-value]


def _create_revision_hash(*, actor_user_id: int, project_id: int | None = None) -> str:
    revision = speichere_revision(
        {"eingabe": {"leistung_mw": 5.0}, "fazit": {"entscheidung": "A"}},
        actor_user_id=actor_user_id,
        project_id=project_id,
        action_type="ANALYSIS_COMPLETED",
        engine_version="test-ki",
    )
    return revision["hash"]


def test_feedback_happy_path(isolierte_ki_feedback, isolierte_revisionen):
    identity = _auth_identity()
    headers = identity["headers"]
    payload = {
        "feedback_typ": "korrigiert",
        "ki_entscheidung": "A",
        "nb_entscheidung": "B",
        "kommentar": "VNB fordert Auflagen nach Detailpruefung.",
        "revision_hash": _create_revision_hash(actor_user_id=int(identity["user_id"])),
        "score_gesamt": 78,
        "confidence_snapshot": 64,
        "anomaly_flags": ["Hoher Score bei begrenzter Datenqualitaet."],
        "quelle": "netzbetreiber",
    }
    r = client.post("/api/v1/ki/feedback", json=payload, headers=headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "OK"
    assert body["feedback"]["feedback_nummer"] == 1
    assert body["feedback"]["feedback_typ"] == "korrigiert"
    assert body["kalibrierung"]["samples"] == 1
    assert body["kalibrierung"]["kalibrierungsfaktor"] < 1.0
    assert body["lernstatus"]["samples_total"] == 1
    assert body["lernstatus"]["korrigiert"] == 1
    assert body["audit_revision"]["hash"]


def test_feedback_rejects_unverified_netzbetreiber_source(isolierte_ki_feedback, isolierte_revisionen):
    identity = _auth_identity(verified_vnb=False)
    payload = {
        "feedback_typ": "korrigiert",
        "ki_entscheidung": "A",
        "nb_entscheidung": "B",
        "revision_hash": _create_revision_hash(actor_user_id=int(identity["user_id"])),
        "quelle": "netzbetreiber",
    }

    response = client.post("/api/v1/ki/feedback", json=payload, headers=identity["headers"])

    assert response.status_code == 403, response.text
    assert response.json()["detail"]["code"] == "VNB_ACCESS_DENIED"


def test_feedback_bestaetigung_uebernimmt_ki_entscheidung(isolierte_ki_feedback, isolierte_revisionen):
    identity = _auth_identity()
    headers = identity["headers"]
    payload = {
        "ki_entscheidung": "B",
        "feedback_typ": "bestaetigt",
        "revision_hash": _create_revision_hash(actor_user_id=int(identity["user_id"])),
        "quelle": "netzbetreiber",
    }
    r = client.post("/api/v1/ki/feedback", json=payload, headers=headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["feedback"]["feedback_typ"] == "bestaetigt"
    assert body["kalibrierung"]["samples"] == 1
    assert body["lernstatus"]["bestaetigt"] == 1


def test_feedback_validation_error_returns_422(isolierte_ki_feedback, isolierte_revisionen):
    identity = _auth_identity()
    headers = identity["headers"]
    payload = {
        "ki_entscheidung": "A",
        "nb_entscheidung": "X",
        "revision_hash": _create_revision_hash(actor_user_id=int(identity["user_id"])),
        "quelle": "netzbetreiber",
    }
    r = client.post("/api/v1/ki/feedback", json=payload, headers=headers)
    assert r.status_code == 422


def test_get_calibration_no_feedback(isolierte_ki_feedback):
    r = client.get("/api/v1/ki/calibration", headers=_auth_headers(admin=True))
    assert r.status_code == 200
    body = r.json()
    assert body["samples"] == 0
    assert body["kalibrierungsfaktor"] == 1.0
    assert body["status"] == "NO_FEEDBACK"


def test_get_learning_status(isolierte_ki_feedback, isolierte_revisionen):
    user_identity = _auth_identity()
    user_headers = user_identity["headers"]
    admin_headers = _auth_headers(admin=True)
    client.post(
        "/api/v1/ki/feedback",
        json={
            "ki_entscheidung": "A",
            "feedback_typ": "bestaetigt",
            "revision_hash": _create_revision_hash(actor_user_id=int(user_identity["user_id"])),
            "quelle": "netzbetreiber",
        },
        headers=user_headers,
    )
    r = client.get("/api/v1/ki/learning-status", headers=admin_headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["samples_total"] == 1
    assert body["status"] == "LOW_SIGNAL"


def test_verify_chain_empty_ok(isolierte_ki_feedback):
    r = client.get("/api/v1/ki/verify", headers=_auth_headers(admin=True))
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["anzahl"] == 0
    assert body["fehler"] == []


def test_verify_chain_with_entries_ok(isolierte_ki_feedback, isolierte_revisionen):
    user_identity = _auth_identity()
    user_headers = user_identity["headers"]
    admin_headers = _auth_headers(admin=True)
    client.post(
        "/api/v1/ki/feedback",
        json={
            "ki_entscheidung": "A",
            "nb_entscheidung": "A",
            "revision_hash": _create_revision_hash(actor_user_id=int(user_identity["user_id"])),
            "quelle": "netzbetreiber",
        },
        headers=user_headers,
    )
    client.post(
        "/api/v1/ki/feedback",
        json={
            "ki_entscheidung": "B",
            "nb_entscheidung": "C",
            "revision_hash": _create_revision_hash(actor_user_id=int(user_identity["user_id"])),
            "quelle": "audit",
        },
        headers=user_headers,
    )

    r = client.get("/api/v1/ki/verify", headers=admin_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["anzahl"] == 2


def test_count_empty(isolierte_ki_feedback):
    r = client.get("/api/v1/ki/count", headers=_auth_headers(admin=True))
    assert r.status_code == 200
    body = r.json()
    assert body["anzahl"] == 0
    assert body["letzte_feedback_nummer"] is None
    assert body["letzter_hash"] is None


def test_count_and_get_by_hash(isolierte_ki_feedback, isolierte_revisionen):
    user_identity = _auth_identity()
    user_headers = user_identity["headers"]
    admin_headers = _auth_headers(admin=True)
    r1 = client.post(
        "/api/v1/ki/feedback",
        json={
            "ki_entscheidung": "A",
            "nb_entscheidung": "A",
            "revision_hash": _create_revision_hash(actor_user_id=int(user_identity["user_id"])),
            "quelle": "netzbetreiber",
        },
        headers=user_headers,
    )
    assert r1.status_code == 200, r1.text
    h = r1.json()["feedback"]["hash"]

    rc = client.get("/api/v1/ki/count", headers=admin_headers)
    assert rc.status_code == 200
    cb = rc.json()
    assert cb["anzahl"] == 1
    assert cb["letzte_feedback_nummer"] == 1
    assert cb["letzter_hash"] == h

    rg = client.get(f"/api/v1/ki/{h}", headers=admin_headers)
    assert rg.status_code == 200, rg.text
    gb = rg.json()
    assert gb["hash"] == h
    assert gb["feedback_nummer"] == 1


def test_get_feedback_by_revision_hash(isolierte_ki_feedback, isolierte_revisionen):
    user_identity = _auth_identity()
    user_headers = user_identity["headers"]
    admin_headers = _auth_headers(admin=True)
    revision_hash = _create_revision_hash(actor_user_id=int(user_identity["user_id"]))
    r_post = client.post(
        "/api/v1/ki/feedback",
        json={
            "ki_entscheidung": "A",
            "feedback_typ": "bestaetigt",
            "revision_hash": revision_hash,
            "quelle": "netzbetreiber",
        },
        headers=user_headers,
    )
    assert r_post.status_code == 200, r_post.text

    r = client.get(f"/api/v1/ki/revision/{revision_hash}", headers=admin_headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["daten"]["revision_hash"] == revision_hash


def test_feedback_with_unknown_revision_returns_404(isolierte_ki_feedback, isolierte_revisionen):
    headers = _auth_headers()
    r = client.post(
        "/api/v1/ki/feedback",
        json={
            "ki_entscheidung": "A",
            "feedback_typ": "bestaetigt",
            "revision_hash": "0" * 64,
            "quelle": "netzbetreiber",
        },
        headers=headers,
    )
    assert r.status_code == 404
    assert r.json()["detail"]["code"] == "KI_FEEDBACK_REVISION_NOT_FOUND"


def test_feedback_requires_revision_hash(isolierte_ki_feedback):
    headers = _auth_headers()
    r = client.post(
        "/api/v1/ki/feedback",
        json={
            "ki_entscheidung": "A",
            "feedback_typ": "bestaetigt",
            "quelle": "netzbetreiber",
        },
        headers=headers,
    )
    assert r.status_code == 422, r.text
    assert r.json()["detail"]["code"] == "KI_FEEDBACK_REVISION_REQUIRED"


def test_feedback_rejects_foreign_revision(isolierte_ki_feedback, isolierte_revisionen):
    owner_identity = _auth_identity()
    foreign_headers = _auth_headers()
    revision_hash = _create_revision_hash(actor_user_id=int(owner_identity["user_id"]))
    r = client.post(
        "/api/v1/ki/feedback",
        json={
            "ki_entscheidung": "A",
            "feedback_typ": "bestaetigt",
            "revision_hash": revision_hash,
            "quelle": "netzbetreiber",
        },
        headers=foreign_headers,
    )
    assert r.status_code == 403, r.text
    assert r.json()["detail"]["code"] == "KI_FEEDBACK_FORBIDDEN"


def test_feedback_rejects_viewer_on_project_revision(isolierte_ki_feedback, isolierte_revisionen):
    owner_identity = _auth_identity()
    viewer_identity = _auth_identity()
    db = SessionLocal()
    try:
        project = Project(
            name="KI Feedback Guard",
            plz="10115",
            typ="pv",
            leistung_kw=1200,
            owner_user_id=int(owner_identity["user_id"]),
        )
        db.add(project)
        db.flush()
        db.add(
            ProjectMember(
                project_id=project.id,
                user_id=int(owner_identity["user_id"]),
                project_role="owner",
            )
        )
        db.add(
            ProjectMember(
                project_id=project.id,
                user_id=int(viewer_identity["user_id"]),
                project_role="viewer",
            )
        )
        db.commit()
        project_id = project.id
    finally:
        db.close()

    revision_hash = _create_revision_hash(
        actor_user_id=int(owner_identity["user_id"]),
        project_id=project_id,
    )
    r = client.post(
        "/api/v1/ki/feedback",
        json={
            "ki_entscheidung": "A",
            "feedback_typ": "bestaetigt",
            "revision_hash": revision_hash,
            "quelle": "netzbetreiber",
        },
        headers=viewer_identity["headers"],
    )
    assert r.status_code == 403, r.text
    assert r.json()["detail"]["code"] == "KI_FEEDBACK_FORBIDDEN"


def test_get_by_hash_invalid_and_not_found(isolierte_ki_feedback):
    headers = _auth_headers(admin=True)
    r_bad = client.get("/api/v1/ki/abc", headers=headers)
    assert r_bad.status_code == 400
    assert r_bad.json()["detail"]["code"] == "KI_FEEDBACK_HASH_INVALID"

    r_nf = client.get("/api/v1/ki/" + ("0" * 64), headers=headers)
    assert r_nf.status_code == 404
    assert r_nf.json()["detail"]["code"] == "KI_FEEDBACK_NOT_FOUND"


def test_ki_feedback_endpoints_require_authentication(isolierte_ki_feedback):
    # Shared TestClient carries cookies from earlier logins; CSRF then returns 403 before 401.
    fresh = TestClient(app)
    post = fresh.post("/api/v1/ki/feedback", json={"ki_entscheidung": "A", "quelle": "netzbetreiber"})
    assert post.status_code == 401

    read = fresh.get("/api/v1/ki/count")
    assert read.status_code == 401


def test_ki_feedback_read_endpoints_require_admin(isolierte_ki_feedback):
    headers = _auth_headers()
    read = client.get("/api/v1/ki/count", headers=headers)
    assert read.status_code == 403
    assert read.json()["detail"]["code"] == "AUTH_FORBIDDEN"
