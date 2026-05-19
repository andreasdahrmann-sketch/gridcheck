from __future__ import annotations

import base64
import hashlib
import io
import json
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from db.database import Base, get_db
from db.models import AnalysisRun, AuditLog, Project, ProjectMember, ReportRevisionRecord, User, make_checksum
from engine.revision import speichere_revision
from main import app
from tests.postgres_test_utils import build_isolated_postgres_session_factory


def build_client():
    _, TestingSessionLocal, cleanup = build_isolated_postgres_session_factory(Base.metadata, label="auth_api")

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    client._gridcheck_cleanup = cleanup  # type: ignore[attr-defined]
    client._gridcheck_session_factory = TestingSessionLocal  # type: ignore[attr-defined]
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


def _db_session(client: TestClient):
    return client._gridcheck_session_factory()  # type: ignore[attr-defined]


def _legacy_pbkdf2_hash(password: str) -> str:
    salt = b"gridcheck-legacy"
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120_000)
    salt_b64 = base64.urlsafe_b64encode(salt).decode("utf-8").rstrip("=")
    digest_b64 = base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")
    return f"{salt_b64}.{digest_b64}"


def _reset_rate_limit_state() -> None:
    from core import rate_limit as rate_limit_mod

    rate_limit_mod._MEM_BUCKETS.clear()
    rate_limit_mod._REDIS_CLIENT = None


def setup_function(function=None):
    _reset_rate_limit_state()


def _rich_project_inputs(*, customer_type: str = "investor") -> dict:
    return {
        "kundentyp": customer_type,
        "anlagentyp": "solar",
        "anschlussleistung_kw": 1200,
        "antragsteller": "SPV Hannover Nord GmbH",
        "project_components": [{"component_type": "pv", "capacity_kw": 1200}],
        "project_location": {
            "latitude": 52.379189,
            "longitude": 9.76199,
            "address_hint": "Gewerbepark Nord",
        },
        "environmental_route": {
            "route_length_km": 4.2,
            "route_complexity": "hoch",
            "notes": "Interne Trassenannahme",
        },
        "umspannwerk": {
            "datenquelle": "planner_assumption",
            "trafos": [{"label": "T1", "sn_mva": 40.0, "belastung_aktuell_mw": 32.5}],
        },
        "stakeholder_context": {"customer_type": customer_type, "priority_focus": "kosten"},
    }


def _rich_analysis_result() -> dict:
    return {
        "status": "OK",
        "score": 82,
        "scores": {"gesamt": 82},
        "machbarkeit_stufe": "orange",
        "spannungsbewertung": "Spannungsband mit Reserve",
        "n1_hinweis": "N-1 nur mit konservativen Annahmen belastbar.",
        "warnungen": ["Interner Engpass moeglich"],
        "empfehlungen": ["Variantenvergleich starten"],
        "fazit": {"entscheidung": "B"},
        "datenqualitaet": {"klasse": "B", "text": "Projekt- und Netzdaten teilweise verifiziert."},
        "projektprofil": {
            "total_installed_kw": 1200,
            "component_count": 1,
            "is_hybrid": False,
            "component_summary": ["PV 1.200 kW"],
            "max_export_kw": 1200,
            "max_import_kw": 50,
            "summary": "PV-Standort mit klassischem Einspeiseprofil.",
        },
        "route_environment": {
            "risk_score": 74,
            "risk_level": "hoch",
            "drivers": ["Querung durch Fremdgrundstuecke"],
            "mitigation": ["Alternative Trasse pruefen"],
            "summary": "Trassenrisiko erhoeht.",
        },
        "stakeholder_bewertung": {
            "netzbetreiber_score": 58,
            "projektierer_score": 73,
            "umsetzung_score": 61,
            "konflikt_level": "mittel",
            "konflikt_summary": "Auflagen koennen Terminplan verschieben.",
            "recommended_focus": "Trasse und technische Auflagen synchronisieren.",
        },
        "kosten_indikation_eur": 1_500_000,
        "kostenklasse": "hoch",
        "kosten_bandbreite": {
            "niedrig_eur": 1_200_000,
            "basis_eur": 1_500_000,
            "hoch_eur": 1_900_000,
        },
        "kurzschluss": {
            "ik_min_kA": 8.2,
            "ik_max_kA": 15.7,
            "sk_am_nvp_mva": 244.0,
            "bewertung": "Technisch ausreichend.",
        },
        "n1": {
            "n1_sicher": False,
            "n1_klasse": "N1-3",
            "topologie_text": "Stich mit begrenzter Reserve",
            "detail_text": "Reservepfad nur mit Nachruestung belastbar.",
            "dso_daten_vorhanden": False,
            "detail_empfehlungen": ["Reservepfad im Detail pruefen"],
            "nachweise_vorhanden": ["Grunddaten"],
            "nachweise_fehlend": ["Verifizierte Abgangslast"],
        },
        "n1_analyse": {
            "gesamt": {"bewertung": "ROT", "stufenbegruendung": "Abgangsreserve unklar."},
            "annahmen": [{"feld": "reserve_n1_a", "wert": 0, "quelle": "planner_assumption"}],
        },
        "ki": {
            "konfidenz_prozent": 71,
            "aehnliche_faelle": 9,
            "kalibrierung": {"status": "ok", "kalibrierungsfaktor": 1.03},
            "feedback_loop": {"status": "ok", "samples_total": 12, "linked_samples": 7, "bestaetigungsquote": 0.75},
            "anomalie_check": {"is_anomaly": False, "severity": "niedrig", "score": 0.1, "summary": "Keine Auffaelligkeit."},
            "hinweise": ["Vorlaeufige KI-Einordnung."],
        },
        "revision": {"hash": "a" * 64},
        "history": {"analysis_run_id": 123},
        "billing_access": {
            "offer_id": "professional_anschlussstrategie",
            "package_scope": "professional",
            "report_scope": "professional",
            "usage_bucket": "oneoff",
            "ops_followup_required": True,
        },
    }


