"""Tests for repository-bundled example data."""

from __future__ import annotations

from pathlib import Path

import pytest

from batch_analyze import build_pipeline
from src.pipeline.base import AnalysisContext


FULL_NIST_EXAMPLE = Path("examples") / "C00Al6xxxT4Numisheet2020R01T1.521W17.91-S-Stress-Strain.csv"


def test_full_nist_example_pipeline_produces_analysis_data() -> None:
    """The public NIST example should be a real analysis input, not metadata only."""

    assert FULL_NIST_EXAMPLE.exists()

    ctx = build_pipeline(FULL_NIST_EXAMPLE).run(AnalysisContext())

    assert ctx.has_data
    assert ctx.n_points == 2000
    assert ctx.properties.ultimate_tensile_mpa == pytest.approx(316.48, rel=0.02)
    assert ctx.properties.yield_strength_mpa == pytest.approx(307.03, rel=0.02)
