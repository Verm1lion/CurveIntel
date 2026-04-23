"""Deterministic unit tests for the tensile-analysis pipeline steps."""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.models.enums import AnomalyType, MaterialType, StepStatus, StressStrainType, YieldBehavior
from src.pipeline.anomaly import (
    CurveIntegrityChecker,
    GripSlippageDetector,
    NoiseAnalyzer,
    PropertyValidator,
    SensorSaturationDetector,
)
from src.pipeline.base import AnalysisContext
from src.pipeline.extraction import (
    ElasticModulusDetector,
    ElongationDetector,
    NeckingDetector,
    StrainHardeningFitter,
    StrainRateValidator,
    ToughnessCalculator,
    UTSDetector,
    YieldDetector,
)
from src.pipeline.ingestion import (
    DataLoader,
    SchemaDetector,
    UnitConverter,
    _detect_separator,
    _parse_dimensions_from_filename,
)
from src.pipeline.preprocessing import (
    MonotonicityChecker,
    Resampler,
    SavitzkyGolayFilter,
    SpikeFilter,
    ToeCompensation,
)
from src.pipeline.vendor_profiles import detect_decimal_separator


def _build_monotonic_engineering_context() -> AnalysisContext:
    strain = np.linspace(0.0, 0.05, 1000)
    stress = np.empty_like(strain)
    elastic_slope = 210_000.0

    for index, strain_value in enumerate(strain):
        if strain_value <= 0.002:
            stress[index] = elastic_slope * strain_value
        else:
            stress[index] = 420.0 + 350.0 * (1.0 - np.exp(-(strain_value - 0.002) * 30.0))

    return AnalysisContext(stress=stress, strain=strain)


def _build_discontinuous_yield_context() -> AnalysisContext:
    strain = np.linspace(0.0, 0.03, 600)
    stress = np.empty_like(strain)

    for index, strain_value in enumerate(strain):
        if strain_value <= 0.0018:
            stress[index] = 200_000.0 * strain_value
        elif strain_value <= 0.0024:
            fraction = (strain_value - 0.0018) / (0.0024 - 0.0018)
            stress[index] = 360.0 - fraction * 30.0
        elif strain_value <= 0.008:
            stress[index] = 330.0 + 5.0 * np.sin((strain_value - 0.0024) * 50.0)
        else:
            stress[index] = 335.0 + (strain_value - 0.008) * 12_000.0

    return AnalysisContext(stress=stress, strain=strain)


def _build_post_uts_true_context() -> AnalysisContext:
    strain = np.linspace(0.0, 0.35, 1200)
    stress = np.empty_like(strain)
    elastic_slope = 210_000.0
    strength_coefficient = 1100.0
    hardening_exponent = 0.15

    for index, strain_value in enumerate(strain):
        if strain_value <= 0.002:
            stress[index] = elastic_slope * strain_value
        elif strain_value <= 0.22:
            stress[index] = strength_coefficient * (strain_value**hardening_exponent)
        else:
            peak_stress = strength_coefficient * (0.22**hardening_exponent)
            stress[index] = peak_stress - (strain_value - 0.22) * 3000.0

    stress = np.maximum(stress, 0.0)
    stress[-30:] = np.linspace(stress[-30], 0.0, 30)

    ctx = AnalysisContext(
        stress=stress,
        strain=strain,
        stress_type=StressStrainType.TRUE,
    )
    ctx.properties.elastic_modulus_gpa = 210.0
    ctx.extra["yield_strain"] = 0.01
    ctx.extra["time_array"] = np.linspace(0.0, 175.0, len(strain))
    return ctx


