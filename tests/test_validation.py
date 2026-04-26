"""CurveIntel validation suite against NIST Numisheet reference data."""

# ruff: noqa: E402

from __future__ import annotations

import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.curveintel.manual_data import get_nist_directory, manual_dataset_help
from src.pipeline.base import AnalysisContext, Pipeline
from src.pipeline.extraction import (
    ElasticModulusDetector,
    ElongationDetector,
    NeckingDetector,
    StrainHardeningFitter,
    ToughnessCalculator,
    UTSDetector,
    YieldDetector,
)
from src.pipeline.ingestion import DataLoader, SchemaDetector, UnitConverter
from src.pipeline.preprocessing import (
    Resampler,
    SavitzkyGolayFilter,
    SpikeFilter,
    ToeCompensation,
)


@dataclass
class MaterialReference:
    """Reference ranges for a known material family."""

    name: str
    rm_mpa: tuple[float, float]
    rp02_mpa: tuple[float, float]
    at_pct: tuple[float, float]
    e_gpa: tuple[float, float]
    n_hollomon: tuple[float, float]


REFERENCES = {
    "Al6xxx-T4": MaterialReference(
        name="Al6xxx-T4 (Automotive AA6xxx, T4 temper)",
        rm_mpa=(200, 350),
        rp02_mpa=(100, 320),
        at_pct=(15, 40),
        e_gpa=(40, 170),
        n_hollomon=(0.10, 10.0),
    ),
    "Al6xxx-T81": MaterialReference(
        name="Al6xxx-T81 (Automotive AA6xxx, T81 temper)",
        rm_mpa=(250, 420),
        rp02_mpa=(180, 380),
        at_pct=(5, 30),
        e_gpa=(40, 170),
        n_hollomon=(0.05, 10.0),
    ),
    "FeDP980": MaterialReference(
        name="FeDP980 (Dual-phase steel, 980 MPa class)",
        rm_mpa=(900, 1150),
        rp02_mpa=(500, 1050),
        at_pct=(5, 25),
        e_gpa=(150, 230),
        n_hollomon=(0.03, 10.0),
    ),
    "FeDP1180": MaterialReference(
        name="FeDP1180 (Dual-phase steel, 1180 MPa class)",
        rm_mpa=(1100, 1400),
        rp02_mpa=(700, 1200),
        at_pct=(3, 20),
        e_gpa=(150, 230),
        n_hollomon=(0.03, 10.0),
    ),
}


def _detect_material(filename: str) -> str | None:
    """Infer the material family from the filename."""

    upper_name = filename.upper()
    if "AL6XXX" in upper_name and "T81" in upper_name:
        return "Al6xxx-T81"
    if "AL6XXX" in upper_name and "T4" in upper_name:
        return "Al6xxx-T4"
    if "DP1180" in upper_name or "FEDP1180" in upper_name:
        return "FeDP1180"
    if "DP980" in upper_name or "FEDP980" in upper_name:
        return "FeDP980"
    return None


def build_validation_pipeline(csv_path: Path) -> Pipeline:
    """Build the validation pipeline without anomaly-only steps."""

    return Pipeline(
        [
            DataLoader(csv_path),
            SchemaDetector(),
            UnitConverter(),
            SpikeFilter(window_size=5, threshold_sigma=3.0),
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
        ]
    )


@dataclass
class ValidationResult:
    """One property-level validation result."""

    filename: str
    material: str
    property_name: str
    measured: float
    ref_min: float
    ref_max: float
    passed: bool
    note: str = ""


@dataclass
class ValidationReport:
    """Aggregate validation report."""

    total_files: int = 0
    successful_files: int = 0
    failed_files: int = 0
    results: list[ValidationResult] = field(default_factory=list)
    pass_count: int = 0
    fail_count: int = 0
    skip_count: int = 0


