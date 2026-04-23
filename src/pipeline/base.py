"""
CurveIntel pipeline base classes.

AnalysisContext carries state through the full pipeline.
PipelineStep defines the abstract processing contract.
StepResult captures each step outcome.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from src.models.enums import (
    AnomalyType,
    MaterialType,
    StepStatus,
    StressStrainType,
    YieldBehavior,
)


@dataclass
class AnomalyRecord:
    """Single detected anomaly entry."""

    anomaly_type: AnomalyType
    confidence: float  # Confidence score in the range 0.0-1.0
    description: str  # Human-readable description
    strain_location: float | None = None  # Strain coordinate where it occurs
    severity: str = "warning"  # "info", "warning", "critical"


@dataclass
class MechanicalProperties:
    """Calculated mechanical properties."""

    elastic_modulus_gpa: float | None = None  # E (GPa)
    yield_strength_mpa: float | None = None  # Rp0.2 or ReH (MPa)
    yield_lower_mpa: float | None = None  # ReL for discontinuous yielding (MPa)
    ultimate_tensile_mpa: float | None = None  # UTS / Rm (MPa)
    elongation_at_break_pct: float | None = None  # Total elongation (%)
    uniform_elongation_pct: float | None = None  # Elongation up to necking (%)
    strain_hardening_n: float | None = None  # Hollomon n value
    strength_coefficient_k: float | None = None  # Hollomon K value (MPa)
    toughness_mj_m3: float | None = None  # Area under the curve (MJ/m^3)
    yield_behavior: YieldBehavior = YieldBehavior.UNDEFINED
    method_tags: dict[str, str] = field(default_factory=dict)
    # ISO 17025 Cl. 7.8.2.1 traceability: keep the standards reference per property.
    # Example: {"yield": "per ISO 6892-1:2019 Cl. 13.1", "uts": "per ISO 6892-1:2019 Cl. 3.10.1"}


@dataclass
class SpecimenMetadata:
    """Specimen and test metadata."""

    specimen_id: str = ""
    material_type: MaterialType = MaterialType.UNKNOWN
    cross_section_area_mm2: float | None = None  # A0 (mm^2)
    gauge_length_mm: float | None = None  # L0 (mm)
    width_mm: float | None = None  # Width (mm)
    thickness_mm: float | None = None  # Thickness (mm)
    test_speed_mm_min: float | None = None  # Crosshead speed (mm/min)
    temperature_c: float | None = None  # Temperature (degC)
    source_file: str = ""
    test_standard: str = ""  # Example: "ISO 6892-1", "ASTM E8"


@dataclass
class AnalysisContext:
    """
    Central data object shared across the full pipeline.

    Each PipelineStep receives this object, mutates it, and returns a StepResult.
    Shared state across modules lives in one explicit container.
    """

    # Raw input data
    raw_df: pd.DataFrame = field(default_factory=pd.DataFrame)

    # Processed engineering data
    stress: np.ndarray = field(default_factory=lambda: np.array([]))
    strain: np.ndarray = field(default_factory=lambda: np.array([]))
    stress_type: StressStrainType = StressStrainType.ENGINEERING

    # Optional true stress-strain representation
    true_stress: np.ndarray = field(default_factory=lambda: np.array([]))
    true_strain: np.ndarray = field(default_factory=lambda: np.array([]))

    # Metadata
    metadata: SpecimenMetadata = field(default_factory=SpecimenMetadata)

    # Computed outputs
    properties: MechanicalProperties = field(default_factory=MechanicalProperties)
    anomalies: list[AnomalyRecord] = field(default_factory=list)

    # Per-step execution log
    step_results: list[StepResult] = field(default_factory=list)

    # Shared scratch space between modules
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def has_data(self) -> bool:
        """Return whether stress/strain arrays are populated."""
        return len(self.stress) > 0 and len(self.strain) > 0

    @property
    def n_points(self) -> int:
        """Return the number of stress-strain points."""
        return len(self.stress)

    def add_anomaly(
        self,
        anomaly_type: AnomalyType,
        confidence: float,
        description: str,
        strain_location: float | None = None,
        severity: str = "warning",
    ) -> None:
        """Append an anomaly record to the context."""
        self.anomalies.append(
            AnomalyRecord(
                anomaly_type=anomaly_type,
                confidence=confidence,
                description=description,
                strain_location=strain_location,
                severity=severity,
            )
        )


@dataclass
class StepResult:
    """Execution result for one pipeline step."""

    step_name: str
    status: StepStatus
    message: str = ""
    duration_ms: float = 0.0


class PipelineStep(ABC):
    """
    Base class for all pipeline modules.

    Each module:
    1. Defines `name`
    2. Implements `process(context)`
    3. Returns a `StepResult`
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Step name used in logs and reports."""
        ...

    @abstractmethod
    def process(self, ctx: AnalysisContext) -> StepResult:
        """
        Run the primary step logic.

        Args:
            ctx: Pipeline context object used for reads and writes.

        Returns:
            StepResult: Outcome of the step (`success`, `warning`, `failure`).
        """
        ...

    def _success(self, msg: str = "") -> StepResult:
        return StepResult(step_name=self.name, status=StepStatus.SUCCESS, message=msg)

    def _warning(self, msg: str) -> StepResult:
        return StepResult(step_name=self.name, status=StepStatus.WARNING, message=msg)

    def _failure(self, msg: str) -> StepResult:
        return StepResult(step_name=self.name, status=StepStatus.FAILURE, message=msg)


class Pipeline:
    """
    Sequential pipeline runner.

    Executes steps in order, stops on failure, and continues through warnings.
    """

    def __init__(self, steps: list[PipelineStep] | None = None):
        self.steps: list[PipelineStep] = steps or []

    def add_step(self, step: PipelineStep) -> "Pipeline":
        self.steps.append(step)
        return self

    def run(self, ctx: AnalysisContext) -> AnalysisContext:
        """Run all steps in order."""
        import time

        for step in self.steps:
            t0 = time.perf_counter()
            try:
                result = step.process(ctx)
            except Exception as e:
                result = StepResult(
                    step_name=step.name,
                    status=StepStatus.FAILURE,
                    message=f"Beklenmeyen hata: {e}",
                )

            result.duration_ms = (time.perf_counter() - t0) * 1000
            ctx.step_results.append(result)

            if result.status == StepStatus.FAILURE:
                # Stop the pipeline on a hard failure.
                break

        return ctx