def test_ingestion_engineering_csv_detects_vendor_and_converts_percent_strain(
    tmp_path: Path,
) -> None:
    csv_path = tmp_path / "instron_export.csv"
    pd.DataFrame(
        {
            "Tensile strain (Extension)": np.linspace(0.0, 20.0, 20),
            "Tensile stress (MPa)": np.linspace(0.0, 400.0, 20),
            "Time": np.linspace(0.0, 19.0, 20),
        }
    ).to_csv(csv_path, index=False)

    ctx = AnalysisContext()
    load_result = DataLoader(csv_path).process(ctx)
    schema_result = SchemaDetector().process(ctx)
    convert_result = UnitConverter().process(ctx)

    assert load_result.status == StepStatus.SUCCESS
    assert schema_result.status == StepStatus.SUCCESS
    assert convert_result.status == StepStatus.SUCCESS
    assert ctx.extra["vendor_profile"] == "Instron Bluehill"
    assert ctx.extra["vendor_encoding"] == "utf-8-sig"
    assert ctx.stress_type == StressStrainType.ENGINEERING
    assert ctx.extra["detected_columns"]["time"] == "Time"
    assert len(ctx.extra["time_array"]) == 20
    assert ctx.stress.max() == pytest.approx(400.0)
    assert ctx.strain.max() == pytest.approx(0.20)


def test_ingestion_force_displacement_parses_dimensions_and_converts_kn(
    tmp_path: Path,
) -> None:
    csv_path = tmp_path / "FeDP980_T1.50W12.00_force.csv"
    pd.DataFrame(
        {
            "Load (kN)": np.linspace(0.0, 15.0, 30),
            "Extension": np.linspace(0.0, 6.0, 30),
        }
    ).to_csv(csv_path, index=False)

    ctx = AnalysisContext()
    load_result = DataLoader(csv_path).process(ctx)
    schema_result = SchemaDetector().process(ctx)
    convert_result = UnitConverter().process(ctx)

    assert load_result.status == StepStatus.SUCCESS
    assert schema_result.status == StepStatus.WARNING
    assert convert_result.status == StepStatus.SUCCESS
    assert _parse_dimensions_from_filename(csv_path.name) == (1.5, 12.0)
    assert ctx.metadata.cross_section_area_mm2 == pytest.approx(18.0)
    assert ctx.metadata.gauge_length_mm == pytest.approx(50.0)
    assert ctx.metadata.material_type == MaterialType.STEEL_DP
    assert ctx.stress_type == StressStrainType.ENGINEERING
    assert ctx.stress[1] == pytest.approx(28.73563218)
    assert ctx.strain[1] == pytest.approx(0.00413793)


def test_ingestion_helpers_detect_locale_separator_and_decimal(tmp_path: Path) -> None:
    csv_path = tmp_path / "devotrans_locale.csv"
    csv_path.write_text(
        "Kuvvet;Uzama\n1,0;0,5\n2,5;1,0\n",
        encoding="utf-8",
    )

    sample_lines = csv_path.read_text(encoding="utf-8").splitlines()

    assert _detect_separator(csv_path) == ";"
    assert detect_decimal_separator(sample_lines[1:], separator=";") == ","


def test_preprocessing_steps_clean_shift_and_resample_data() -> None:
    strain = np.linspace(0.0, 0.1, 100)
    stress = np.linspace(0.0, 500.0, 100)
    stress[40] = 1000.0
    ctx = AnalysisContext(stress=stress.copy(), strain=strain.copy())

    spike_result = SpikeFilter(window_size=5, threshold_sigma=2.5).process(ctx)

    assert spike_result.status == StepStatus.WARNING
    assert ctx.stress[40] < 300.0
    assert ctx.anomalies[0].anomaly_type == AnomalyType.SPIKE

    toe_strain = np.linspace(0.001, 0.02, 300)
    toe_stress = 210_000.0 * (toe_strain - 0.001) + np.linspace(0.0, 5.0, 300)
    toe_ctx = AnalysisContext(stress=toe_stress, strain=toe_strain)
    toe_result = ToeCompensation().process(toe_ctx)

    assert toe_result.status == StepStatus.SUCCESS
    assert toe_ctx.strain[0] == pytest.approx(0.0, abs=1e-12)
    assert toe_ctx.extra["toe_elastic_slope"] == pytest.approx(210_263.15789473685)

    resample_ctx = AnalysisContext(
        stress=np.array(
            [
                0.0,
                50.0,
                100.0,
                150.0,
                200.0,
                190.0,
                210.0,
                250.0,
                300.0,
                305.0,
                350.0,
                400.0,
                450.0,
                500.0,
            ]
        ),
        strain=np.array(
            [
                0.0,
                0.005,
                0.01,
                0.015,
                0.02,
                0.019,
                0.021,
                0.025,
                0.03,
                0.03,
                0.035,
                0.04,
                0.045,
                0.05,
            ]
        ),
    )
    resample_result = Resampler(n_points=20, method="pchip").process(resample_ctx)

    assert resample_result.status == StepStatus.SUCCESS
    assert len(resample_ctx.strain) == 20
    assert np.all(np.diff(resample_ctx.strain) > 0)

    filter_ctx = AnalysisContext(
        stress=np.sin(np.linspace(0.0, 1.0, 101) * 6.0) + np.linspace(0.0, 1.0, 101) * 10.0,
        strain=np.linspace(0.0, 1.0, 101),
    )
    filter_result = SavitzkyGolayFilter(window_length=9, polyorder=3).process(filter_ctx)

    assert filter_result.status == StepStatus.SUCCESS
    assert "pre_sg_stress" in filter_ctx.extra
    assert len(filter_ctx.extra["pre_sg_stress"]) == 101