def _persist_project_analysis_run(
    client: TestClient,
    *,
    owner_email: str,
    project_id: int,
    request_payload: dict | None = None,
    result_payload: dict | None = None,
) -> int:
    payload = request_payload or {
        "project_id": project_id,
        "nennspannung": 20,
        "leistung_mw": 1.2,
        "leitungstyp": "NA2XS2Y240",
        "entfernung_km": 4.2,
        "anschlussart": "Einspeisung",
        "plz": "10115",
        "anlagentyp": "PV",
    }
    result = result_payload or _rich_analysis_result()
    with _db_session(client) as db:
        owner = db.query(User).filter(User.email == owner_email).first()
        assert owner is not None
        revision = speichere_revision(
            result,
            actor_user_id=owner.id,
            action_type="ANALYSIS_COMPLETED",
            project_id=project_id,
            engine_version="test-auth-project-report",
            db=db,
        )
        persisted_result = dict(result)
        persisted_result["revision"] = {"hash": revision["hash"]}
        run = AnalysisRun(
            user_id=owner.id,
            project_id=project_id,
            source="interactive",
            status="completed",
            input_json=json.dumps(payload, ensure_ascii=False),
            request_checksum=make_checksum(payload),
            result_json=json.dumps(persisted_result, ensure_ascii=False),
            result_checksum=make_checksum(persisted_result),
            score=82,
            decision_code="B",
            revision_hash=revision["hash"],
            offer_id="professional_anschlussstrategie",
            package_scope="professional",
            usage_bucket="oneoff",
            billing_category="paid",
            free_quota_consumed=False,
            created_at=datetime.now(timezone.utc),
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        return run.id


def test_auth_register_login_and_me():
    client = build_client()
    try:
        tokens = _register_and_login(client, "alice@example.com")
        me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"})
        assert me.status_code == 200
        assert me.json()["email"] == "alice@example.com"
    finally:
        _close_client(client)


def test_password_policy_is_consistent_for_register_change_and_legacy_upgrade():
    client = build_client()
    try:
        weak_register = client.post(
            "/api/v1/auth/register",
            json={"email": "weak@example.com", "password": "Passwort1234", "role": "projektierer"},
        )
        assert weak_register.status_code == 400, weak_register.text
        assert weak_register.json()["detail"]["code"] == "PASSWORD_TOO_WEAK"

        primary_tokens = _register_and_login(client, "legacy-upgrade@example.com")
        with _db_session(client) as db:
            legacy_user = User(
                email="legacy-hash@example.com",
                password_hash=_legacy_pbkdf2_hash("Passwort123!"),
                role="projektierer",
                is_active=True,
            )
            db.add(legacy_user)
            db.commit()

        legacy_login = client.post(
            "/api/v1/auth/login",
            json={"email": "legacy-hash@example.com", "password": "Passwort123!"},
        )
        assert legacy_login.status_code == 200, legacy_login.text
        with _db_session(client) as db:
            upgraded_user = db.query(User).filter(User.email == "legacy-hash@example.com").first()
            assert upgraded_user is not None
            assert upgraded_user.password_hash.startswith("$2")

        password_headers = {"Authorization": f"Bearer {primary_tokens['access_token']}"}
        weak_change = client.patch(
            "/api/v1/users/me/password",
            headers=password_headers,
            json={"current_password": "Passwort123!", "new_password": "NeuesPasswort12"},
        )
        assert weak_change.status_code == 400, weak_change.text
        assert weak_change.json()["detail"]["code"] == "PASSWORD_TOO_WEAK"

        reused = client.patch(
            "/api/v1/users/me/password",
            headers=password_headers,
            json={"current_password": "Passwort123!", "new_password": "Passwort123!"},
        )
        assert reused.status_code == 400, reused.text
        assert reused.json()["detail"]["code"] == "PASSWORD_REUSE_FORBIDDEN"

        strong_change = client.patch(
            "/api/v1/users/me/password",
            headers=password_headers,
            json={"current_password": "Passwort123!", "new_password": "NeuPasswort123!"},
        )
        assert strong_change.status_code == 200, strong_change.text

        old_login = client.post(
            "/api/v1/auth/login",
            json={"email": "legacy-upgrade@example.com", "password": "Passwort123!"},
        )
        assert old_login.status_code == 401, old_login.text
        new_login = client.post(
            "/api/v1/auth/login",
            json={"email": "legacy-upgrade@example.com", "password": "NeuPasswort123!"},
        )
        assert new_login.status_code == 200, new_login.text
    finally:
        _close_client(client)


def test_admin_self_registration_is_blocked_but_preprovisioned_admin_can_login():
    client = build_client()
    try:
        blocked = client.post(
            "/api/v1/auth/register",
            json={"email": "blocked-admin@example.com", "password": "Passwort123!", "role": "admin"},
        )
        assert blocked.status_code == 422, blocked.text

        _register_and_login(client, "internal-admin@example.com")
        with _db_session(client) as db:
            from db.models import User

            admin = db.query(User).filter(User.email == "internal-admin@example.com").first()
            assert admin is not None
            admin.role = "admin"
            db.commit()

        login = client.post(
            "/api/v1/auth/login",
            json={"email": "internal-admin@example.com", "password": "Passwort123!"},
        )
        assert login.status_code == 200, login.text
        me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {login.json()['access_token']}"})
        assert me.status_code == 200, me.text
        assert me.json()["role"] == "admin"
    finally:
        _close_client(client)


def test_legacy_stakeholder_route_requires_auth_role_and_persists_owner_guardrails():
    client = build_client()
    payload = {
        "projektname": "Solar Nord",
        "plz": "10115",
        "anlagentyp": "pv",
        "leistung_kw": 500.0,
        "spannungsebene": "20",
        "cos_phi": 0.95,
        "einspeiseart": "volleinspeisung",
        "speicher": False,
        "speicher_kwh": None,
        "trafo_mva": 0.63,
        "leitungslaenge_km": 1.0,
        "leitungstyp": "NAYY",
        "querschnitt_mm2": "150",
        "netzverknuepfungspunkt": "",
        "skv_mva": None,
        "parallelsysteme": 1,
        "eigentumsgrenze": "HAK",
        "vorbelastung_mw": 0,
        "netz_typ": "kabel",
        "gewuenschte_massnahmen": [],
        "pruefer_id": "pr-1",
        "aktenzeichen": "AZ-12345",
        "pruefvermerk": "",
    }
    try:
        anonymous = client.post("/api/stakeholder/netzbetreiber", json=payload)
        assert anonymous.status_code == 401, anonymous.text

        wrong_role_register = client.post(
            "/api/v1/auth/register",
            json={"email": "stakeholder-endkunde@example.com", "password": "Passwort123!", "role": "endkunde"},
        )
        assert wrong_role_register.status_code == 200, wrong_role_register.text
        wrong_role_login = client.post(
            "/api/v1/auth/login",
            json={"email": "stakeholder-endkunde@example.com", "password": "Passwort123!"},
        )
        assert wrong_role_login.status_code == 200, wrong_role_login.text
        wrong_role = client.post(
            "/api/stakeholder/netzbetreiber",
            headers={"Authorization": f"Bearer {wrong_role_login.json()['access_token']}"},
            json=payload,
        )
        assert wrong_role.status_code == 403, wrong_role.text
        assert wrong_role.json()["detail"]["code"] == "STAKEHOLDER_FORBIDDEN"

        nb_register = client.post(
            "/api/v1/auth/register",
            json={"email": "stakeholder-vnb@example.com", "password": "Passwort123!", "role": "netzbetreiber"},
        )
        assert nb_register.status_code == 200, nb_register.text
        user_id = nb_register.json()["id"]
        nb_login = client.post(
            "/api/v1/auth/login",
            json={"email": "stakeholder-vnb@example.com", "password": "Passwort123!"},
        )
        assert nb_login.status_code == 200, nb_login.text

        authorized = client.post(
            "/api/stakeholder/netzbetreiber",
            headers={"Authorization": f"Bearer {nb_login.json()['access_token']}"},
            json=payload,
        )
        assert authorized.status_code == 200, authorized.text
        project_id = authorized.json()["project_id"]

        with _db_session(client) as db:
            project = db.get(Project, project_id)
            assert project is not None
            assert project.owner_user_id == user_id
            role_inputs = json.loads(project.role_inputs)
            assert role_inputs["kundentyp"] == "netzbetreiber"
            membership = (
                db.query(ProjectMember)
                .filter(ProjectMember.project_id == project_id, ProjectMember.user_id == user_id)
                .first()
            )
            assert membership is not None
            assert membership.project_role == "owner"
            audit = (
                db.query(AuditLog)
                .filter(
                    AuditLog.project_id == project_id,
                    AuditLog.action == "STAKEHOLDER_NETZBETREIBER",
                )
                .order_by(AuditLog.id.desc())
                .first()
            )
            assert audit is not None
            detail = json.loads(audit.detail)
            assert detail["actor_user_id"] == user_id
            assert detail["payload"]["request"]["kundentyp"] == "netzbetreiber"
    finally:
        _close_client(client)


def test_history_lists_accessible_project_summaries():
    client = build_client()
    try:
        owner_tokens = _register_and_login(client, "history-owner@example.com")
        headers = {"Authorization": f"Bearer {owner_tokens['access_token']}"}

        created = client.post(
            "/api/v1/projects",
            headers=headers,
            json={
                "name": "Historie Projekt",
                "plz": "30159",
                "typ": "pv",
                "leistung_kw": 500,
            },
        )
        assert created.status_code == 200, created.text
        project_id = created.json()["id"]

        history = client.get("/api/v1/history", headers=headers)
        assert history.status_code == 200, history.text
        items = history.json()
        assert isinstance(items, list)
        match = next((item for item in items if item["id"] == project_id), None)
        assert match is not None
        assert match["name"] == "Historie Projekt"
        assert match["plz"] == "30159"
        assert match["leistung_kw"] == 500
    finally:
        _close_client(client)


def test_project_crud_sharing_and_upload(monkeypatch):
    client = build_client()
    try:
        owner_tokens = _register_and_login(client, "owner@example.com")
        user = client.post(
            "/api/v1/auth/register",
            json={"email": "viewer@example.com", "password": "Passwort123!", "role": "endkunde"},
        )
        assert user.status_code == 200
        viewer_id = user.json()["id"]
        headers = {"Authorization": f"Bearer {owner_tokens['access_token']}"}

        created = client.post(
            "/api/v1/projects",
            headers=headers,
            json={
                "name": "P1",
                "plz": "10115",
                "typ": "pv",
                "leistung_kw": 1200,
                "role_inputs": {
                    "anlagentyp": "solar",
                    "anschlussleistung_kw": 1200,
                    "project_components": [{"component_type": "pv", "capacity_kw": 1200}],
                },
            },
        )
        assert created.status_code == 200, created.text
        project_id = created.json()["id"]
        assert created.json()["role_inputs"]["anlagentyp"] == "solar"

        shared = client.post(
            f"/api/v1/projects/{project_id}/share",
            headers=headers,
            json={"target_user_id": viewer_id, "project_role": "viewer"},
        )
        assert shared.status_code == 200, shared.text
        viewer_login = client.post(
            "/api/v1/auth/login",
            json={"email": "viewer@example.com", "password": "Passwort123!"},
        )
        viewer_headers = {"Authorization": f"Bearer {viewer_login.json()['access_token']}"}
        viewer_list = client.get("/api/v1/projects", headers=viewer_headers)
        assert viewer_list.status_code == 200
        assert any(item["id"] == project_id for item in viewer_list.json())

        history = client.get("/api/v1/history", headers=viewer_headers)
        assert history.status_code == 200
        assert any(item["id"] == project_id for item in history.json())

        updated = client.patch(
            f"/api/v1/projects/{project_id}",
            headers=headers,
            json={
                "description": "Aktualisiert",
                "role_results": {
                    "score": 82,
                    "erweiterte_scores": {"netzdienlichkeit": 70, "stakeholder_fit": 64},
                },
            },
        )
        assert updated.status_code == 200
        assert updated.json()["description"] == "Aktualisiert"
        assert updated.json()["role_results"]["score"] == 82

        upload = client.post(
            f"/api/v1/projects/{project_id}/files",
            headers=headers,
            files={"file": ("plan.txt", io.BytesIO(b"netzplan"), "text/plain")},
        )
        assert upload.status_code == 200, upload.text
        assert upload.json()["file_name"] == "plan.txt"

        deleted = client.delete(f"/api/v1/projects/{project_id}", headers=headers)
        assert deleted.status_code == 200
        forbidden_after_delete = client.get(f"/api/v1/projects/{project_id}", headers=viewer_headers)
        assert forbidden_after_delete.status_code == 404
    finally:
        _close_client(client)


def test_project_viewer_receives_server_side_redacted_fields():
    client = build_client()
    try:
        owner_tokens = _register_and_login(client, "owner-redacted@example.com")
        viewer = client.post(
            "/api/v1/auth/register",
            json={"email": "viewer-redacted@example.com", "password": "Passwort123!", "role": "endkunde"},
        )
        assert viewer.status_code == 200, viewer.text
        viewer_id = viewer.json()["id"]
        owner_headers = {"Authorization": f"Bearer {owner_tokens['access_token']}"}

        created = client.post(
            "/api/v1/projects",
            headers=owner_headers,
            json={
                "name": "Investor Scope",
                "plz": "10115",
                "typ": "pv",
                "leistung_kw": 1200,
                "role_inputs": _rich_project_inputs(),
            },
        )
        assert created.status_code == 200, created.text
        project_id = created.json()["id"]

        updated = client.patch(
            f"/api/v1/projects/{project_id}",
            headers=owner_headers,
            json={"role_results": _rich_analysis_result()},
        )
        assert updated.status_code == 200, updated.text

        shared = client.post(
            f"/api/v1/projects/{project_id}/share",
            headers=owner_headers,
            json={"target_user_id": viewer_id, "project_role": "viewer"},
        )
        assert shared.status_code == 200, shared.text

        viewer_login = client.post(
            "/api/v1/auth/login",
            json={"email": "viewer-redacted@example.com", "password": "Passwort123!"},
        )
        assert viewer_login.status_code == 200, viewer_login.text
        viewer_headers = {"Authorization": f"Bearer {viewer_login.json()['access_token']}"}

        fetched = client.get(f"/api/v1/projects/{project_id}", headers=viewer_headers)
        assert fetched.status_code == 200, fetched.text
        body = fetched.json()

        assert body["owner_user_id"] is None
        assert "antragsteller" not in body["role_inputs"]
        assert "project_location" not in body["role_inputs"]
        assert "umspannwerk" not in body["role_inputs"]
        assert body["role_results"]["kosten_indikation_eur"] == 1_500_000
        assert body["role_results"]["route_environment"]["risk_level"] == "hoch"
        assert "kurzschluss" not in body["role_results"]
        assert "n1_analyse" not in body["role_results"]
        assert "history" not in body["role_results"]
    finally:
        _close_client(client)


def test_project_viewer_cannot_access_project_audit():
    client = build_client()
    try:
        owner_tokens = _register_and_login(client, "owner-audit@example.com")
        viewer = client.post(
            "/api/v1/auth/register",
            json={"email": "viewer-audit@example.com", "password": "Passwort123!", "role": "endkunde"},
        )
        assert viewer.status_code == 200, viewer.text
        owner_headers = {"Authorization": f"Bearer {owner_tokens['access_token']}"}

        created = client.post(
            "/api/v1/projects",
            headers=owner_headers,
            json={
                "name": "Audit Scope",
                "plz": "10115",
                "typ": "pv",
                "leistung_kw": 900,
                "role_inputs": _rich_project_inputs(customer_type="projektierer"),
            },
        )
        assert created.status_code == 200, created.text
        project_id = created.json()["id"]

        shared = client.post(
            f"/api/v1/projects/{project_id}/share",
            headers=owner_headers,
            json={"target_user_id": viewer.json()['id'], "project_role": "viewer"},
        )
        assert shared.status_code == 200, shared.text

        viewer_login = client.post(
            "/api/v1/auth/login",
            json={"email": "viewer-audit@example.com", "password": "Passwort123!"},
        )
        viewer_headers = {"Authorization": f"Bearer {viewer_login.json()['access_token']}"}

        forbidden = client.get(f"/api/v1/audit/{project_id}", headers=viewer_headers)
        assert forbidden.status_code == 403, forbidden.text
        assert forbidden.json()["detail"]["code"] == "AUDIT_FORBIDDEN"

        allowed = client.get(f"/api/v1/audit/{project_id}", headers=owner_headers)
        assert allowed.status_code == 200, allowed.text
        detail = json.loads(allowed.json()[0]["detail"])
        assert detail["action"] == "PROJECT_CREATED"
    finally:
        _close_client(client)


def test_project_viewer_cannot_create_project_bound_analysis_runs():
    client = build_client()
    try:
        owner_email = "owner-analysis-guard@example.com"
        owner_tokens = _register_and_login(client, owner_email)
        viewer = client.post(
            "/api/v1/auth/register",
            json={"email": "viewer-analysis-guard@example.com", "password": "Passwort123!", "role": "endkunde"},
        )
        assert viewer.status_code == 200, viewer.text
        owner_headers = {"Authorization": f"Bearer {owner_tokens['access_token']}"}

        created = client.post(
            "/api/v1/projects",
            headers=owner_headers,
            json={
                "name": "Guarded Analysis Project",
                "plz": "10115",
                "typ": "pv",
                "leistung_kw": 1200,
                "role_inputs": _rich_project_inputs(customer_type="projektierer"),
            },
        )
        assert created.status_code == 200, created.text
        project_id = created.json()["id"]

        shared = client.post(
            f"/api/v1/projects/{project_id}/share",
            headers=owner_headers,
            json={"target_user_id": viewer.json()["id"], "project_role": "viewer"},
        )
        assert shared.status_code == 200, shared.text

        viewer_login = client.post(
            "/api/v1/auth/login",
            json={"email": "viewer-analysis-guard@example.com", "password": "Passwort123!"},
        )
        assert viewer_login.status_code == 200, viewer_login.text
        viewer_headers = {"Authorization": f"Bearer {viewer_login.json()['access_token']}"}

        denied = client.post(
            "/api/v1/analyze",
            headers=viewer_headers,
            json={
                "project_id": project_id,
                "nennspannung": 20,
                "leistung_mw": 1.2,
                "leitungstyp": "NA2XS2Y240",
                "entfernung_km": 4.2,
                "anschlussart": "Einspeisung",
                "plz": "10115",
                "anlagentyp": "PV",
            },
        )
        assert denied.status_code == 403, denied.text
        assert denied.json()["detail"]["code"] == "PROJECT_WRITE_FORBIDDEN"

        with _db_session(client) as db:
            count = db.query(AnalysisRun).filter(AnalysisRun.project_id == project_id).count()
            assert count == 0
    finally:
        _close_client(client)


def test_project_viewer_cannot_export_project_bound_reports_from_existing_run():
    client = build_client()
    try:
        owner_email = "owner-report-guard@example.com"
        owner_tokens = _register_and_login(client, owner_email)
        viewer = client.post(
            "/api/v1/auth/register",
            json={"email": "viewer-report-guard@example.com", "password": "Passwort123!", "role": "endkunde"},
        )
        assert viewer.status_code == 200, viewer.text
        owner_headers = {"Authorization": f"Bearer {owner_tokens['access_token']}"}

        created = client.post(
            "/api/v1/projects",
            headers=owner_headers,
            json={
                "name": "Guarded Report Project",
                "plz": "10115",
                "typ": "pv",
                "leistung_kw": 1200,
                "role_inputs": _rich_project_inputs(customer_type="netzbetreiber"),
            },
        )
        assert created.status_code == 200, created.text
        project_id = created.json()["id"]

        shared = client.post(
            f"/api/v1/projects/{project_id}/share",
            headers=owner_headers,
            json={"target_user_id": viewer.json()["id"], "project_role": "viewer"},
        )
        assert shared.status_code == 200, shared.text

        run_id = _persist_project_analysis_run(client, owner_email=owner_email, project_id=project_id)

        viewer_login = client.post(
            "/api/v1/auth/login",
            json={"email": "viewer-report-guard@example.com", "password": "Passwort123!"},
        )
        assert viewer_login.status_code == 200, viewer_login.text
        viewer_headers = {"Authorization": f"Bearer {viewer_login.json()['access_token']}"}

        denied = client.post(
            "/api/v2/reports/vnb",
            headers=viewer_headers,
            json={"analysis_run_id": run_id},
        )
        assert denied.status_code == 403, denied.text
        assert denied.json()["detail"]["code"] == "PROJECT_WRITE_FORBIDDEN"

        with _db_session(client) as db:
            assert db.query(ReportRevisionRecord).count() == 0
    finally:
        _close_client(client)


def test_project_bound_report_requires_matching_stakeholder_path():
    client = build_client()
    try:
        owner_email = "owner-stakeholder-guard@example.com"
        owner_tokens = _register_and_login(client, owner_email)
        owner_headers = {"Authorization": f"Bearer {owner_tokens['access_token']}"}

        created = client.post(
            "/api/v1/projects",
            headers=owner_headers,
            json={
                "name": "Investor Stakeholder Project",
                "plz": "10115",
                "typ": "pv",
                "leistung_kw": 1200,
                "role_inputs": _rich_project_inputs(customer_type="investor"),
            },
        )
        assert created.status_code == 200, created.text
        project_id = created.json()["id"]
        run_id = _persist_project_analysis_run(client, owner_email=owner_email, project_id=project_id)

        denied = client.post(
            "/api/v2/reports/vnb",
            headers=owner_headers,
            json={"analysis_run_id": run_id},
        )
        assert denied.status_code == 403, denied.text
        assert denied.json()["detail"]["code"] == "REPORT_STAKEHOLDER_FORBIDDEN"

        with _db_session(client) as db:
            assert db.query(ReportRevisionRecord).count() == 0
    finally:
        _close_client(client)


def test_analyze_v2_investor_path_is_sanitized_server_side(monkeypatch):
    client = build_client()
    try:
        tokens = _register_and_login(client, "investor-analyze@example.com")
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}

        from api import analyze_v2 as analyze_v2_api

        monkeypatch.setattr(analyze_v2_api, "run_v1_analysis", lambda payload: _rich_analysis_result())

        response = client.post(
            "/api/v1/analyze",
            headers=headers,
            json={
                "nennspannung": 20,
                "leistung_mw": 1.2,
                "leitungstyp": "NA2XS2Y240",
                "entfernung_km": 4.2,
                "anschlussart": "Einspeisung",
                "plz": "10115",
                "anlagentyp": "PV",
                "stakeholder_context": {"customer_type": "investor", "priority_focus": "kosten"},
            },
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["kosten_indikation_eur"] == 1_500_000
        assert body["route_environment"]["risk_level"] == "hoch"
        assert "kurzschluss" not in body
        assert "n1_analyse" not in body
        assert body["billing_access"]["package_scope"] in {"basic", "premium", "professional"}
    finally:
        _close_client(client)


def test_user_settings_and_contact(monkeypatch):
    client = build_client()
    try:
        tokens = _register_and_login(client, "settings@example.com")
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}

        update_me = client.patch("/api/v1/users/me", headers=headers, json={"full_name": "Max Mustermann"})
        assert update_me.status_code == 200
        assert update_me.json()["full_name"] == "Max Mustermann"

        change_pw = client.patch(
            "/api/v1/users/me/password",
            headers=headers,
            json={"current_password": "Passwort123!", "new_password": "NeuPasswort123!"},
        )
        assert change_pw.status_code == 200

        from api import contact as contact_api

        monkeypatch.setattr(contact_api, "send_contact_mail", lambda **kwargs: None)
        payload = {
            "name": "Tester",
            "email": "tester@example.com",
            "subject": "Frage",
            "message": "Bitte um Rueckmeldung zur Netzkapazitaet.",
        }
        contact = client.post("/api/v1/contact", json=payload)
        assert contact.status_code == 200
        for _ in range(5):
            client.post("/api/v1/contact", json=payload)
        limited = client.post("/api/v1/contact", json=payload)
        assert limited.status_code == 429
        assert limited.json()["detail"]["code"] == "RATE_LIMITED"
    finally:
        _close_client(client)


