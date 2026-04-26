"""Manual U-series smoke script kept import-safe for pytest."""

# ruff: noqa: E402

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from batch_analyze import build_pipeline
from src.curveintel.manual_data import get_u_series_reference_csv, manual_dataset_help
from src.pipeline.base import AnalysisContext
from src.pipeline.reporting import generate_pdf_report


def main() -> None:
    """Run the manual U-series smoke flow."""

    csv_path = get_u_series_reference_csv()
    if csv_path is None:
        print(f"[SKIP] No U-series manual sample was found. {manual_dataset_help()}")
        return

    print(f"File: {csv_path.name}")
    print(f"Size: {csv_path.stat().st_size / 1e6:.1f} MB")

    pipeline = build_pipeline(csv_path)
    ctx = AnalysisContext()
    ctx = pipeline.run(ctx)

    print("\n[PIPELINE RESULTS]")
    for result in ctx.step_results:
        icon = {"success": "[OK]", "warning": "[!!]", "failure": "[XX]"}[result.status.value]
        print(f"  {icon} {result.step_name:<25} {result.message[:70]}")

    properties = ctx.properties
    if ctx.has_data:
        print(
            f"\n  E = {properties.elastic_modulus_gpa:.1f} GPa"
            if properties.elastic_modulus_gpa
            else ""
        )
        print(
            f"  Yield = {properties.yield_strength_mpa:.1f} MPa"
            if properties.yield_strength_mpa
            else ""
        )
        print(
            f"  UTS = {properties.ultimate_tensile_mpa:.1f} MPa"
            if properties.ultimate_tensile_mpa
            else ""
        )
        print(
            f"  Elongation = {properties.elongation_at_break_pct:.1f}%"
            if properties.elongation_at_break_pct
            else ""
        )

        out_dir = Path(__file__).parent / "reports"
        out_dir.mkdir(exist_ok=True)
        pdf_path = out_dir / f"{csv_path.stem}_report.pdf"
        generate_pdf_report(ctx, pdf_path)
        print(f"\n  [PDF] {pdf_path.name} ({pdf_path.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
