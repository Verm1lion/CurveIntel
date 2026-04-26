"""CurveIntel full-dataset diagnostic script.

Run every CSV file in an external dataset folder through the pipeline and
persist a summary CSV with coarse status buckets.
"""

# ruff: noqa: E402

from __future__ import annotations

import csv
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.curveintel.manual_data import get_dataset_root, manual_dataset_help
from src.pipeline.anomaly import (
    CurveIntegrityChecker,
    GripSlippageDetector,
    NoiseAnalyzer,
    PropertyValidator,
    SensorSaturationDetector,
)
from src.pipeline.base import AnalysisContext, Pipeline
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
from src.pipeline.ingestion import DataLoader, SchemaDetector, UnitConverter
from src.pipeline.preprocessing import (
    MonotonicityChecker,
    Resampler,
    SavitzkyGolayFilter,
    SpikeFilter,
    ToeCompensation,
)
from src.pipeline.reporting import _quality_score


def build_pipeline(csv_path: Path) -> Pipeline:
    """Build the full diagnostic pipeline."""

    return Pipeline(
        [
            DataLoader(csv_path),
            SchemaDetector(),
            UnitConverter(),
            SpikeFilter(window_size=5, threshold_sigma=3.0),
            MonotonicityChecker(),
            ToeCompensation(),
            Resampler(n_points=2000),
            SavitzkyGolayFilter(window_length=21, polyorder=3),
            ElasticModulusDetector(),
            YieldDetector(),
            UTSDetector(),
            ElongationDetector(),
            NeckingDetector(),
            StrainHardeningFitter(),
            ToughnessCalculator(),
            StrainRateValidator(),
            GripSlippageDetector(),
            SensorSaturationDetector(),
            NoiseAnalyzer(),
            CurveIntegrityChecker(),
            PropertyValidator(),
        ]
    )


DATASET_ROOT = get_dataset_root()
OUTPUT_CSV = Path(__file__).parent / "diagnostic_results.csv"


def _relative_path(csv_path: Path) -> str:
    """Return a stable relative path for reporting."""

    if DATASET_ROOT is None:
        return csv_path.name
    try:
        return str(csv_path.relative_to(DATASET_ROOT))
    except ValueError:
        return csv_path.name


def analyze_file(csv_path: Path) -> dict:
    """Analyze one file and return a summary dictionary."""

    result = {
        "file": csv_path.name,
        "dir": csv_path.parent.name,
        "rel_path": _relative_path(csv_path),
        "size_kb": round(csv_path.stat().st_size / 1024, 1),
        "status": "UNKNOWN",
        "n_points": 0,
        "has_data": False,
        "E_gpa": None,
        "yield_mpa": None,
        "uts_mpa": None,
        "elongation_pct": None,
        "score": None,
        "grade": None,
        "errors": [],
        "warnings": [],
        "duration_ms": 0,
        "fail_reason": None,
    }

    try:
        with csv_path.open("r", errors="replace") as handle:
            head = [handle.readline().strip() for _ in range(3)]
        result["head_preview"] = " | ".join(head[:2])[:100]

        t0 = time.perf_counter()
        pipeline = build_pipeline(csv_path)
        ctx = AnalysisContext()
        ctx = pipeline.run(ctx)
        result["duration_ms"] = round((time.perf_counter() - t0) * 1000, 1)

        result["has_data"] = ctx.has_data
        result["n_points"] = ctx.n_points

        if not ctx.has_data or ctx.n_points == 0:
            result["status"] = "NO_DATA"
            result["fail_reason"] = "Pipeline ran but no stress-strain data was extracted."
            return result

        properties = ctx.properties
        result["E_gpa"] = (
            round(properties.elastic_modulus_gpa, 1) if properties.elastic_modulus_gpa else None
        )
        result["yield_mpa"] = (
            round(properties.yield_strength_mpa, 1) if properties.yield_strength_mpa else None
        )
        result["uts_mpa"] = (
            round(properties.ultimate_tensile_mpa, 1) if properties.ultimate_tensile_mpa else None
        )
        result["elongation_pct"] = (
            round(properties.elongation_at_break_pct, 1)
            if properties.elongation_at_break_pct
            else None
        )

        score, grade = _quality_score(ctx)
        result["score"] = round(score, 0)
        result["grade"] = grade

        missing = []
        if not properties.elastic_modulus_gpa:
            missing.append("E")
        if not properties.yield_strength_mpa:
            missing.append("Yield")
        if not properties.ultimate_tensile_mpa:
            missing.append("UTS")
        if not properties.elongation_at_break_pct:
            missing.append("Elongation")
        result["missing_props"] = missing

        for anomaly in ctx.anomalies:
            if anomaly.severity in ("warning", "critical"):
                result["warnings"].append(
                    f"{anomaly.anomaly_type.value}: {anomaly.description[:60]}"
                )

        for step in ctx.step_results:
            if step.status.value == "failure":
                result["errors"].append(f"{step.step_name}: {step.message[:60]}")

        is_cyclic = ctx.extra.get("is_cyclic", False)
        result["is_cyclic"] = is_cyclic

        if is_cyclic:
            result["status"] = "CYCLIC"
            result["fail_reason"] = (
                f"Cyclic data ({ctx.extra.get('strain_reversals', 0)} reversals)"
            )
        elif result["uts_mpa"] and result["uts_mpa"] > 0:
            result["status"] = "FULL_RESULT" if len(missing) <= 1 else "PARTIAL_RESULT"
        elif result["n_points"] > 0:
            result["status"] = "DATA_ONLY"
        else:
            result["status"] = "NO_DATA"

    except Exception as exc:
        result["status"] = "ERROR"
        result["fail_reason"] = f"{type(exc).__name__}: {str(exc)[:100]}"

    return result