def test_cookie_auth_requires_csrf_for_mutations():
    client = build_client()
    try:
        _register_and_login(client, "csrf@example.com")

        no_csrf = client.patch("/api/v1/users/me", json={"full_name": "CSRF Test"})
        assert no_csrf.status_code == 403
        assert no_csrf.json()["detail"]["code"] == "CSRF_INVALID"

        csrf_token = client.cookies.get("gridcheck_csrf")
        assert csrf_token
        with_csrf = client.patch(
            "/api/v1/users/me",
            headers={"X-CSRF-Token": csrf_token},
            json={"full_name": "CSRF Test"},
        )
        assert with_csrf.status_code == 200
        assert with_csrf.json()["full_name"] == "CSRF Test"

        no_csrf_project = client.post(
            "/api/v1/projects",
            json={"name": "No CSRF", "plz": "10115", "typ": "pv", "leistung_kw": 1000},
        )
        assert no_csrf_project.status_code == 403
        assert no_csrf_project.json()["detail"]["code"] == "CSRF_INVALID"
    finally:
        _close_client(client)


def test_freemium_paywall_and_billing_catalog(monkeypatch):
    client = build_client()
    try:
        tokens = _register_and_login(client, "billing@example.com")
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}

        from api import analyze_v2 as analyze_v2_api

        fake_result = {
            "scores": {"gesamt": 78},
            "fazit": {"entscheidung": "B"},
            "warnungen": [],
            "empfehlungen": ["Weiter abstimmen"],
            "revision": {"hash": "a" * 64},
        }
        monkeypatch.setattr(analyze_v2_api, "run_v1_analysis", lambda payload: fake_result)

        payload = {
            "nennspannung": 20,
            "leistung_mw": 2.5,
            "leitungstyp": "NA2XS2Y240",
            "entfernung_km": 4,
            "anschlussart": "Einspeisung",
            "plz": "10115",
            "anlagentyp": "PV",
        }

        for _ in range(3):
            response = client.post("/api/v1/analyze", headers=headers, json=payload)
            assert response.status_code == 200, response.text
            assert response.json()["billing"]["free_checks_remaining"] >= 0

        paywalled = client.post("/api/v1/analyze", headers=headers, json=payload)
        assert paywalled.status_code == 402, paywalled.text
        assert paywalled.json()["detail"]["code"] == "FREE_TIER_LIMIT"
        assert paywalled.json()["detail"]["billing"]["upgrade_required"] is True
        assert "pro_lizenz" in paywalled.json()["detail"]["billing"]["recommended_offer_ids"]

        billing_status = client.get("/api/v1/billing/status", headers=headers)
        assert billing_status.status_code == 200, billing_status.text
        body = billing_status.json()
        assert body["free_checks_used"] == 3
        assert body["upgrade_required"] is True
        offer_names = [offer["name"] for offer in body["catalog"]["offers"]]
        assert "Basic Schnellcheck" in offer_names
        assert "Premium Pre-Check" in offer_names
        assert "Professional Anschlussstrategie" in offer_names
        assert "Pro Lizenz" in offer_names
        assert "VNB Pilot" in offer_names
        addon_names = [offer["name"] for offer in body["catalog"]["addons"]]
        assert "Express" in addon_names
    finally:
        _close_client(client)


