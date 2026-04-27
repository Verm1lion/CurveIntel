"""API integration coverage for CurveIntel web routes."""

from __future__ import annotations

from datetime import datetime, timezone
import importlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from src.curveintel.auth.security import reset_auth_state
from src.curveintel.db.database import reset_database_state
from src.curveintel.db.enums import AuditAction, UserRole
from src.curveintel.db.models import AuditLog, User
from src.curveintel.web.settings import reset_web_settings
from tests.support import build_analysis_context, login, persist_analysis_result, run_migrations


@pytest.fixture()
def api_database_url(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    """Configure an isolated database for API integration tests."""

    database_url = f"sqlite:///{tmp_path / 'curveintel_api.db'}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("CURVEINTEL_ENV", "development")
    monkeypatch.setenv("CURVEINTEL_LOAD_DEMO_DATA", "false")
    monkeypatch.setenv("JWT_SECRET_KEY", "test-api-secret")
    monkeypatch.setenv("AUTH_COOKIE_SECURE", "false")
    monkeypatch.setenv(
        "CORS_ALLOW_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:5173",
    )
    reset_database_state()
    reset_auth_state()
    reset_web_settings()
    run_migrations(database_url)
    yield database_url
    reset_database_state()
    reset_auth_state()
    reset_web_settings()


@pytest.fixture()
def api_client(api_database_url: str) -> TestClient:
    """Create a TestClient backed by an isolated API database."""

    import web.app as web_app

    importlib.reload(web_app)
    with TestClient(web_app.app) as client:
        yield client


def test_public_routes_and_health_redirects(api_client: TestClient) -> None:
    """Public pages should remain reachable while the dashboard redirects to login."""

    health = api_client.get("/api/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    dashboard = api_client.get("/", follow_redirects=False)
    assert dashboard.status_code == 303
    assert dashboard.headers["location"] == "/login"

    login_page = api_client.get("/login")
    assert login_page.status_code == 200
    assert "CurveIntel" in login_page.text

    guide_page = api_client.get("/guide")
    assert guide_page.status_code == 200


def test_admin_analysis_api_flow(
    api_client: TestClient,
    api_database_url: str,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Admin users should analyze, list, read, audit, and delete persisted results."""

    api_client.post(
        "/api/auth/register",
        json={
            "email": "admin@example.com",
            "full_name": "Bootstrap Admin",
            "password": "Bootstrap123A",
        },
    )
    login(api_client, "admin@example.com", "Bootstrap123A")

    import web.app as web_app

    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    monkeypatch.setattr(web_app, "UPLOAD_DIR", upload_dir)

    class FakePipeline:
        def __init__(self, filename: str) -> None:
            self.ctx = build_analysis_context(filename, 792.0)

        def run(self, _):
            return self.ctx

    monkeypatch.setattr(web_app, "build_pipeline", lambda csv_path: FakePipeline(csv_path.name))

    analyze_response = api_client.post(
        "/api/analyze",
        files={"file": ("integration.csv", b"strain,stress\n0,0\n0.01,100\n", "text/csv")},
    )
    assert analyze_response.status_code == 200, analyze_response.text
    analyze_payload = analyze_response.json()
    assert analyze_payload["status"] == "success"
    result_id = analyze_payload["data"]["id"]

    results_response = api_client.get("/api/results")
    assert results_response.status_code == 200
    assert [item["id"] for item in results_response.json()["results"]] == [result_id]

    single_result = api_client.get(f"/api/results/{result_id}")
    assert single_result.status_code == 200
    assert single_result.json()["filename"] == "integration.csv"

    audit_response = api_client.get(
        "/api/audit-logs",
        params={"entity_type": "analysis_result", "entity_id": result_id},
    )
    assert audit_response.status_code == 200, audit_response.text
    audit_payload = audit_response.json()
    assert audit_payload["count"] >= 1
    assert all(item["entity_id"] == result_id for item in audit_payload["items"])

    delete_response = api_client.delete(f"/api/results/{result_id}")
    assert delete_response.status_code == 200
    assert delete_response.json()["status"] == "deleted"

    missing_response = api_client.get(f"/api/results/{result_id}")
    assert missing_response.status_code == 404
    missing_payload = missing_response.json()
    assert missing_payload["status"] == "error"
    assert missing_payload["error"]["code"] == "not_found"
    assert missing_payload["error"]["message"] == "Analysis result not found."

    engine = create_engine(api_database_url, future=True)
    with Session(engine) as session:
        audit_actions = [
            event.action.value
            for event in session.scalars(select(AuditLog).order_by(AuditLog.occurred_at)).all()
        ]
    engine.dispose()

    assert AuditAction.CREATE.value in audit_actions
    assert AuditAction.DELETE.value in audit_actions


def test_role_boundaries_and_audit_validation(
    api_client: TestClient,
    api_database_url: str,
) -> None:
    """Analysts/viewers should remain read-only while audit validation stays standardized."""

    api_client.post(
        "/api/auth/register",
        json={
            "email": "admin@example.com",
            "full_name": "Bootstrap Admin",
            "password": "Bootstrap123A",
        },
    )
    login(api_client, "admin@example.com", "Bootstrap123A")

    analyst_response = api_client.post(
        "/api/auth/register",
        json={
            "email": "analyst@example.com",
            "full_name": "Analyst User",
            "password": "Analyst123Ax",
            "role": UserRole.ANALYST.value,
        },
    )
    viewer_response = api_client.post(
        "/api/auth/register",
        json={
            "email": "viewer@example.com",
            "full_name": "Viewer User",
            "password": "Viewer123Axy",
            "role": UserRole.VIEWER.value,
        },
    )
    assert analyst_response.status_code == 201, analyst_response.text
    assert viewer_response.status_code == 201, viewer_response.text

    engine = create_engine(api_database_url, future=True)
    with Session(engine) as session:
        admin = session.scalar(select(User).where(User.email == "admin@example.com"))
        assert admin is not None
        persisted = persist_analysis_result(
            session,
            filename="role-boundary.csv",
            uts_mpa=801.0,
            created_by_user_id=admin.id,
            created_at=datetime(2026, 4, 1, tzinfo=timezone.utc),
        )
    engine.dispose()

    invalid_filter = api_client.get("/api/audit-logs", params={"entity_id": str(persisted.id)})
    assert invalid_filter.status_code == 422
    invalid_filter_payload = invalid_filter.json()
    assert invalid_filter_payload["status"] == "error"
    assert (
        invalid_filter_payload["error"]["message"]
        == "entity_type is required when entity_id is provided."
    )

    api_client.post("/api/auth/logout")
    login(api_client, "analyst@example.com", "Analyst123Ax")

    analyst_list = api_client.get("/api/results")
    assert analyst_list.status_code == 200
    assert analyst_list.json()["results"][0]["id"] == str(persisted.id)

    analyst_get = api_client.get(f"/api/results/{persisted.id}")
    assert analyst_get.status_code == 200

    analyst_delete = api_client.delete(f"/api/results/{persisted.id}")
    assert analyst_delete.status_code == 403
    assert analyst_delete.json()["error"]["code"] == "forbidden"

    analyst_audit = api_client.get("/api/audit-logs")
    assert analyst_audit.status_code == 403
    assert analyst_audit.json()["error"]["code"] == "forbidden"

    api_client.post("/api/auth/logout")
    login(api_client, "viewer@example.com", "Viewer123Axy")

    viewer_list = api_client.get("/api/results")
    assert viewer_list.status_code == 200
    assert viewer_list.json()["results"][0]["id"] == str(persisted.id)

    viewer_clear = api_client.delete("/api/results/clear")
    assert viewer_clear.status_code == 403
    assert viewer_clear.json()["error"]["code"] == "forbidden"


def test_admin_user_management_and_role_aware_dashboard(api_client: TestClient) -> None:
    """Admins should manage users while dashboards remain role-aware."""

    register_admin = api_client.post(
        "/api/auth/register",
        json={
            "email": "admin@example.com",
            "full_name": "Bootstrap Admin",
            "password": "Bootstrap123A",
        },
    )
    assert register_admin.status_code == 201, register_admin.text
    login(api_client, "admin@example.com", "Bootstrap123A")

    analyst_response = api_client.post(
        "/api/auth/register",
        json={
            "email": "analyst@example.com",
            "full_name": "Analyst User",
            "password": "Analyst123Ax",
            "role": UserRole.ANALYST.value,
        },
    )
    viewer_response = api_client.post(
        "/api/auth/register",
        json={
            "email": "viewer@example.com",
            "full_name": "Viewer User",
            "password": "Viewer123Axy",
            "role": UserRole.VIEWER.value,
        },
    )
    assert analyst_response.status_code == 201, analyst_response.text
    assert viewer_response.status_code == 201, viewer_response.text

    users_response = api_client.get("/api/users")
    assert users_response.status_code == 200, users_response.text
    users_payload = users_response.json()
    assert users_payload["count"] == 3
    users_by_email = {item["email"]: item for item in users_payload["users"]}
    analyst_id = users_by_email["analyst@example.com"]["id"]

    update_response = api_client.patch(
        f"/api/users/{analyst_id}",
        json={"role": UserRole.VIEWER.value, "is_active": False},
    )
    assert update_response.status_code == 200, update_response.text
    updated_payload = update_response.json()
    assert updated_payload["status"] == "success"
    assert updated_payload["user"]["role"] == UserRole.VIEWER.value
    assert updated_payload["user"]["is_active"] is False

    filtered_audit = api_client.get(
        "/api/audit-logs",
        params={
            "action": "update",
            "status": "success",
            "entity_type": "user",
            "entity_id": analyst_id,
        },
    )
    assert filtered_audit.status_code == 200, filtered_audit.text
    filtered_payload = filtered_audit.json()
    assert filtered_payload["count"] == 1
    assert filtered_payload["items"][0]["action"] == "update"
    assert filtered_payload["items"][0]["entity_type"] == "user"
    assert filtered_payload["items"][0]["entity_id"] == analyst_id

    admin_dashboard = api_client.get("/")
    assert admin_dashboard.status_code == 200
    assert "Admin Control Plane" in admin_dashboard.text
    assert "User Access Control" in admin_dashboard.text
    assert "Add New User" in admin_dashboard.text
    assert "addUserForm" in admin_dashboard.text
    assert "Audit Trail" in admin_dashboard.text

    api_client.post("/api/auth/logout")
    login(api_client, "viewer@example.com", "Viewer123Axy")
    viewer_dashboard = api_client.get("/")
    assert viewer_dashboard.status_code == 200
    assert "Read-only Workspace" in viewer_dashboard.text
    assert "User Access Control" not in viewer_dashboard.text
    assert "Add New User" not in viewer_dashboard.text
    assert "addUserForm" not in viewer_dashboard.text


def test_last_admin_guard_and_filtered_audit_queries(api_client: TestClient) -> None:
    """The last active admin should be protected and audit filters should remain composable."""

    register_admin = api_client.post(
        "/api/auth/register",
        json={
            "email": "admin@example.com",
            "full_name": "Bootstrap Admin",
            "password": "Bootstrap123A",
        },
    )
    assert register_admin.status_code == 201, register_admin.text
    login(api_client, "admin@example.com", "Bootstrap123A")

    analyst_response = api_client.post(
        "/api/auth/register",
        json={
            "email": "analyst@example.com",
            "full_name": "Analyst User",
            "password": "Analyst123Ax",
            "role": UserRole.ANALYST.value,
        },
    )
    assert analyst_response.status_code == 201, analyst_response.text

    users_response = api_client.get("/api/users")
    users_payload = users_response.json()
    users_by_email = {item["email"]: item for item in users_payload["users"]}
    admin_id = users_by_email["admin@example.com"]["id"]
    analyst_id = users_by_email["analyst@example.com"]["id"]

    demote_admin = api_client.patch(
        f"/api/users/{admin_id}",
        json={"role": UserRole.VIEWER.value},
    )
    assert demote_admin.status_code == 409
    demote_payload = demote_admin.json()
    assert demote_payload["status"] == "error"
    assert demote_payload["error"]["code"] == "conflict"
    assert (
        demote_payload["error"]["message"] == "At least one active admin must remain in the system."
    )

    update_analyst = api_client.patch(
        f"/api/users/{analyst_id}",
        json={"role": UserRole.VIEWER.value},
    )
    assert update_analyst.status_code == 200, update_analyst.text

    filtered_audit = api_client.get(
        "/api/audit-logs",
        params={
            "action": "update",
            "entity_type": "user",
            "entity_id": analyst_id,
            "actor_user_id": admin_id,
        },
    )
    assert filtered_audit.status_code == 200, filtered_audit.text
    filtered_payload = filtered_audit.json()
    assert filtered_payload["count"] == 1
    assert filtered_payload["items"][0]["actor_user_id"] == admin_id
    assert filtered_payload["items"][0]["entity_id"] == analyst_id
