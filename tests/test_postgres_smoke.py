"""Optional PostgreSQL smoke test for the stabilized auth/audit baseline."""

from __future__ import annotations

import importlib
import os
from pathlib import Path
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, delete
from sqlalchemy.orm import Session

from src.curveintel.auth.security import reset_auth_state
from src.curveintel.db.database import reset_database_state
from src.curveintel.db.enums import AuditAction, UserRole
from src.curveintel.db.models import AnalysisResult, AuditLog, User
from src.curveintel.web.settings import reset_web_settings
from tests.support import build_analysis_context, login, run_migrations


POSTGRES_SMOKE_URL_ENV = "CURVEINTEL_TEST_DATABASE_URL"


@pytest.fixture()
def postgres_database_url(monkeypatch: pytest.MonkeyPatch) -> str:
    """Configure a live PostgreSQL database for the optional smoke flow."""

    database_url = os.getenv(POSTGRES_SMOKE_URL_ENV)
    if not database_url:
        pytest.skip(f"Set {POSTGRES_SMOKE_URL_ENV} to run the PostgreSQL smoke test.")

    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("CURVEINTEL_ENV", "development")
    monkeypatch.setenv("CURVEINTEL_LOAD_DEMO_DATA", "false")
    monkeypatch.setenv("JWT_SECRET_KEY", "postgres-smoke-secret")
    monkeypatch.setenv("AUTH_COOKIE_SECURE", "false")
    monkeypatch.delenv("AUTH_BOOTSTRAP_ADMIN_PASSWORD", raising=False)

    reset_database_state()
    reset_auth_state()
    reset_web_settings()
    run_migrations(database_url)

    engine = create_engine(database_url, future=True)
    with Session(engine) as session:
        session.execute(delete(AuditLog))
        session.execute(delete(AnalysisResult))
        session.execute(delete(User))
        session.commit()
    engine.dispose()

    yield database_url

    reset_database_state()
    reset_auth_state()
    reset_web_settings()


@pytest.fixture()
def postgres_client(postgres_database_url: str) -> TestClient:
    """Create a TestClient wired to the live PostgreSQL smoke database."""

    import web.app as web_app

    importlib.reload(web_app)
    with TestClient(web_app.app) as client:
        yield client


def test_postgres_smoke_flow(
    postgres_client: TestClient,
    postgres_database_url: str,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Exercise the primary auth, analyze, audit, download, and delete path on PostgreSQL."""

    login_page = postgres_client.get("/login")
    assert login_page.status_code == 200
    assert "Bootstrap first admin" in login_page.text

    register_admin = postgres_client.post(
        "/api/auth/register",
        json={
            "email": "admin@example.com",
            "full_name": "Bootstrap Admin",
            "password": "Bootstrap123A",
        },
    )
    assert register_admin.status_code == 201, register_admin.text
    login(postgres_client, "admin@example.com", "Bootstrap123A")

    analyst_response = postgres_client.post(
        "/api/auth/register",
        json={
            "email": "analyst@example.com",
            "full_name": "Analyst User",
            "password": "Analyst123Ax",
            "role": UserRole.ANALYST.value,
        },
    )
    viewer_response = postgres_client.post(
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

    import web.app as web_app

    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    monkeypatch.setattr(web_app, "UPLOAD_DIR", upload_dir)

    class FakePipeline:
        def __init__(self, filename: str) -> None:
            self.ctx = build_analysis_context(filename, 812.0)

        def run(self, _):
            return self.ctx

    monkeypatch.setattr(web_app, "build_pipeline", lambda csv_path: FakePipeline(csv_path.name))

    postgres_client.post("/api/auth/logout")
    login(postgres_client, "analyst@example.com", "Analyst123Ax")

    analyze_response = postgres_client.post(
        "/api/analyze",
        files={"file": ("postgres-smoke.csv", b"strain,stress\n0,0\n0.01,100\n", "text/csv")},
    )
    assert analyze_response.status_code == 200, analyze_response.text
    result_id = analyze_response.json()["data"]["id"]

    postgres_client.post("/api/auth/logout")
    login(postgres_client, "viewer@example.com", "Viewer123Axy")

    results_response = postgres_client.get("/api/results")
    assert results_response.status_code == 200, results_response.text
    assert results_response.json()["results"][0]["id"] == result_id

    report_response = postgres_client.get(f"/api/report/{result_id}/pdf")
    assert report_response.status_code == 200, report_response.text
    assert report_response.headers["content-type"] == "application/pdf"

    viewer_audit_response = postgres_client.get("/api/audit-logs")
    assert viewer_audit_response.status_code == 403

    postgres_client.post("/api/auth/logout")
    login(postgres_client, "admin@example.com", "Bootstrap123A")

    audit_response = postgres_client.get(
        "/api/audit-logs",
        params={"entity_type": "analysis_result", "entity_id": result_id},
    )
    assert audit_response.status_code == 200, audit_response.text
    assert audit_response.json()["count"] >= 1

    delete_response = postgres_client.delete(f"/api/results/{result_id}")
    assert delete_response.status_code == 200, delete_response.text

    parsed_result_id = UUID(result_id)
    engine = create_engine(postgres_database_url, future=True)
    with Session(engine) as session:
        actions = [
            event.action.value
            for event in session.query(AuditLog).order_by(AuditLog.occurred_at.asc()).all()
        ]
        deleted_result = session.get(AnalysisResult, parsed_result_id)
        users = session.query(User).order_by(User.email.asc()).all()
    engine.dispose()

    assert len(users) == 3
    assert AuditAction.REGISTER.value in actions
    assert AuditAction.LOGIN.value in actions
    assert AuditAction.CREATE.value in actions
    assert AuditAction.DOWNLOAD.value in actions
    assert AuditAction.DELETE.value in actions
    assert deleted_result is not None
    assert deleted_result.deleted_at is not None
