"""
CurveIntel pipeline base classes.

AnalysisContext: Tüm pipeline boyunca taşınan veri ve sonuç nesnesi.
PipelineStep: Her modülün implement etmesi gereken abstract base class.
StepResult: Her adımın döndürdüğü sonuç.
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
    """Tespit edilen tek bir anomali kaydı."""
    anomaly_type: AnomalyType
    confidence: float                    # 0.0 — 1.0 arası güven skoru
    description: str                     # İnsan-okunabilir açıklama
    strain_location: float | None = None # Anomalinin gerçekleştiği strain değeri
    severity: str = "warning"            # "info", "warning", "critical"


@dataclass
class MechanicalProperties:
    """Hesaplanan mekanik özellikler."""
    elastic_modulus_gpa: float | None = None       # E (GPa)
    yield_strength_mpa: float | None = None        # Rp0.2 veya ReH (MPa)
    yield_lower_mpa: float | None = None           # ReL — sadece çift akma (MPa)
    ultimate_tensile_mpa: float | None = None       # UTS / Rm (MPa)
    elongation_at_break_pct: float | None = None    # % uzama
    uniform_elongation_pct: float | None = None     # Necking başlangıcına kadar % uzama
    strain_hardening_n: float | None = None         # Hollomon n değeri
    strength_coefficient_k: float | None = None     # Hollomon K değeri (MPa)
    toughness_mj_m3: float | None = None            # Eğri altı alan (MJ/m³)
    yield_behavior: YieldBehavior = YieldBehavior.UNDEFINED
    method_tags: dict[str, str] = field(default_factory=dict)
    # ISO 17025 Cl. 7.8.2.1 izlenebilirlik: her hesabin ISO madde referansi
    # Ornek: {"yield": "per ISO 6892-1:2019 Cl. 13.1", "uts": "per ISO 6892-1:2019 Cl. 3.10.1"}


@dataclass
class SpecimenMetadata:
    """Numune ve test bilgileri."""
    specimen_id: str = ""
    material_type: MaterialType = MaterialType.UNKNOWN
    cross_section_area_mm2: float | None = None   # A₀ (mm²)
    gauge_length_mm: float | None = None          # L₀ (mm)
    width_mm: float | None = None                  # Genişlik (mm)
    thickness_mm: float | None = None              # Kalınlık (mm)
    test_speed_mm_min: float | None = None         # Test hızı (mm/min)
    temperature_c: float | None = None             # Sıcaklık (°C)
    source_file: str = ""
    test_standard: str = ""                        # Örn: "ISO 6892-1", "ASTM E8"


@dataclass
class AnalysisContext:
    """
    Pipeline boyunca taşınan merkezi veri nesnesi.

    Her PipelineStep bu nesneyi alır, üzerinde çalışır ve geri döndürür.
    Böylece modüller arası veri paylaşımı tek bir nesne üzerinden yapılır.
    """
    # ── Ham veri ──
    raw_df: pd.DataFrame = field(default_factory=pd.DataFrame)

    # ── İşlenmiş veri ──
    stress: np.ndarray = field(default_factory=lambda: np.array([]))
    strain: np.ndarray = field(default_factory=lambda: np.array([]))
    stress_type: StressStrainType = StressStrainType.ENGINEERING

    # ── Gerçek (true) stress-strain (opsiyonel) ──
    true_stress: np.ndarray = field(default_factory=lambda: np.array([]))
    true_strain: np.ndarray = field(default_factory=lambda: np.array([]))

    # ── Metadata ──
    metadata: SpecimenMetadata = field(default_factory=SpecimenMetadata)

    # ── Sonuçlar ──
    properties: MechanicalProperties = field(default_factory=MechanicalProperties)
    anomalies: list[AnomalyRecord] = field(default_factory=list)

    # ── Pipeline log ──
    step_results: list[StepResult] = field(default_factory=list)

    # ── Ek veri (modüller arası paylaşım) ──
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def has_data(self) -> bool:
        """Stress/strain verisi yüklü mü?"""
        return len(self.stress) > 0 and len(self.strain) > 0

    @property
    def n_points(self) -> int:
        """Veri noktası sayısı."""
        return len(self.stress)

    def add_anomaly(
        self,
        anomaly_type: AnomalyType,
        confidence: float,
        description: str,
        strain_location: float | None = None,
        severity: str = "warning",
    ) -> None:
        """Anomali kaydı ekle."""
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
    """Bir pipeline adımının sonucu."""
    step_name: str
    status: StepStatus
    message: str = ""
    duration_ms: float = 0.0


class PipelineStep(ABC):
    """
    Tüm pipeline modüllerinin base class'ı.

    Her modül:
    1. name property'sini tanımlar
    2. process(context) metodunu implement eder
    3. StepResult döndürür
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Adım adı (loglama ve raporlama için)."""
        ...

    @abstractmethod
    def process(self, ctx: AnalysisContext) -> StepResult:
        """
        Ana işlem metodu.

        Args:
            ctx: Pipeline context — veri bu nesne üzerinde okunur/yazılır.

        Returns:
            StepResult: Adımın sonucu (success/warning/failure).
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
    Sıralı pipeline çalıştırıcısı.

    Adımları sırasıyla çalıştırır. FAILURE durumunda durur,
    WARNING durumunda devam eder.
    """

    def __init__(self, steps: list[PipelineStep] | None = None):
        self.steps: list[PipelineStep] = steps or []

    def add_step(self, step: PipelineStep) -> "Pipeline":
        self.steps.append(step)
        return self

    def run(self, ctx: AnalysisContext) -> AnalysisContext:
        """Tüm adımları sırasıyla çalıştır."""
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
                # Kritik hata — pipeline durur
                break

        return ctx
