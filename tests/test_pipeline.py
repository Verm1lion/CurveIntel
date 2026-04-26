"""Manual full-pipeline smoke script kept import-safe for pytest."""

# ruff: noqa: E402

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.curveintel.manual_data import (
    get_nist_reference_csv,
    get_zenodo_reference_csv,
    manual_dataset_help,
)
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
    Resampler,
    SavitzkyGolayFilter,
    SpikeFilter,
    ToeCompensation,
)


def run_full_pipeline(csv_path: Path, label: str) -> AnalysisContext:
    """Run the full pipeline over one CSV file and print a manual summary."""

    print("=" * 70)
    print(f"  CurveIntel - {label}")
    print(f"  File: {csv_path.name}")
    print("=" * 70)

    pipeline = Pipeline(
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
            StrainRateValidator(),
            GripSlippageDetector(),
            SensorSaturationDetector(),
            NoiseAnalyzer(),
            CurveIntegrityChecker(),
            PropertyValidator(),
        ]
    )

    ctx = AnalysisContext()
    ctx = pipeline.run(ctx)

    total_ms = 0
    ok = warn = fail = 0
    print("\n[PIPELINE STEPS]")
    print("-" * 70)
    for result in ctx.step_results:
        icon = {"success": "[OK]", "warning": "[!!]", "failure": "[XX]"}[result.status.value]
        print(f"  {icon} {result.step_name:<25} {result.message[:70]}")
        total_ms += result.duration_ms
        if result.status.value == "success":
            ok += 1
        elif result.status.value == "warning":
            warn += 1
        else:
            fail += 1

    print(f"\n  Result: {ok} OK, {warn} warnings, {fail} failures | Time: {total_ms:.1f} ms")

    properties = ctx.properties
    print("\n[MECHANICAL PROPERTIES]")
    print("-" * 70)
    pairs = [
        (
            "E",
            f"{properties.elastic_modulus_gpa:.1f} GPa"
            if properties.elastic_modulus_gpa
            else "---",
        ),
        (
            "Yield",
            f"{properties.yield_strength_mpa:.1f} MPa ({properties.yield_behavior.value})"
            if properties.yield_strength_mpa
            else "---",
        ),
        (
            "UTS",
            f"{properties.ultimate_tensile_mpa:.1f} MPa"
            if properties.ultimate_tensile_mpa
            else "---",
        ),
        (
            "Elongation",
            f"{properties.elongation_at_break_pct:.1f}%"
            if properties.elongation_at_break_pct
            else "---",
        ),
        (
            "Uniform Elong.",
            f"{properties.uniform_elongation_pct:.2f}%"
            if properties.uniform_elongation_pct
            else "---",
        ),
        (
            "n (hardening)",
            f"{properties.strain_hardening_n:.3f}" if properties.strain_hardening_n else "---",
        ),
        (
            "Toughness",
            f"{properties.toughness_mj_m3:.2f} MJ/m3" if properties.toughness_mj_m3 else "---",
        ),
    ]
    for name, value in pairs:
        print(f"  {name:<20} {value}")

    snr = ctx.extra.get("snr_db")
    noise_pct = ctx.extra.get("noise_pct")
    if snr:
        print(f"\n  [SIGNAL QUALITY] SNR={snr:.1f} dB, Noise={noise_pct:.2f}%")

    info_count = sum(1 for anomaly in ctx.anomalies if anomaly.severity == "info")
    warn_count = sum(1 for anomaly in ctx.anomalies if anomaly.severity == "warning")
    crit_count = sum(1 for anomaly in ctx.anomalies if anomaly.severity == "critical")

    print(
        f"\n[ANOMALIES] Total: {len(ctx.anomalies)} "
        f"(info={info_count}, warning={warn_count}, critical={crit_count})"
    )
    print("-" * 70)
    for anomaly in ctx.anomalies:
        print(f"  [{anomaly.severity:8}] {anomaly.anomaly_type.value}: {anomaly.description[:65]}")

    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(12, 7))
        ax.plot(ctx.strain, ctx.stress, "b-", lw=1.0, label="Stress-Strain")

        yield_strain = ctx.extra.get("yield_strain")
        if yield_strain and properties.yield_strength_mpa:
            ax.plot(
                yield_strain,
                properties.yield_strength_mpa,
                "go",
                ms=10,
                label=f"Yield={properties.yield_strength_mpa:.0f} MPa",
            )

        uts_idx = ctx.extra.get("uts_idx")
        if uts_idx and properties.ultimate_tensile_mpa:
            ax.plot(
                ctx.strain[uts_idx],
                properties.ultimate_tensile_mpa,
                "r^",
                ms=10,
                label=f"UTS={properties.ultimate_tensile_mpa:.0f} MPa",
            )

        neck_idx = ctx.extra.get("necking_idx")
        if neck_idx:
            ax.axvline(ctx.strain[neck_idx], color="orange", ls="--", alpha=0.7, label="Necking")

        for anomaly in ctx.anomalies:
            if anomaly.strain_location and anomaly.severity in ("warning", "critical"):
                ax.axvline(anomaly.strain_location, color="red", ls=":", alpha=0.4)

        ax.set_xlabel("Strain (mm/mm)", fontsize=12)
        ax.set_ylabel("Stress (MPa)", fontsize=12)
        ax.set_title(f"CurveIntel Analysis - {csv_path.stem}", fontsize=14)
        ax.legend(fontsize=10, loc="lower right")
        ax.grid(True, alpha=0.3)

        plot_name = f"test_{label.lower().replace(' ', '_')}.png"
        fig.savefig(Path(__file__).parent / plot_name, dpi=150, bbox_inches="tight")
        plt.close()
        print(f"\n  [PLOT] {plot_name}")
    except Exception:
        pass

    print("\n")
    return ctx


def main() -> None:
    """Run the manual full-pipeline smoke flow."""

    runs: list[tuple[Path, str]] = []

    nist_csv = get_nist_reference_csv()
    if nist_csv is not None:
        runs.append((nist_csv, "NIST Al6xxx-T4"))

    zenodo_csv = get_zenodo_reference_csv()
    if zenodo_csv is not None:
        runs.append((zenodo_csv, "Zenodo S355J2"))

    if not runs:
        print(f"[SKIP] No manual smoke files were resolved. {manual_dataset_help()}")
        return

    for csv_path, label in runs:
        run_full_pipeline(csv_path, label)


if __name__ == "__main__":
    main()