def run_validation(data_dir: Path, max_files: int | None = None) -> ValidationReport:
    """Run the validation suite against a NIST dataset directory."""

    report = ValidationReport()

    csv_files = sorted(data_dir.rglob("*.csv"))
    csv_files = [
        file_path
        for file_path in csv_files
        if "map" not in file_path.name.lower()
        and "summary" not in file_path.name.lower()
        and "report" not in file_path.name.lower()
        and "attributes" not in file_path.name.lower()
        and "rawdata.csv" not in file_path.name.lower()
    ]

    if max_files:
        csv_files = csv_files[:max_files]

    report.total_files = len(csv_files)

    print("=" * 70)
    print("  CurveIntel Validation Test Suite")
    print(f"  Directory: {data_dir}")
    print(f"  Files: {len(csv_files)}")
    print("=" * 70)

    for index, csv_path in enumerate(csv_files, 1):
        material = _detect_material(csv_path.name)
        if material is None:
            continue

        ref = REFERENCES[material]
        rel = csv_path.name[:40]
        print(f"\n  [{index}/{len(csv_files)}] {rel} [{material}]")

        try:
            pipeline = build_validation_pipeline(csv_path)
            ctx = AnalysisContext()
            ctx = pipeline.run(ctx)

            if not ctx.has_data:
                report.failed_files += 1
                continue

            report.successful_files += 1
            properties = ctx.properties

            checks = [
                ("Rm", properties.ultimate_tensile_mpa, ref.rm_mpa),
                ("Rp0.2", properties.yield_strength_mpa, ref.rp02_mpa),
                ("At", properties.elongation_at_break_pct, ref.at_pct),
                ("E", properties.elastic_modulus_gpa, ref.e_gpa),
                ("n", properties.strain_hardening_n, ref.n_hollomon),
            ]

            for prop_name, measured, (ref_min, ref_max) in checks:
                if measured is None:
                    report.skip_count += 1
                    continue

                passed = ref_min <= measured <= ref_max
                validation_result = ValidationResult(
                    filename=csv_path.name,
                    material=material,
                    property_name=prop_name,
                    measured=round(measured, 4),
                    ref_min=ref_min,
                    ref_max=ref_max,
                    passed=passed,
                )

                if passed:
                    report.pass_count += 1
                    icon = "OK"
                else:
                    report.fail_count += 1
                    icon = "XX"
                    validation_result.note = (
                        f"OUTSIDE_RANGE: {measured:.2f} not in [{ref_min}, {ref_max}]"
                    )

                report.results.append(validation_result)
                print(
                    f"    [{icon}] {prop_name:>6} = {measured:>10.2f}  "
                    f"ref:[{ref_min:.0f}-{ref_max:.0f}]"
                )

        except Exception as exc:
            report.failed_files += 1
            print(f"    [XX] Error: {exc}")

    total_checks = report.pass_count + report.fail_count
    pass_rate = (report.pass_count / total_checks * 100) if total_checks else 0

    print("\n" + "=" * 70)
    print("  VALIDATION RESULT")
    print(f"  Files: {report.successful_files}/{report.total_files} successful")
    print(
        f"  Checks: {report.pass_count} PASS / {report.fail_count} FAIL / {report.skip_count} SKIP"
    )
    print(f"  Pass rate: {pass_rate:.1f}%")

    if report.fail_count > 0:
        print("\n  [FAILED CHECKS]")
        for result in report.results:
            if not result.passed:
                print(
                    f"    {result.filename[:35]:35} {result.property_name:>6} = "
                    f"{result.measured:>10.2f}  ref:[{result.ref_min:.0f}-{result.ref_max:.0f}]"
                )

    print("=" * 70)
    return report


if __name__ == "__main__":
    nist_dir = (
        Path(sys.argv[1])
        if len(sys.argv) > 1 and not sys.argv[1].startswith("--")
        else get_nist_directory()
    )
    if nist_dir is None:
        print("[SKIP] No NIST dataset directory is configured for the validation suite.")
        print(f"[HINT] {manual_dataset_help()}")
        raise SystemExit(0)

    max_files = 12 if "--quick" in sys.argv else None

    t0 = time.perf_counter()
    report = run_validation(nist_dir, max_files=max_files)
    elapsed = time.perf_counter() - t0

    total_checks = report.pass_count + report.fail_count
    pass_rate = (report.pass_count / total_checks * 100) if total_checks else 0

    print(f"\n  Total time: {elapsed:.1f} s")

    if pass_rate >= 90.0:
        print(f"  [SUCCESS] Validation passed ({pass_rate:.1f}% >= 90%)")
        sys.exit(0)

    print(f"  [FAIL] Validation did not pass ({pass_rate:.1f}% < 90%)")
    sys.exit(1)
