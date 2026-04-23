"""Serialization helpers for analysis persistence."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Mapping
from uuid import UUID, uuid4

import numpy as np
import pandas as pd

from src import __version__ as CURVEINTEL_VERSION
from src.curveintel.db.schemas import AnalysisSnapshotCreate
from src.models.enums import AnomalyType, MaterialType, StepStatus, StressStrainType, YieldBehavior
from src.pipeline.base import (
    AnalysisContext,
    AnomalyRecord,
    MechanicalProperties,
    SpecimenMetadata,
    StepResult,
)
from src.pipeline.reporting import _quality_score


def _coerce_analysis_id(value: UUID | str | None) -> UUID | None:
    """Normalize analysis identifiers to UUID values."""

    if value is None:
        return None
    if isinstance(value, UUID):
        return value
    return UUID(str(value))


def utcnow_display() -> str:
    """Return the default dashboard timestamp string."""

    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")


def compute_sha256(file_path: str | Path | None) -> str | None:
    """Compute the SHA-256 digest of a source file when available."""

    if file_path is None:
        return None

    path = Path(file_path)
    if not path.exists() or not path.is_file():
        return None

    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_json_ready(value: Any) -> Any:
    """Convert values into JSON-serializable primitives."""

    if isinstance(value, dict):
        return {str(key): make_json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [make_json_ready(item) for item in value]
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, pd.DataFrame):
        return value.to_dict(orient="list")
    if isinstance(value, pd.Series):
        return value.to_list()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (datetime, UUID)):
        return str(value)
    return value


def _coerce_optional_float(value: Any) -> float | None:
    """Coerce numeric JSON values into floats when possible."""

    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _coerce_float_array(value: Any) -> np.ndarray:
    """Coerce a JSON array-like value into a float NumPy array."""

    if value is None:
        return np.array([], dtype=float)
    try:
        return np.asarray(value, dtype=float)
    except (TypeError, ValueError):
        return np.array([], dtype=float)


def _coerce_enum_member(enum_type: type[Enum], value: Any, default: Enum) -> Enum:
    """Return a safe enum member from JSON data."""

    if isinstance(value, enum_type):
        return value
    if value is None:
        return default
    try:
        return enum_type(str(value))
    except ValueError:
        return default


def _coerce_enum_member_or_none(enum_type: type[Enum], value: Any) -> Enum | None:
    """Return an enum member or None when the value is unknown."""

    if isinstance(value, enum_type):
        return value
    if value is None:
        return None
    try:
        return enum_type(str(value))
    except ValueError:
        return None


def _mapping_or_empty(value: Any) -> Mapping[str, Any]:
    """Return a mapping-like object or an empty dict."""

    return value if isinstance(value, Mapping) else {}


def _sequence_or_empty(value: Any) -> list[Any]:
    """Return a JSON sequence or an empty list."""

    return list(value) if isinstance(value, (list, tuple)) else []


def _nearest_index(values: np.ndarray, target: float | None) -> int | None:
    """Locate the closest array index for a target value."""

    if target is None or len(values) == 0:
        return None
    return int(np.abs(values - target).argmin())


def build_analysis_context_from_payload(payload: Mapping[str, Any]) -> AnalysisContext:
    """Rebuild an AnalysisContext from the canonical dashboard payload."""

    normalized_payload = dict(payload)
    properties = _mapping_or_empty(normalized_payload.get("properties"))
    curve = _mapping_or_empty(normalized_payload.get("curve"))
    quality = _mapping_or_empty(normalized_payload.get("quality"))
    vendor = _mapping_or_empty(normalized_payload.get("vendor"))
    strain_rate = _mapping_or_empty(normalized_payload.get("strain_rate"))
    anomalies = _sequence_or_empty(
        _mapping_or_empty(normalized_payload.get("anomalies")).get("entries")
    )
    pipeline_steps = _sequence_or_empty(
        _mapping_or_empty(normalized_payload.get("pipeline")).get("steps")
    )

    strain = _coerce_float_array(curve.get("strain"))
    stress = _coerce_float_array(curve.get("stress"))
    yield_point = _mapping_or_empty(curve.get("yield_point"))
    uts_point = _mapping_or_empty(curve.get("uts_point"))
    neck_point = _mapping_or_empty(curve.get("neck_point"))

    ctx = AnalysisContext(
        stress=stress,
        strain=strain,
        stress_type=_coerce_enum_member(
            StressStrainType,
            normalized_payload.get("stress_type"),
            StressStrainType.ENGINEERING,
        ),
        metadata=SpecimenMetadata(
            specimen_id=str(normalized_payload.get("filename") or ""),
            material_type=_coerce_enum_member(
                MaterialType,
                normalized_payload.get("material_type"),
                MaterialType.UNKNOWN,
            ),
            source_file=str(normalized_payload.get("filename") or ""),
            test_standard=str(normalized_payload.get("test_standard") or "ISO 6892-1:2019"),
        ),
        properties=MechanicalProperties(
            elastic_modulus_gpa=_coerce_optional_float(properties.get("elastic_modulus_gpa")),
            yield_strength_mpa=_coerce_optional_float(properties.get("yield_strength_mpa")),
            yield_lower_mpa=_coerce_optional_float(properties.get("yield_lower_mpa")),
            ultimate_tensile_mpa=_coerce_optional_float(properties.get("ultimate_tensile_mpa")),
            elongation_at_break_pct=_coerce_optional_float(
                properties.get("elongation_at_break_pct")
            ),
            uniform_elongation_pct=_coerce_optional_float(properties.get("uniform_elongation_pct")),
            strain_hardening_n=_coerce_optional_float(properties.get("strain_hardening_n")),
            strength_coefficient_k=_coerce_optional_float(properties.get("strength_coefficient_k")),
            toughness_mj_m3=_coerce_optional_float(properties.get("toughness_mj_m3")),
            yield_behavior=_coerce_enum_member(
                YieldBehavior,
                properties.get("yield_behavior"),
                YieldBehavior.UNDEFINED,
            ),
            method_tags={
                str(key): str(value)
                for key, value in _mapping_or_empty(properties.get("method_tags")).items()
            },
        ),
        extra={
            "vendor_name": vendor.get("name"),
            "vendor_confidence": vendor.get("confidence"),
            "detected_encoding": vendor.get("encoding"),
            "detected_separator": vendor.get("separator"),
            "strain_rate_range": strain_rate.get("range"),
            "strain_rate_code": strain_rate.get("code"),
            "strain_rate_median": strain_rate.get("value"),
            "strain_rate_compliant": strain_rate.get("compliant"),
            "snr_db": quality.get("snr_db"),
            "noise_pct": quality.get("noise_pct"),
            "yield_strain": _coerce_optional_float(yield_point.get("strain")),
            "uts_idx": _nearest_index(strain, _coerce_optional_float(uts_point.get("strain"))),
            "necking_idx": _nearest_index(strain, _coerce_optional_float(neck_point.get("strain"))),
            "is_cyclic": normalized_payload.get("is_cyclic", False),
            "strain_reversals": normalized_payload.get("strain_reversals", 0),
        },
    )

    ctx.anomalies = [
        AnomalyRecord(
            anomaly_type=anomaly_type,
            confidence=_coerce_optional_float(item.get("confidence")) or 0.0,
            description=str(item.get("description") or ""),
            strain_location=_coerce_optional_float(item.get("strain_location")),
            severity=str(item.get("severity") or "warning"),
        )
        for item in anomalies
        if isinstance(item, Mapping)
        if (anomaly_type := _coerce_enum_member_or_none(AnomalyType, item.get("type"))) is not None
    ]
    ctx.step_results = [
        StepResult(
            step_name=str(item.get("name") or "UnknownStep"),
            status=_coerce_enum_member(StepStatus, item.get("status"), StepStatus.FAILURE),
            message=str(item.get("message") or ""),
            duration_ms=_coerce_optional_float(item.get("duration_ms")) or 0.0,
        )
        for item in pipeline_steps
        if isinstance(item, Mapping)
    ]
    return ctx


def build_analysis_context_from_snapshot(snapshot: Mapping[str, Any]) -> AnalysisContext:
    """Rebuild an AnalysisContext from a persisted context snapshot."""

    normalized_snapshot = dict(snapshot)
    if "legacy_analysis_payload" in normalized_snapshot:
        legacy_payload = _mapping_or_empty(normalized_snapshot.get("legacy_analysis_payload"))
        if not legacy_payload:
            raise ValueError("Legacy context snapshot does not include a usable analysis payload.")
        return build_analysis_context_from_payload(legacy_payload)

    metadata = _mapping_or_empty(normalized_snapshot.get("metadata"))
    arrays = _mapping_or_empty(normalized_snapshot.get("arrays"))
    properties = _mapping_or_empty(normalized_snapshot.get("properties"))
    raw_input = _mapping_or_empty(normalized_snapshot.get("raw_input"))

    if not metadata or not arrays or not properties:
        raise ValueError("Context snapshot is incomplete and cannot be rehydrated.")

    preview = _mapping_or_empty(raw_input.get("preview"))
    ctx = AnalysisContext(
        raw_df=pd.DataFrame(preview) if preview else pd.DataFrame(),
        stress=_coerce_float_array(arrays.get("stress")),
        strain=_coerce_float_array(arrays.get("strain")),
        stress_type=_coerce_enum_member(
            StressStrainType,
            arrays.get("stress_type"),
            StressStrainType.ENGINEERING,
        ),
        true_stress=_coerce_float_array(arrays.get("true_stress")),
        true_strain=_coerce_float_array(arrays.get("true_strain")),
        metadata=SpecimenMetadata(
            specimen_id=str(metadata.get("specimen_id") or ""),
            material_type=_coerce_enum_member(
                MaterialType,
                metadata.get("material_type"),
                MaterialType.UNKNOWN,
            ),
            cross_section_area_mm2=_coerce_optional_float(metadata.get("cross_section_area_mm2")),
            gauge_length_mm=_coerce_optional_float(metadata.get("gauge_length_mm")),
            width_mm=_coerce_optional_float(metadata.get("width_mm")),
            thickness_mm=_coerce_optional_float(metadata.get("thickness_mm")),
            test_speed_mm_min=_coerce_optional_float(metadata.get("test_speed_mm_min")),
            temperature_c=_coerce_optional_float(metadata.get("temperature_c")),
            source_file=str(metadata.get("source_file") or ""),
            test_standard=str(metadata.get("test_standard") or ""),
        ),
        properties=MechanicalProperties(
            elastic_modulus_gpa=_coerce_optional_float(properties.get("elastic_modulus_gpa")),
            yield_strength_mpa=_coerce_optional_float(properties.get("yield_strength_mpa")),
            yield_lower_mpa=_coerce_optional_float(properties.get("yield_lower_mpa")),
            ultimate_tensile_mpa=_coerce_optional_float(properties.get("ultimate_tensile_mpa")),
            elongation_at_break_pct=_coerce_optional_float(
                properties.get("elongation_at_break_pct")
            ),
            uniform_elongation_pct=_coerce_optional_float(properties.get("uniform_elongation_pct")),
            strain_hardening_n=_coerce_optional_float(properties.get("strain_hardening_n")),
            strength_coefficient_k=_coerce_optional_float(properties.get("strength_coefficient_k")),
            toughness_mj_m3=_coerce_optional_float(properties.get("toughness_mj_m3")),
            yield_behavior=_coerce_enum_member(
                YieldBehavior,
                properties.get("yield_behavior"),
                YieldBehavior.UNDEFINED,
            ),
            method_tags={
                str(key): str(value)
                for key, value in _mapping_or_empty(properties.get("method_tags")).items()
            },
        ),
        extra=dict(_mapping_or_empty(normalized_snapshot.get("extra"))),
    )

    ctx.anomalies = [
        AnomalyRecord(
            anomaly_type=anomaly_type,
            confidence=_coerce_optional_float(item.get("confidence")) or 0.0,
            description=str(item.get("description") or ""),
            strain_location=_coerce_optional_float(item.get("strain_location")),
            severity=str(item.get("severity") or "warning"),
        )
        for item in _sequence_or_empty(normalized_snapshot.get("anomalies"))
        if isinstance(item, Mapping)
        if (anomaly_type := _coerce_enum_member_or_none(AnomalyType, item.get("anomaly_type")))
        is not None
    ]
    ctx.step_results = [
        StepResult(
            step_name=str(item.get("step_name") or "UnknownStep"),
            status=_coerce_enum_member(StepStatus, item.get("status"), StepStatus.FAILURE),
            message=str(item.get("message") or ""),
            duration_ms=_coerce_optional_float(item.get("duration_ms")) or 0.0,
        )
        for item in _sequence_or_empty(normalized_snapshot.get("step_results"))
        if isinstance(item, Mapping)
    ]
    return ctx


def build_analysis_payload(
    ctx: AnalysisContext,
    filename: str,
    *,
    result_id: str | None = None,
    timestamp: str | None = None,
) -> dict[str, Any]:
    """Build the canonical dashboard/API payload for an analysis."""

    p = ctx.properties
    score, grade = _quality_score(ctx)

    strain_list: list[float] = []
    stress_list: list[float] = []
    if ctx.has_data and len(ctx.strain) > 0:
        step = max(1, len(ctx.strain) // 500)
        strain_list = ctx.strain[::step].tolist()
        stress_list = ctx.stress[::step].tolist()

    yield_strain = ctx.extra.get("yield_strain")
    uts_idx = ctx.extra.get("uts_idx")
    neck_idx = ctx.extra.get("necking_idx")

    yield_point = None
    if yield_strain is not None and p.yield_strength_mpa is not None:
        yield_point = {"strain": float(yield_strain), "stress": float(p.yield_strength_mpa)}

    uts_point = None
    if uts_idx is not None and p.ultimate_tensile_mpa is not None and ctx.has_data:
        uts_point = {"strain": float(ctx.strain[uts_idx]), "stress": float(p.ultimate_tensile_mpa)}

    neck_point = None
    if neck_idx is not None and ctx.has_data:
        neck_point = {"strain": float(ctx.strain[neck_idx]), "stress": float(ctx.stress[neck_idx])}

    steps = []
    total_ms = 0.0
    for result in ctx.step_results:
        steps.append(
            {
                "name": result.step_name,
                "status": result.status.value,
                "duration_ms": round(result.duration_ms, 2),
                "message": result.message,
            }
        )
        total_ms += result.duration_ms

    layer_status = {
        "ingestion": "success",
        "preprocessing": "success",
        "extraction": "success",
        "anomaly": "success",
        "reporting": "success",
    }
    for result in ctx.step_results:
        name = result.step_name.lower()
        if name in ("dataloader", "schemadetector", "unitconverter"):
            layer = "ingestion"
        elif name in (
            "spikefilter",
            "toecompensation",
            "resampler",
            "savgolayfilter",
            "savitzkygolayfilter",
            "monotonicitychecker",
        ):
            layer = "preprocessing"
        elif name in (
            "elasticmodulusdetector",
            "yielddetector",
            "utsdetector",
            "elongationdetector",
            "neckingdetector",
            "strainhardeningfitter",
            "toughnesscalculator",
            "strainratevalidator",
        ):
            layer = "extraction"
        elif name in (
            "gripslippagedetector",
            "sensorsaturationdetector",
            "noiseanalyzer",
            "curveintegritychecker",
            "propertyvalidator",
        ):
            layer = "anomaly"
        else:
            layer = "reporting"

        if result.status.value == "failure":
            layer_status[layer] = "failure"
        elif result.status.value == "warning" and layer_status[layer] != "failure":
            layer_status[layer] = "warning"

    anomalies = []
    info_count = 0
    warn_count = 0
    crit_count = 0
    for anomaly in ctx.anomalies:
        anomalies.append(
            {
                "type": anomaly.anomaly_type.value,
                "severity": anomaly.severity,
                "description": anomaly.description,
                "confidence": anomaly.confidence,
                "strain_location": anomaly.strain_location,
            }
        )
        if anomaly.severity == "info":
            info_count += 1
        elif anomaly.severity == "warning":
            warn_count += 1
        else:
            crit_count += 1

    vendor_name = ctx.extra.get("vendor_name", "Generic CSV")
    vendor_confidence = ctx.extra.get("vendor_confidence", 0)
    detected_encoding = ctx.extra.get("detected_encoding", "utf-8")
    detected_separator = ctx.extra.get("detected_separator", ",")
    strain_rate_range = ctx.extra.get("strain_rate_range")
    strain_rate_code = ctx.extra.get("strain_rate_code")
    strain_rate_value = ctx.extra.get("strain_rate_median")
    strain_rate_compliant = ctx.extra.get("strain_rate_compliant")

    return {
        "id": result_id or str(uuid4()),
        "filename": filename,
        "timestamp": timestamp or utcnow_display(),
        "material_type": ctx.metadata.material_type.value
        if ctx.metadata.material_type
        else "unknown",
        "stress_type": ctx.stress_type.value,
        "n_points": ctx.n_points,
        "is_cyclic": ctx.extra.get("is_cyclic", False),
        "strain_reversals": ctx.extra.get("strain_reversals", 0),
        "properties": {
            "elastic_modulus_gpa": round(p.elastic_modulus_gpa, 1)
            if p.elastic_modulus_gpa
            else None,
            "yield_strength_mpa": round(p.yield_strength_mpa, 1) if p.yield_strength_mpa else None,
            "yield_lower_mpa": round(p.yield_lower_mpa, 1) if p.yield_lower_mpa else None,
            "ultimate_tensile_mpa": round(p.ultimate_tensile_mpa, 1)
            if p.ultimate_tensile_mpa
            else None,
            "elongation_at_break_pct": round(p.elongation_at_break_pct, 1)
            if p.elongation_at_break_pct
            else None,
            "uniform_elongation_pct": round(p.uniform_elongation_pct, 2)
            if p.uniform_elongation_pct
            else None,
            "strain_hardening_n": round(p.strain_hardening_n, 3) if p.strain_hardening_n else None,
            "strength_coefficient_k": round(p.strength_coefficient_k, 1)
            if p.strength_coefficient_k
            else None,
            "toughness_mj_m3": round(p.toughness_mj_m3, 2) if p.toughness_mj_m3 else None,
            "yield_behavior": p.yield_behavior.value,
            "method_tags": dict(p.method_tags),
        },
        "quality": {
            "score": round(score, 0),
            "grade": grade.split("(")[0].strip(),
            "grade_label": grade,
            "snr_db": round(ctx.extra.get("snr_db", 0), 1),
            "noise_pct": round(ctx.extra.get("noise_pct", 0), 2),
            "elastic_r2": round(ctx.extra.get("elastic_r2", 0), 6),
            "elastic_sm_rel": round(ctx.extra.get("elastic_sm_rel", 0), 2),
            "elastic_n_points": ctx.extra.get("elastic_n_points"),
            "elastic_iterations": ctx.extra.get("elastic_iterations"),
        },
        "vendor": {
            "name": vendor_name,
            "confidence": vendor_confidence,
            "encoding": detected_encoding,
            "separator": detected_separator,
        },
        "strain_rate": {
            "range": strain_rate_range,
            "code": strain_rate_code,
            "value": round(strain_rate_value, 6) if strain_rate_value else None,
            "compliant": strain_rate_compliant,
        },
        "curve": {
            "strain": strain_list,
            "stress": stress_list,
            "yield_point": yield_point,
            "uts_point": uts_point,
            "neck_point": neck_point,
        },
        "pipeline": {
            "steps": steps,
            "total_ms": round(total_ms, 1),
            "layer_status": layer_status,
        },
        "anomalies": {
            "entries": anomalies,
            "total": len(anomalies),
            "info": info_count,
            "warning": warn_count,
            "critical": crit_count,
        },
    }


def build_context_snapshot(ctx: AnalysisContext) -> dict[str, Any]:
    """Build a reproducible context snapshot suitable for persistence."""

    return {
        "metadata": make_json_ready(
            {
                "specimen_id": ctx.metadata.specimen_id,
                "material_type": ctx.metadata.material_type,
                "cross_section_area_mm2": ctx.metadata.cross_section_area_mm2,
                "gauge_length_mm": ctx.metadata.gauge_length_mm,
                "width_mm": ctx.metadata.width_mm,
                "thickness_mm": ctx.metadata.thickness_mm,
                "test_speed_mm_min": ctx.metadata.test_speed_mm_min,
                "temperature_c": ctx.metadata.temperature_c,
                "source_file": ctx.metadata.source_file,
                "test_standard": ctx.metadata.test_standard,
            }
        ),
        "arrays": make_json_ready(
            {
                "stress": ctx.stress,
                "strain": ctx.strain,
                "true_stress": ctx.true_stress,
                "true_strain": ctx.true_strain,
                "stress_type": ctx.stress_type,
            }
        ),
        "properties": make_json_ready(
            {
                "elastic_modulus_gpa": ctx.properties.elastic_modulus_gpa,
                "yield_strength_mpa": ctx.properties.yield_strength_mpa,
                "yield_lower_mpa": ctx.properties.yield_lower_mpa,
                "ultimate_tensile_mpa": ctx.properties.ultimate_tensile_mpa,
                "elongation_at_break_pct": ctx.properties.elongation_at_break_pct,
                "uniform_elongation_pct": ctx.properties.uniform_elongation_pct,
                "strain_hardening_n": ctx.properties.strain_hardening_n,
                "strength_coefficient_k": ctx.properties.strength_coefficient_k,
                "toughness_mj_m3": ctx.properties.toughness_mj_m3,
                "yield_behavior": ctx.properties.yield_behavior,
                "method_tags": ctx.properties.method_tags,
            }
        ),
        "anomalies": make_json_ready(
            [
                {
                    "anomaly_type": anomaly.anomaly_type,
                    "confidence": anomaly.confidence,
                    "description": anomaly.description,
                    "strain_location": anomaly.strain_location,
                    "severity": anomaly.severity,
                }
                for anomaly in ctx.anomalies
            ]
        ),
        "step_results": make_json_ready(
            [
                {
                    "step_name": result.step_name,
                    "status": result.status,
                    "message": result.message,
                    "duration_ms": result.duration_ms,
                }
                for result in ctx.step_results
            ]
        ),
        "extra": make_json_ready(ctx.extra),
        "raw_input": {
            "shape": list(ctx.raw_df.shape),
            "columns": ctx.raw_df.columns.tolist(),
            "preview": make_json_ready(ctx.raw_df.head(5)) if not ctx.raw_df.empty else {},
        },
    }


def build_analysis_snapshot_from_context(
    ctx: AnalysisContext,
    filename: str,
    *,
    source_file_path: str | Path | None = None,
    input_sha256: str | None = None,
    created_by_user_id: UUID | None = None,
    engine_version: str | None = CURVEINTEL_VERSION,
    analysis_id: UUID | str | None = None,
) -> AnalysisSnapshotCreate:
    """Build a validated persistence DTO from an AnalysisContext."""

    resolved_path = str(Path(source_file_path)) if source_file_path is not None else None
    normalized_id = _coerce_analysis_id(analysis_id) or uuid4()
    return AnalysisSnapshotCreate(
        id=normalized_id,
        source_filename=filename,
        source_file_path=resolved_path,
        input_sha256=input_sha256 or compute_sha256(resolved_path),
        analysis_payload=build_analysis_payload(
            ctx,
            filename,
            result_id=str(normalized_id),
        ),
        context_snapshot=build_context_snapshot(ctx),
        created_by_user_id=created_by_user_id,
        engine_version=engine_version,
    )


def build_analysis_snapshot_from_payload(
    payload: Mapping[str, Any],
    *,
    source_file_path: str | Path | None = None,
    input_sha256: str | None = None,
    created_by_user_id: UUID | None = None,
    engine_version: str | None = CURVEINTEL_VERSION,
    context_snapshot: Mapping[str, Any] | None = None,
    analysis_id: UUID | str | None = None,
) -> AnalysisSnapshotCreate:
    """Build a validated persistence DTO from an existing dashboard payload."""

    resolved_path = str(Path(source_file_path)) if source_file_path is not None else None
    normalized_payload = make_json_ready(dict(payload))
    normalized_context = make_json_ready(
        dict(context_snapshot)
        if context_snapshot is not None
        else {"legacy_analysis_payload": payload}
    )
    payload_id = analysis_id or normalized_payload.get("id")
    normalized_id = _coerce_analysis_id(payload_id) or uuid4()
    normalized_payload["id"] = str(normalized_id)
    return AnalysisSnapshotCreate(
        id=normalized_id,
        source_file_path=resolved_path,
        input_sha256=input_sha256 or compute_sha256(resolved_path),
        analysis_payload=normalized_payload,
        context_snapshot=normalized_context,
        created_by_user_id=created_by_user_id,
        engine_version=engine_version,
    )