def test_monotonicity_checker_flags_cyclic_data() -> None:
    strain = np.concatenate(
        [
            np.linspace(0.0, 0.10, 100),
            np.linspace(0.08, 0.12, 100),
            np.linspace(0.09, 0.14, 100),
            np.linspace(0.11, 0.16, 100),
            np.linspace(0.13, 0.18, 100),
            np.linspace(0.15, 0.20, 100),
        ]
    )
    stress = np.linspace(0.0, 600.0, len(strain))
    ctx = AnalysisContext(stress=stress, strain=strain)

    result = MonotonicityChecker(reversal_threshold=3).process(ctx)

    assert result.status == StepStatus.WARNING
    assert ctx.extra["is_cyclic"] is True
    assert ctx.extra["strain_reversals"] >= 5
    assert ctx.anomalies[0].anomaly_type == AnomalyType.NON_MONOTONIC


def test_elastic_modulus_and_offset_yield_are_computed_for_monotonic_curve() -> None:
    ctx = _build_monotonic_engineering_context()

    elastic_result = ElasticModulusDetector().process(ctx)
    yield_result = YieldDetector().process(ctx)

    assert elastic_result.status == StepStatus.SUCCESS
    assert yield_result.status == StepStatus.SUCCESS
    assert ctx.properties.elastic_modulus_gpa == pytest.approx(210.0, rel=1e-3)
    assert ctx.properties.yield_behavior == YieldBehavior.CONTINUOUS
    assert ctx.properties.yield_strength_mpa == pytest.approx(441.3879824268907, rel=1e-3)
    assert ctx.extra["yield_strain"] > 0.004
    assert "parallel-line offset" in ctx.properties.method_tags["yield"]


def test_discontinuous_yield_is_detected_from_plateau_drop() -> None:
    ctx = _build_discontinuous_yield_context()

    result = YieldDetector().process(ctx)

    assert result.status == StepStatus.SUCCESS
    assert ctx.properties.yield_behavior == YieldBehavior.DISCONTINUOUS
    assert ctx.properties.yield_strength_mpa == pytest.approx(359.84974958263774, rel=1e-3)
    assert ctx.properties.yield_lower_mpa == pytest.approx(330.00100166944236, rel=1e-3)
    assert ctx.extra["yield_ae_pct"] == pytest.approx(0.0)
    assert ctx.anomalies[0].anomaly_type == AnomalyType.DOUBLE_YIELD


def test_post_uts_detectors_compute_hardening_toughness_and_rate_code() -> None:
    ctx = _build_post_uts_true_context()
    steps = [
        UTSDetector(),
        ElongationDetector(),
        NeckingDetector(),
        StrainHardeningFitter(),
        ToughnessCalculator(),
        StrainRateValidator(),
    ]

    results = [step.process(ctx) for step in steps]

    assert all(result.status == StepStatus.SUCCESS for result in results)
    assert ctx.properties.ultimate_tensile_mpa == pytest.approx(876.3669440492461, rel=1e-3)
    assert ctx.properties.elongation_at_break_pct == pytest.approx(35.0, rel=1e-3)
    assert ctx.properties.uniform_elongation_pct == pytest.approx(14.974979149291073, rel=1e-3)
    assert ctx.properties.strain_hardening_n == pytest.approx(0.14079678478140273, rel=1e-2)
    assert ctx.properties.toughness_mj_m3 > 250.0
    assert ctx.extra["strain_rate_report_code"] == "A333"
    assert ctx.extra["strain_rate_all_ok"] is True
    assert ctx.extra["necking_idx"] < ctx.extra["uts_idx"]