def test_analyze_v2_is_rate_limited(monkeypatch):
    client = build_client()
    try:
        _reset_rate_limit_state()
        tokens = _register_and_login(client, "analyze-rate-limit@example.com")
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}

        from api import analyze_v2 as analyze_v2_api

        monkeypatch.setattr(analyze_v2_api, "ensure_analysis_allowed", lambda db, user: None)
        monkeypatch.setattr(
            analyze_v2_api,
            "package_access_context",
            lambda db, user, requested_offer_id=None: {
                "offer_id": "manual",
                "package_scope": "professional",
                "usage_bucket": "paid",
                "report_scope": "professional",
                "ops_followup_required": False,
            },
        )
        monkeypatch.setattr(analyze_v2_api, "enforce_package_rights", lambda payload, access: payload)
        monkeypatch.setattr(
            analyze_v2_api,
            "run_v1_analysis",
            lambda payload: {
                "status": "OK",
                "scores": {"gesamt": 81},
                "fazit": {"entscheidung": "A"},
                "warnungen": [],
                "empfehlungen": ["Weiter abstimmen"],
                "revision": {"hash": "a" * 64},
            },
        )
        monkeypatch.setattr(
            analyze_v2_api,
            "persist_completed_analysis_run",
            lambda *args, **kwargs: type("Run", (), {"id": 1})(),
        )
        monkeypatch.setattr(
            analyze_v2_api,
            "build_billing_overview",
            lambda *args, **kwargs: {"free_checks_remaining": 99},
        )

        payload = {
            "nennspannung": 20,
            "leistung_mw": 2.5,
            "leitungstyp": "NA2XS2Y240",
            "entfernung_km": 4,
            "anschlussart": "Einspeisung",
            "plz": "10115",
            "anlagentyp": "PV",
        }

        for _ in range(12):
            response = client.post("/api/v1/analyze", headers=headers, json=payload)
            assert response.status_code == 200, response.text

        limited = client.post("/api/v1/analyze", headers=headers, json=payload)
        assert limited.status_code == 429, limited.text
        detail = limited.json()["detail"]
        assert detail["code"] == "RATE_LIMITED"
        assert detail["message"] == "Zu viele Analyse-Anfragen"
    finally:
        _close_client(client)


