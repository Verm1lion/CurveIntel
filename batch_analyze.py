"""CurveIntel batch analysis utility."""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.curveintel.manual_data import (
    get_default_batch_input_dir,
    get_default_batch_output_dir,
)
from src.pipeline.anomaly import (
    CurveIntegrityChecker,
    GripSlippageDetector,
    NoiseAnalyzer,
    PropertyValidator,
    SensorSaturationDetector,
)
from src.pipeline.base import AnalysisContext, Pipeline
from src.pipeline.batch_qc import (
    format_batch_summary,
    generate_batch_plots,
    run_batch_qc,
)
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
from src.pipeline.reporting import export_results_csv, export_results_json, generate_pdf_report


def build_pipeline(csv_path: Path) -> Pipeline:
    """Build the default deterministic analysis pipeline."""

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
            StrainRateValidator(),
            GripSlippageDetector(),
            SensorSaturationDetector(),
            NoiseAnalyzer(),
            CurveIntegrityChecker(),
            PropertyValidator(),
        ]
    )


def analyze_single(csv_path: Path, output_dir: Path) -> AnalysisContext | None:
    """Analyze a single CSV file and export its artifacts."""

    pipeline = build_pipeline(csv_path)
    ctx = AnalysisContext()
    ctx = pipeline.run(ctx)

    stem = csv_path.stem

    pdf_path = output_dir / f"{stem}_report.pdf"
    try:
        generate_pdf_report(ctx, pdf_path)
    except Exception as exc:
        print(f"  [!!] PDF generation failed: {exc}")

    json_path = output_dir / f"{stem}_results.json"
    try:
        export_results_json(ctx, json_path)
    except Exception as exc:
        print(f"  [!!] JSON export failed: {exc}")

    return ctx


def batch_analyze(input_dir: str | Path, output_dir: str | Path | None = None) -> None:
    """Analyze every CSV file under a directory tree."""

    input_dir = Path(input_dir)
    if output_dir is None:
        output_dir = input_dir / "curveintel_reports"
    else:
        output_dir = Path(output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)

    csv_files = sorted(input_dir.rglob("*.csv"))
    csv_files = [
        file_path
        for file_path in csv_files
        if "report" not in file_path.stem.lower()
        and "summary" not in file_path.stem.lower()
        and "map" not in file_path.stem.lower()
    ]

    if not csv_files:
        print(f"  [XX] No CSV files were found under {input_dir}.")
        return

    print("=" * 70)
    print("  CurveIntel Batch Analysis")
    print(f"  Input directory: {input_dir}")
    print(f"  CSV files: {len(csv_files)}")
    print(f"  Output directory: {output_dir}")
    print("=" * 70)

    summary_csv = output_dir / "batch_summary.csv"
    if summary_csv.exists():
        summary_csv.unlink()

    success_count = 0
    fail_count = 0
    all_contexts: list[AnalysisContext] = []
    t_total = time.perf_counter()

    for index, csv_path in enumerate(csv_files, 1):
        rel = csv_path.relative_to(input_dir)
        print(f"\n  [{index}/{len(csv_files)}] {rel}")

        t0 = time.perf_counter()
        try:
            ctx = analyze_single(csv_path, output_dir)
            if ctx and ctx.has_data:
                export_results_csv(ctx, summary_csv)

                properties = ctx.properties
                uts = (
                    f"{properties.ultimate_tensile_mpa:.0f}"
                    if properties.ultimate_tensile_mpa
                    else "---"
                )
                ys = (
                    f"{properties.yield_strength_mpa:.0f}"
                    if properties.yield_strength_mpa
                    else "---"
                )
                dt = (time.perf_counter() - t0) * 1000

                print(f"         [OK] UTS={uts} MPa, Yield={ys} MPa | {dt:.0f} ms")
                success_count += 1
                all_contexts.append(ctx)
            else:
                print("         [XX] Pipeline produced no usable data")
                fail_count += 1
        except Exception as exc:
            print(f"         [XX] Error: {exc}")
            fail_count += 1

    total_time = time.perf_counter() - t_total

    print("\n" + "=" * 70)
    print("  BATCH RESULT")
    print(f"  Successful: {success_count}/{len(csv_files)}")
    print(f"  Failed: {fail_count}/{len(csv_files)}")
    print(f"  Total time: {total_time:.1f} s")
    print(f"  Summary CSV: {summary_csv}")
    print(f"  Reports: {output_dir}")
    print("=" * 70)

    if all_contexts and len(all_contexts) >= 2:
        print("\n  [QC] Running batch quality-control analysis...")
        qc_report = run_batch_qc(all_contexts)
        print(format_batch_summary(qc_report))

        plot_files = generate_batch_plots(all_contexts, qc_report, output_dir)
        for plot_file in plot_files:
            print(f"  [PLOT] {plot_file.name}")
    else:
        print("\n  [QC] At least two successful samples are required for batch QC.")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        input_path = sys.argv[1]
        output_path = sys.argv[2] if len(sys.argv) > 2 else None
        batch_analyze(input_path, output_path)
    else:
        default_input = get_default_batch_input_dir()
        default_output = get_default_batch_output_dir()
        print(f"[INFO] Using default input directory: {default_input}")
        print(f"[INFO] Using default output directory: {default_output}")
        batch_analyze(default_input, default_output)
