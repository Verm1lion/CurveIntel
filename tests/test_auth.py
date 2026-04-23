"""Auth and RBAC integration tests for CurveIntel."""

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
from src.curveintel.db.enums import AuditAction, AuditStatus, UserRole
from src.curveintel.db.models import AuditLog, User
from src.curveintel.db.repository import AnalysisResultRepository
from src.curveintel.web.settings import get_web_settings, reset_web_settings
from tests.support import login, persist_analysis_result, run_migrations


@pytest.fixture()
def auth_database_url(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    """Configure an isolated auth test database."""

    database_url = f"sqlite:///{tmp_path / 'curveintel_auth.db'}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("CURVEINTEL_ENV", "development")
    monkeypatch.setenv("CURVEINTEL_LOAD_DEMO_DATA", "false")
    monkeypatch.setenv("JWT_SECRET_KEY", "test-jwt-secret")
    monkeypatch.setenv("AUTH_COOKIE_SECURE", "false")
    monkeypatch.delenv("AUTH_BOOTSTRAP_ADMIN_PASSWORD", raising=False)
    reset_database_state()
    reset_auth_state()
    reset_web_settings()
    run_migrations(database_url)
    yield database_url
    reset_database_state()
    reset_auth_state()
    reset_web_settings()


@pytest.fixture()
def auth_client(auth_database_url: str) -> TestClient:
    """Create a TestClient backed by an isolated auth database."""

    import web.app as web_app

    importlib.reload(web_app)
    with TestClient(web_app.app) as client:
        yield client


def test_bootstrap_register_and_login_flow(auth_client: TestClient, auth_database_url: str) -> None:
    """The first registration should create an admin and allow sign-in."""

    login_page = auth_client.get("/login")
    assert login_page.status_code == 200
    assert "Bootstrap first admin" in login_page.text

    register_response = auth_client.post(
        "/api/auth/register",
        json={
            "email": "admin@example.com",
            "full_name": "Bootstrap Admin",
            "password": "Bootstrap123A",
        },
    )
    assert register_response.status_code == 201, register_response.text
    registered_user = register_response.json()
    assert registered_user["role"] == UserRole.ADMIN.value

    login_payload = login(auth_client, "admin@example.com", "Bootstrap123A")
    assert login_payload["user"]["email"] == "admin@example.com"
    assert "curveintel_access_token" in auth_client.cookies

    me_response = auth_client.get("/api/auth/me")
    assert me_response.status_code == 200
    assert me_response.json()["role"] == UserRole.ADMIN.value

    engine = create_engine(auth_database_url, future=True)
    with Session(engine) as session:
        audit_events = session.scalars(select(AuditLog).order_by(AuditLog.occurred_at)).all()
        actions = {(event.action.value, event.status.value) for event in audit_events}
    engine.dispose()

    assert (AuditAction.REGISTER.value, AuditStatus.SUCCESS.value) in actions
    assert (AuditAction.LOGIN.value, AuditStatus.SUCCESS.value) in actions


def test_api_errors_use_standardized_payloads(auth_client: TestClient) -> None:
    """HTTP and validation errors should share the same API error envelope."""

    invalid_login = auth_client.post(
        "/api/auth/login",
        json={"email": "ghost@example.com", "password": "WrongPassword1"},
    )
    assert invalid_login.status_code == 401
    invalid_login_payload = invalid_login.json()
    assert invalid_login_payload["status"] == "error"
    assert invalid_login_payload["error"]["code"] == "unauthorized"
    assert invalid_login_payload["error"]["message"] == "Invalid email or password."
    assert invalid_login_payload["error"]["path"] == "/api/auth/login"

    invalid_register = auth_client.post(
        "/api/auth/register",
        json={
            "email": "not-an-email",
            "full_name": "",
            "password": "short",
        },
    )
    assert invalid_register.status_code == 422
    invalid_register_payload = invalid_register.json()
    assert invalid_register_payload["status"] == "error"
    assert invalid_register_payload["error"]["code"] == "validation_error"
    assert invalid_register_payload["error"]["message"] == "Request validation failed."
    assert isinstance(invalid_register_payload["error"]["details"], list)


def test_admin_can_register_roles_and_viewer_cannot_analyze(
    auth_client: TestClient,
    auth_database_url: str,
) -> None:
    """Admins should create users, while viewers remain blocked from analysis endpoints."""

    auth_client.post(
        "/api/auth/register",
        json={
            "email": "admin@example.com",
            "full_name": "Bootstrap Admin",
            "password": "Bootstrap123A",
        },
    )
    login(auth_client, "admin@example.com", "Bootstrap123A")

    analyst_response = auth_client.post(
        "/api/auth/register",
        json={
            "email": "analyst@example.com",
            "full_name": "Analyst User",
            "password": "Analyst123Ax",
            "role": UserRole.ANALYST.value,
        },
    )
    viewer_response = auth_client.post(
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

    auth_client.post("/api/auth/logout")
    login(auth_client, "viewer@example.com", "Viewer123Axy")
    viewer_attempt = auth_client.post("/api/analyze")
    assert viewer_attempt.status_code == 403

    auth_client.post("/api/auth/logout")
    login(auth_client, "analyst@example.com", "Analyst123Ax")
    analyst_attempt = auth_client.post("/api/analyze")
    assert analyst_attempt.status_code == 422

    engine = create_engine(auth_database_url, future=True)
    with Session(engine) as session:
        users = session.scalars(select(User).order_by(User.email)).all()
    engine.dispose()

    assert [user.role.value for user in users] == ["admin", "analyst", "viewer"]


def test_default_admin_seed_allows_login(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Configured bootstrap admin credentials should seed a default admin on startup."""

    database_url = f"sqlite:///{tmp_path / 'curveintel_seed.db'}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("CURVEINTEL_ENV", "development")
    monkeypatch.setenv("CURVEINTEL_LOAD_DEMO_DATA", "false")
    monkeypatch.setenv("JWT_SECRET_KEY", "seed-test-secret")
    monkeypatch.setenv("AUTH_BOOTSTRAP_ADMIN_EMAIL", "seed.admin@example.com")
    monkeypatch.setenv("AUTH_BOOTSTRAP_ADMIN_FULL_NAME", "Seeded Admin")
    monkeypatch.setenv("AUTH_BOOTSTRAP_ADMIN_PASSWORD", "SeededAdmin123")
    reset_database_state()
    reset_auth_state()
    run_migrations(database_url)

    import web.app as web_app

    importlib.reload(web_app)
    with TestClient(web_app.app) as client:
        login_response = client.post(
            "/api/auth/login",
            json={"email": "seed.admin@example.com", "password": "SeededAdmin123"},
        )
        assert login_response.status_code == 200, login_response.text
        assert login_response.json()["user"]["role"] == UserRole.ADMIN.value

    engine = create_engine(database_url, future=True)
    with Session(engine) as session:
        users = session.scalars(select(User)).all()
        audit_events = session.scalars(select(AuditLog).order_by(AuditLog.occurred_at)).all()
    engine.dispose()
    reset_database_state()
    reset_auth_state()

    assert len(users) == 1
    assert users[0].email == "seed.admin@example.com"
    assert any(event.action == AuditAction.SEED for event in audit_events)


def test_dashboard_uses_requested_result_id(
    auth_client: TestClient,
    auth_database_url: str,
) -> None:
    """Dashboard selection should honor the requested persisted result ID."""

    auth_client.post(
        "/api/auth/register",
        json={
            "email": "admin@example.com",
            "full_name": "Bootstrap Admin",
            "password": "Bootstrap123A",
        },
    )
    login(auth_client, "admin@example.com", "Bootstrap123A")

    engine = create_engine(auth_database_url, future=True)
    with Session(engine) as session:
        admin = session.scalar(select(User).where(User.email == "admin@example.com"))
        assert admin is not None
        selected_result = persist_analysis_result(
            session,
            filename="selected.csv",
            uts_mpa=812.0,
            created_by_user_id=admin.id,
            created_at=datetime(2026, 1, 10, tzinfo=timezone.utc),
        )
        persist_analysis_result(
            session,
            filename="latest.csv",
            uts_mpa=845.0,
            created_by_user_id=admin.id,
            created_at=datetime(2026, 1, 11, tzinfo=timezone.utc),
        )
    engine.dispose()

    response = auth_client.get(f"/?id={selected_result.id}")
    assert response.status_code == 200
    assert response.context["current"]["id"] == str(selected_result.id)
    assert response.context["selected_result_id"] == str(selected_result.id)


def test_admin_can_read_audit_logs_and_viewer_cannot(
    auth_client: TestClient,
) -> None:
    """Audit trail should be admin-only."""

    auth_client.post(
        "/api/auth/register",
        json={
            "email": "admin@example.com",
            "full_name": "Bootstrap Admin",
            "password": "Bootstrap123A",
        },
    )
    login(auth_client, "admin@example.com", "Bootstrap123A")

    viewer_response = auth_client.post(
        "/api/auth/register",
        json={
            "email": "viewer@example.com",
            "full_name": "Viewer User",
            "password": "Viewer123Axy",
            "role": UserRole.VIEWER.value,
        },
    )
    assert viewer_response.status_code == 201, viewer_response.text

    admin_audit = auth_client.get("/api/audit-logs")
    assert admin_audit.status_code == 200, admin_audit.text
    audit_payload = admin_audit.json()
    assert audit_payload["count"] >= 2
    assert any(item["action"] == AuditAction.LOGIN.value for item in audit_payload["items"])

    auth_client.post("/api/auth/logout")
    login(auth_client, "viewer@example.com", "Viewer123Axy")
    viewer_audit = auth_client.get("/api/audit-logs")
    assert viewer_audit.status_code == 403


def test_clear_results_soft_deletes_persisted_records(
    auth_client: TestClient,
    auth_database_url: str,
) -> None:
    """Clear-all should operate on persisted DB rows, not only in-memory cache state."""

    auth_client.post(
        "/api/auth/register",
        json={
            "email": "admin@example.com",
            "full_name": "Bootstrap Admin",
            "password": "Bootstrap123A",
        },
    )
    login(auth_client, "admin@example.com", "Bootstrap123A")

    engine = create_engine(auth_database_url, future=True)
    with Session(engine) as session:
        admin = session.scalar(select(User).where(User.email == "admin@example.com"))
        assert admin is not None
        persist_analysis_result(
            session,
            filename="first.csv",
            uts_mpa=780.0,
            created_by_user_id=admin.id,
            created_at=datetime(2026, 2, 1, tzinfo=timezone.utc),
        )
        persist_analysis_result(
            session,
            filename="second.csv",
            uts_mpa=805.0,
            created_by_user_id=admin.id,
            created_at=datetime(2026, 2, 2, tzinfo=timezone.utc),
        )
    engine.dispose()

    clear_response = auth_client.delete("/api/results/clear")
    assert clear_response.status_code == 200, clear_response.text
    assert clear_response.json()["deleted_count"] == 2

    engine = create_engine(auth_database_url, future=True)
    with Session(engine) as session:
        repo = AnalysisResultRepository(session)
        active_results = repo.list_recent(limit=None)
        all_results = repo.list_recent(limit=None, include_deleted=True)
        delete_events = session.scalars(
            select(AuditLog).where(AuditLog.action == AuditAction.DELETE)
        ).all()
    engine.dispose()

    assert active_results == []
    assert len(all_results) == 2
    assert all(result.deleted_at is not None for result in all_results)
    assert len(delete_events) >= 2


def test_report_download_rehydrates_context_from_snapshot(
    auth_client: TestClient,
    auth_database_url: str,
) -> None:
    """PDF downloads should rebuild report context from persisted snapshots."""

    auth_client.post(
        "/api/auth/register",
        json={
            "email": "admin@example.com",
            "full_name": "Bootstrap Admin",
            "password": "Bootstrap123A",
        },
    )
    login(auth_client, "admin@example.com", "Bootstrap123A")

    engine = create_engine(auth_database_url, future=True)
    with Session(engine) as session:
        admin = session.scalar(select(User).where(User.email == "admin@example.com"))
        assert admin is not None
        persisted = persist_analysis_result(
            session,
            filename="reportable.csv",
            uts_mpa=798.0,
            created_by_user_id=admin.id,
            created_at=datetime(2026, 3, 1, tzinfo=timezone.utc),
        )
    engine.dispose()

    report_response = auth_client.get(f"/api/report/{persisted.id}/pdf")
    assert report_response.status_code == 200, report_response.text
    assert report_response.headers["content-type"].startswith("application/pdf")

    engine = create_engine(auth_database_url, future=True)
    with Session(engine) as session:
        latest_download_event = session.scalar(
            select(AuditLog)
            .where(AuditLog.action == AuditAction.DOWNLOAD)
            .order_by(AuditLog.occurred_at.desc())
        )
    engine.dispose()

    assert latest_download_event is not None
    assert latest_download_event.event_meta["report_source"] == "snapshot_rehydrated"


def test_cors_preflight_uses_configured_origin(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Configured browser origins should receive CORS preflight responses."""

    database_url = f"sqlite:///{tmp_path / 'curveintel_cors.db'}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("CURVEINTEL_ENV", "development")
    monkeypatch.setenv("CURVEINTEL_LOAD_DEMO_DATA", "false")
    monkeypatch.setenv("JWT_SECRET_KEY", "cors-test-secret")
    monkeypatch.setenv("CORS_ALLOW_ORIGINS", "http://localhost:3000,http://127.0.0.1:5173")
    monkeypatch.setenv("CORS_ALLOW_METHODS", "GET,POST,DELETE,OPTIONS")
    monkeypatch.setenv("CORS_ALLOW_HEADERS", "Authorization,Content-Type,X-Request-ID")
    monkeypatch.setenv("CORS_ALLOW_CREDENTIALS", "true")
    reset_database_state()
    reset_auth_state()
    reset_web_settings()
    run_migrations(database_url)

    import web.app as web_app

    importlib.reload(web_app)
    with TestClient(web_app.app) as client:
        response = client.options(
            "/api/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Authorization,Content-Type",
            },
        )
        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
        assert response.headers["access-control-allow-credentials"] == "true"

    reset_database_state()
    reset_auth_state()
    reset_web_settings()


def test_cors_rejects_wildcard_with_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    """Cookie auth should not permit wildcard CORS origins."""

    monkeypatch.setenv("CORS_ALLOW_ORIGINS", "*")
    monkeypatch.setenv("CORS_ALLOW_CREDENTIALS", "true")
    reset_web_settings()

    with pytest.raises(ValueError, match="CORS_ALLOW_ORIGINS"):
        get_web_settings()

    reset_web_settings()