if __name__ == "__main__":
    if len(sys.argv) > 1:
        DATASET_ROOT = get_dataset_root(sys.argv[1])

    if DATASET_ROOT is None:
        print("[SKIP] No external dataset root is configured for the diagnostic run.")
        print(f"[HINT] {manual_dataset_help()}")
        raise SystemExit(0)

    csv_files = sorted(DATASET_ROOT.rglob("*.csv"))
    print(f"[DIAGNOSTIC] Found {len(csv_files)} CSV files under {DATASET_ROOT}\n")

    results = []
    status_counts = {
        "FULL_RESULT": 0,
        "PARTIAL_RESULT": 0,
        "DATA_ONLY": 0,
        "CYCLIC": 0,
        "NO_DATA": 0,
        "ERROR": 0,
    }

    for index, csv_file in enumerate(csv_files, 1):
        result = analyze_file(csv_file)
        results.append(result)
        status_counts[result["status"]] = status_counts.get(result["status"], 0) + 1

        icon = {
            "FULL_RESULT": "[OK]",
            "PARTIAL_RESULT": "[PT]",
            "DATA_ONLY": "[DO]",
            "CYCLIC": "[CY]",
            "NO_DATA": "[ND]",
            "ERROR": "[ER]",
        }.get(result["status"], "[??]")
        props = (
            f"E={result['E_gpa']} Ys={result['yield_mpa']} UTS={result['uts_mpa']}"
            if result["uts_mpa"]
            else (result["fail_reason"] or "no properties")[:50]
        )
        print(
            f"  [{index:3d}/{len(csv_files)}] {icon} "
            f"{result['dir']}/{result['file'][:50]:50s} | "
            f"{result['status']:15s} | {props}"
        )

    print(f"\n{'=' * 80}")
    print(f"RESULTS ({len(csv_files)} files)")
    print(f"{'=' * 80}")
    for status, count in sorted(status_counts.items()):
        pct = count / len(csv_files) * 100 if csv_files else 0
        bar = "#" * int(pct / 2) + "-" * (50 - int(pct / 2))
        print(f"  {status:20s} {count:4d} ({pct:5.1f}%) {bar}")

    print(f"\n{'=' * 80}")
    print("FAILED FILES (NO_DATA + ERROR)")
    print(f"{'=' * 80}")
    failures = [result for result in results if result["status"] in ("NO_DATA", "ERROR")]
    if failures:
        reasons: dict[str, list[str]] = {}
        for result in failures:
            reason = result.get("fail_reason", "unknown") or "no stress-strain columns"
            reasons.setdefault(reason[:60], []).append(result["file"])
        for reason, files in sorted(reasons.items(), key=lambda item: -len(item[1])):
            print(f"\n  [{len(files)} files] {reason}")
            for filename in files[:5]:
                print(f"    - {filename}")
            if len(files) > 5:
                print(f"    ... and {len(files) - 5} more")

    with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "status",
                "is_cyclic",
                "dir",
                "file",
                "n_points",
                "E_gpa",
                "yield_mpa",
                "uts_mpa",
                "elongation_pct",
                "score",
                "grade",
                "duration_ms",
                "fail_reason",
                "missing_props",
                "warnings",
                "errors",
                "size_kb",
                "rel_path",
            ],
        )
        writer.writeheader()
        for result in results:
            row = dict(result)
            row["missing_props"] = ",".join(result.get("missing_props", []))
            row["warnings"] = " | ".join(result.get("warnings", []))
            row["errors"] = " | ".join(result.get("errors", []))
            row.pop("has_data", None)
            row.pop("head_preview", None)
            writer.writerow(row)

    print(f"\n[OUTPUT] Detailed diagnostic results: {OUTPUT_CSV}")
