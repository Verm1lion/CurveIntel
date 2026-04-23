"""Database-layer tests for CurveIntel Phase 2.1."""

from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from src.curveintel.db.database import get_database_settings, get_engine, reset_database_state
from src.curveintel.db.enums import AuditAction, AuditEntityType, AuditStatus, UserRole
from src.curveintel.db.repository import (
    AnalysisResultRepository,
    AuditLogRepository,
    UserRepository,
)
from src.curveintel.db.schemas import AuditEventCreate, UserCreate
from src.curveintel.db.serializers import (
    build_analysis_context_from_payload,
    build_analysis_context_from_snapshot,
    build_analysis_snapshot_from_context,
    build_analysis_snapshot_from_payload,
)
from src.models.enums import AnomalyType, MaterialType, StepStatus, StressStrainType, YieldBehavior
from src.pipeline.base import AnalysisContext, StepResult


ROOT_DIR = Path(__file__).resolve().parent.parent


def run_migrations(database_url: str) -> None:
    """Upgrade the target database to the latest revision."""

    config = Config(str(ROOT_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT_DIR / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "head")


def build_sample_context() -> AnalysisContext:
    """Create a compact analysis context for DB tests."""

    ctx = AnalysisContext()
    ctx.metadata.source_file = "sample.csv"
    ctx.metadata.specimen_id = "SP-001"
    ctx.metadata.material_type = MaterialType.ALUMINUM
    ctx.metadata.test_standard = "ISO 6892-1:2019"
    ctx.stress_type = StressStrainType.ENGINEERING
    ctx.stress = np.array([0.0, 110.0, 205.0, 250.0], dtype=float)
    ctx.strain = np.array([0.0, 0.001, 0.003, 0.007], dtype=float)
    ctx.true_stress = np.array([0.0, 111.0, 208.0, 255.0], dtype=float)
    ctx.true_strain = np.array([0.0, 0.0011, 0.0031, 0.0073], dtype=float)
    ctx.properties.elastic_modulus_gpa = 69.5
    ctx.properties.yield_strength_mpa = 210.4
    ctx.properties.yield_lower_mpa = 205.7
    ctx.properties.ultimate_tensile_mpa = 252.9
    ctx.properties.elongation_at_break_pct = 18.6
    ctx.properties.uniform_elongation_pct = 14.2
    ctx.properties.strain_hardening_n = 0.19
    ctx.properties.strength_coefficient_k = 331.2
    ctx.properties.toughness_mj_m3 = 12.8
    ctx.properties.yield_behavior = YieldBehavior.CONTINUOUS
    ctx.properties.method_tags = {"yield": "ISO 6892-1:2019 Cl. 13.1"}
    ctx.extra.update(
        {
            "vendor_name": "NIST",
            "vendor_confidence": 98,
            "detected_encoding": "utf-8",
            "detected_separator": ",",
            "yield_strain": 0.0021,
            "uts_idx": 3,
            "necking_idx": 2,
            "strain_rate_range": "Method A",
            "strain_rate_code": "A1",
            "strain_rate_median": 0.00025,
            "strain_rate_compliant": True,
            "snr_db": 37.8,
            "noise_pct": 0.18,
            "elastic_r2": 0.9987,
            "elastic_sm_rel": 1.4,
            "elastic_n_points": 42,
            "elastic_iterations": 3,
        }
    )
    ctx.add_anomaly(
        AnomalyType.HIGH_NOISE,
        confidence=0.22,
        description="Minor acquisition noise detected.",
        strain_location=0.006,
        severity="warning",
    )
    ctx.step_results = [
        StepResult("DataLoader", StepStatus.SUCCESS, "Loaded CSV", 1.2),
        StepResult("ElasticModulusDetector", StepStatus.SUCCESS, "Elastic fit completed", 2.1),
    ]
    return ctx


@pytest.fixture()
def sqlite_session(tmp_path: Path) -> Session:
    """Provide a migrated SQLite session."""

    database_url = f"sqlite:///{tmp_path / 'curveintel.db'}"
    run_migrations(database_url)
    engine = create_engine(database_url, future=True)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    with session_factory() as session:
        yield session
    engine.dispose()


def test_sqlite_alembic_upgrade_creates_tables(tmp_path: Path) -> None:
    """SQLite migrations should create the Phase 2.1 tables."""

    database_url = f"sqlite:///{tmp_path / 'sqlite_migration.db'}"
    run_migrations(database_url)
    engine = create_engine(database_url, future=True)
    table_names = set(inspect(engine).get_table_names())
    engine.dispose()

    assert {"users", "analysis_results", "audit_logs"} <= table_names


def test_database_settings_use_environment_database_url(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """database.py should honor DATABASE_URL from the environment."""

    database_url = f"sqlite:///{tmp_path / 'settings.db'}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    reset_database_state()
    try:
        assert get_database_settings().database_url == database_url
        assert str(get_engine().url) == database_url
    finally:
        reset_database_state()


def test_user_repository_enforces_unique_email(sqlite_session: Session) -> None:
    """Users should enforce unique email addresses."""

    repo = UserRepository(sqlite_session)
    created = repo.create(
        UserCreate(
            email="qa@example.com",
            full_name="QA Engineer",
            password_hash="x" * 60,
            role=UserRole.ADMIN,
        )
    )

    assert created.email == "qa@example.com"
    assert repo.get_by_email("QA@example.com").id == created.id

    with pytest.raises(IntegrityError):
        repo.create(
            UserCreate(
                email="qa@example.com",
                full_name="Duplicate",
                password_hash="y" * 60,
            )
        )


def test_analysis_snapshot_roundtrip_and_soft_delete(
    sqlite_session: Session, tmp_path: Path
) -> None:
    """Analysis snapshots should persist, list, and soft-delete cleanly."""

    user_repo = UserRepository(sqlite_session)
    analysis_repo = AnalysisResultRepository(sqlite_session)
    created_user = user_repo.create(
        UserCreate(
            email="analyst@example.com",
            full_name="Analyst User",
            password_hash="z" * 60,
            role=UserRole.ANALYST,
        )
    )

    source_file = tmp_path / "sample.csv"
    source_file.write_text("strain,stress\n0,0\n0.001,110\n", encoding="utf-8")
    snapshot = build_analysis_snapshot_from_context(
        build_sample_context(),
        filename=source_file.name,
        source_file_path=source_file,
        created_by_user_id=created_user.id,
    )
    persisted = analysis_repo.create_from_snapshot(snapshot)

    assert persisted.source_filename == "sample.csv"
    assert persisted.created_by_user_id == created_user.id
    assert persisted.input_sha256 is not None
    assert len(persisted.input_sha256) == 64

    fetched = analysis_repo.get_by_id(persisted.id)
    assert fetched is not None
    assert fetched.analysis_payload["filename"] == "sample.csv"

    recent = analysis_repo.list_recent()
    assert [item.id for item in recent] == [persisted.id]

    by_user = analysis_repo.list_by_user(created_user.id)
    assert [item.id for item in by_user] == [persisted.id]

    deleted = analysis_repo.soft_delete(persisted.id, deleted_by_user_id=created_user.id)
    assert deleted is not None
    assert deleted.deleted_by_user_id == created_user.id
    assert analysis_repo.get_by_id(persisted.id) is None
    assert analysis_repo.get_by_id(persisted.id, include_deleted=True) is not None
    assert analysis_repo.list_recent() == []
    assert analysis_repo.list_recent(include_deleted=True)[0].id == persisted.id


def test_legacy_ctx_to_dict_payload_is_backward_compatible(tmp_path: Path) -> None:
    """The current ctx_to_dict payload shape should hydrate into AnalysisSnapshotCreate."""

    from web.app import ctx_to_dict

    ctx = build_sample_context()
    payload = ctx_to_dict(ctx, "legacy.csv")
    source_file = tmp_path / "legacy.csv"
    source_file.write_text("strain,stress\n0,0\n0.001,110\n", encoding="utf-8")

    snapshot = build_analysis_snapshot_from_payload(payload, source_file_path=source_file)
    hydrated = json.loads(snapshot.model_dump_json())

    assert snapshot.source_filename == "legacy.csv"
    assert snapshot.material_type == "aluminum"
    assert snapshot.quality_score == payload["quality"]["score"]
    assert hydrated["analysis_payload"]["filename"] == "legacy.csv"


def test_persisted_context_snapshot_can_rehydrate_analysis_context(tmp_path: Path) -> None:
    """Persisted snapshots should reconstruct a usable AnalysisContext for reports."""

    source_file = tmp_path / "rehydrate.csv"
    source_file.write_text("strain,stress\n0,0\n0.001,110\n", encoding="utf-8")
    original_ctx = build_sample_context()
    snapshot = build_analysis_snapshot_from_context(
        original_ctx,
        filename=source_file.name,
        source_file_path=source_file,
    )

    restored_from_snapshot = build_analysis_context_from_snapshot(snapshot.context_snapshot)
    restored_from_payload = build_analysis_context_from_payload(snapshot.analysis_payload)

    assert restored_from_snapshot.metadata.source_file == "sample.csv"
    assert restored_from_snapshot.metadata.material_type == MaterialType.ALUMINUM
    assert restored_from_snapshot.properties.ultimate_tensile_mpa == pytest.approx(252.9)
    assert restored_from_snapshot.properties.yield_behavior == YieldBehavior.CONTINUOUS
    assert restored_from_snapshot.extra["snr_db"] == pytest.approx(37.8)
    assert len(restored_from_snapshot.anomalies) == 1
    assert restored_from_snapshot.anomalies[0].anomaly_type == AnomalyType.HIGH_NOISE
    assert len(restored_from_snapshot.step_results) == 2
    np.testing.assert_allclose(restored_from_snapshot.stress, original_ctx.stress)
    np.testing.assert_allclose(restored_from_snapshot.strain, original_ctx.strain)

    assert restored_from_payload.metadata.source_file == "rehydrate.csv"
    assert restored_from_payload.properties.ultimate_tensile_mpa == pytest.approx(252.9)
    assert restored_from_payload.extra["yield_strain"] == pytest.approx(0.0021)
    assert restored_from_payload.step_results[0].status == StepStatus.SUCCESS


def test_audit_log_repository_is_append_only(sqlite_session: Session) -> None:
    """Audit events should append and remain queryable."""

    user_repo = UserRepository(sqlite_session)
    audit_repo = AuditLogRepository(sqlite_session)
    created_user = user_repo.create(
        UserCreate(
            email="auditor@example.com",
            full_name="Audit User",
            password_hash="a" * 60,
        )
    )

    before_snapshot = {"deleted_at": None}
    after_snapshot = {"deleted_at": "2026-04-22T12:00:00+00:00"}
    created_event = audit_repo.append(
        AuditEventCreate(
            actor_user_id=created_user.id,
            action=AuditAction.DELETE,
            entity_type=AuditEntityType.ANALYSIS_RESULT,
            entity_id="analysis-123",
            request_id="req-001",
            ip_address="127.0.0.1",
            user_agent="pytest",
            status=AuditStatus.SUCCESS,
            before_snapshot=before_snapshot,
            after_snapshot=after_snapshot,
            event_meta={"reason": "soft_delete"},
        )
    )

    assert created_event.before_snapshot == before_snapshot
    assert created_event.after_snapshot == after_snapshot
    assert not hasattr(audit_repo, "update")
    assert not hasattr(audit_repo, "delete")

    events = audit_repo.list_for_entity(AuditEntityType.ANALYSIS_RESULT, "analysis-123")
    assert [event.id for event in events] == [created_event.id]


@pytest.mark.skipif(
    not os.getenv("TEST_POSTGRES_DSN"),
    reason="Set TEST_POSTGRES_DSN to run PostgreSQL migration parity tests.",
)
def test_postgres_migration_parity() -> None:
    """The same Alembic revision should apply to PostgreSQL."""

    database_url = os.environ["TEST_POSTGRES_DSN"]
    run_migrations(database_url)
    engine = create_engine(database_url, future=True)
    table_names = set(inspect(engine).get_table_names())
    engine.dispose()

    assert {"users", "analysis_results", "audit_logs"} <= table_names