def test_analyze_v2_accepts_planner_n1_context():
    client = build_client()
    try:
        _reset_rate_limit_state()
        tokens = _register_and_login(client, "planner-n1@example.com")
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        payload = {
            "nennspannung": 20.0,
            "leistung_mw": 5.0,
            "leitungstyp": "NA2XS2Y240",
            "entfernung_km": 5.0,
            "anschlussart": "Einspeisung",
            "parallele_systeme": 2,
            "topologie": "ring",
            "restkapazitaet_ms_mva": 10.0,
            "n1_datengrundlage": "dso_verified",
            "umspannwerk": {
                "datenquelle": "dso_verified",
                "trafos": [
                    {"label": "T1", "sn_mva": 40.0, "belastung_aktuell_mw": 10.0},
                    {"label": "T2", "sn_mva": 40.0, "belastung_aktuell_mw": 10.0},
                ],
                "abgaenge": [
                    {"label": "A1", "primary": True, "i_max_a": 630.0, "belastung_aktuell_a": 520.0, "datenquelle": "dso_verified"},
                    {"label": "A2", "i_max_a": 630.0, "belastung_aktuell_a": 250.0, "datenquelle": "dso_verified"},
                ],
            },
        }

        response = client.post("/api/v1/analyze", headers=headers, json=payload)
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["status"] == "OK"
        assert body["n1"]["n1_klasse"] == "N1-4"
        assert body["n1"]["dso_daten_vorhanden"] is True
        assert "Abgangsreserve / Betriebsmittelpfad" in body["n1"]["nachweise_vorhanden"]
    finally:
        _close_client(client)


def test_forgot_password_always_returns_ok():
    client = build_client()
    try:
        known = client.post("/api/v1/auth/forgot-password", json={"email": "billing@example.com"})
        unknown = client.post("/api/v1/auth/forgot-password", json={"email": "does-not-exist@example.com"})
        assert known.status_code == 200, known.text
        assert unknown.status_code == 200, unknown.text
        assert known.json()["status"] == "ok"
        assert unknown.json()["status"] == "ok"
    finally:
        _close_client(client)