def test_anomaly_detectors_flag_quality_problems() -> None:
    slip_strain = np.linspace(0.0, 0.2, 300)
    slip_stress = np.linspace(0.0, 600.0, 300)
    slip_stress[120] = 520.0
    slip_stress[121] = 380.0
    slip_stress[122:150] = np.linspace(390.0, 530.0, 28)
    slip_ctx = AnalysisContext(stress=slip_stress, strain=slip_strain)
    slip_result = GripSlippageDetector(drop_threshold=0.15, recovery_pct=0.9).process(slip_ctx)

    assert slip_result.status == StepStatus.WARNING
    assert slip_ctx.anomalies[0].anomaly_type == AnomalyType.GRIP_SLIPPAGE

    saturation_stress = np.concatenate(
        [np.linspace(0.0, 400.0, 120), np.full(40, 450.0), np.linspace(450.0, 200.0, 140)]
    )
    saturation_strain = np.linspace(0.0, 0.25, len(saturation_stress))
    saturation_ctx = AnalysisContext(stress=saturation_stress, strain=saturation_strain)
    saturation_ctx.extra["yield_strain"] = 0.01
    saturation_result = SensorSaturationDetector(
        window=20, std_threshold=0.2, min_length=10
    ).process(saturation_ctx)

    assert saturation_result.status == StepStatus.WARNING
    assert saturation_ctx.anomalies[0].anomaly_type == AnomalyType.SENSOR_SATURATION

    noise_x = np.linspace(0.0, 1.0, 500)
    noise_stress = 200.0 * noise_x + 20.0 * np.sin(2.0 * np.pi * 60.0 * noise_x)
    noise_ctx = AnalysisContext(stress=noise_stress, strain=noise_x)
    noise_result = NoiseAnalyzer(snr_threshold_db=30.0).process(noise_ctx)

    assert noise_result.status == StepStatus.WARNING
    assert noise_ctx.extra["snr_db"] < 30.0
    assert noise_ctx.anomalies[0].anomaly_type == AnomalyType.HIGH_NOISE

    integrity_stress = np.concatenate([np.linspace(0.0, 600.0, 150), np.linspace(590.0, 420.0, 50)])
    integrity_strain = np.linspace(0.0, 0.015, len(integrity_stress))
    integrity_ctx = AnalysisContext(stress=integrity_stress, strain=integrity_strain)
    integrity_ctx.properties.ultimate_tensile_mpa = 600.0
    integrity_ctx.properties.elongation_at_break_pct = 1.4
    integrity_result = CurveIntegrityChecker().process(integrity_ctx)

    assert integrity_result.status == StepStatus.WARNING
    assert {anomaly.anomaly_type for anomaly in integrity_ctx.anomalies} == {
        AnomalyType.TRUNCATION,
        AnomalyType.PREMATURE_FRACTURE,
    }

    property_ctx = AnalysisContext(stress=np.array([1.0, 2.0]), strain=np.array([0.0, 0.1]))
    property_ctx.properties.elastic_modulus_gpa = 700.0
    property_ctx.properties.yield_strength_mpa = 650.0
    property_ctx.properties.ultimate_tensile_mpa = 600.0
    property_ctx.properties.uniform_elongation_pct = 15.0
    property_ctx.properties.elongation_at_break_pct = 10.0
    property_ctx.properties.strain_hardening_n = 1.4
    property_ctx.properties.toughness_mj_m3 = -5.0
    property_result = PropertyValidator().process(property_ctx)

    assert property_result.status == StepStatus.WARNING
    assert len(property_ctx.anomalies) == 5
    assert all(anomaly.anomaly_type == AnomalyType.SPIKE for anomaly in property_ctx.anomalies)


def test_pipeline_step_builders_are_physically_ordered() -> None:
    ctx = _build_post_uts_true_context()

    assert ctx.stress_type == StressStrainType.TRUE
    assert math.isclose(ctx.properties.elastic_modulus_gpa or 0.0, 210.0)
    assert np.all(np.diff(ctx.strain) > 0)
