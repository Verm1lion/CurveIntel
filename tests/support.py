"""Shared test helpers for CurveIntel integration suites."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from uuid import UUID

import numpy as np
import pandas as pd
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.curveintel.db.repository import AnalysisResultRepository
from src.curveintel.db.serializers import build_analysis_snapshot_from_context
from src.models.enums import MaterialType, StepStatus, YieldBehavior
from src.pipeline.base import AnalysisContext, MechanicalProperties, SpecimenMetadata, StepResult


ROOT_DIR = Path(__file__).resolve().parent.parent


def run_migrations(database_url: str) -> None:
    """Upgrade the target database to the latest revision."""

    config = Config(str(ROOT_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT_DIR / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "head")


def login(client: TestClient, email: str, password: str) -> dict:
    """Authenticate a user and return the response payload."""

    response = client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return response.json()


def build_analysis_context(filename: str, uts_mpa: float) -> AnalysisContext:
    """Create a deterministic synthetic analysis context for persistence tests."""

    strain = np.linspace(0.0, 0.24, 240)
    rising = np.linspace(0.0, uts_mpa, 180)
    softening = np.linspace(uts_mpa, uts_mpa * 0.82, 60)
    stress = np.concatenate([rising, softening])
    yield_strength = round(uts_mpa * 0.72, 1)
    uts_idx = int(np.argmax(stress))
    necking_idx = min(len(strain) - 1, uts_idx + 12)

    ctx = AnalysisContext()
    ctx.raw_df = pd.DataFrame({"strain": strain[:25], "stress": stress[:25]})
    ctx.strain = strain
    ctx.stress = stress
    ctx.metadata = SpecimenMetadata(
        specimen_id=filename.removesuffix(".csv"),
        material_type=MaterialType.STEEL_DP,
        source_file=filename,
        test_standard="ISO 6892-1:2019",
    )
    ctx.properties = MechanicalProperties(
        elastic_modulus_gpa=210.0,
        yield_strength_mpa=yield_strength,
        ultimate_tensile_mpa=uts_mpa,
        elongation_at_break_pct=18.4,
        uniform_elongation_pct=12.1,
        strain_hardening_n=0.19,
        strength_coefficient_k=1015.0,
        toughness_mj_m3=132.4,
        yield_behavior=YieldBehavior.CONTINUOUS,
        method_tags={"yield": "ISO 6892-1:2019 Cl. 13.1"},
    )
    ctx.step_results = [
        StepResult(step_name="DataLoader", status=StepStatus.SUCCESS, duration_ms=1.2),
        StepResult(step_name="YieldDetector", status=StepStatus.SUCCESS, duration_ms=1.4),
        StepResult(step_name="UTSDetector", status=StepStatus.SUCCESS, duration_ms=1.1),
    ]
    ctx.extra = {
        "vendor_name": "Instron",
        "vendor_confidence": 96,
        "detected_encoding": "utf-8",
        "detected_separator": ",",
        "strain_rate_range": "Method A1",
        "strain_rate_code": "A1",
        "strain_rate_median": 0.00025,
        "strain_rate_compliant": True,
        "yield_strain": 0.012,
        "uts_idx": uts_idx,
        "necking_idx": necking_idx,
        "snr_db": 43.7,
        "noise_pct": 0.8,
    }
    return ctx


def persist_analysis_result(
    session: Session,
    *,
    filename: str,
    uts_mpa: float,
    created_by_user_id: UUID,
    created_at: datetime,
):
    """Persist a synthetic analysis result with a controlled timestamp."""

    snapshot = build_analysis_snapshot_from_context(
        build_analysis_context(filename, uts_mpa),
        filename,
        created_by_user_id=created_by_user_id,
    ).model_copy(update={"created_at": created_at})
    return AnalysisResultRepository(session).create_from_snapshot(snapshot)
