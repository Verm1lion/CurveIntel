"""Manual PDF report smoke script kept import-safe for pytest."""

# ruff: noqa: E402

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from batch_analyze import build_pipeline
from src.curveintel.manual_data import get_nist_reference_csv, manual_dataset_help
from src.pipeline.base import AnalysisContext
from src.pipeline.reporting import export_results_json, generate_pdf_report


def main() -> None:
    """Run the manual single-file report smoke flow."""

    csv_path = get_nist_reference_csv()
    if csv_path is None:
        print(f"[SKIP] NIST report sample could not be resolved. {manual_dataset_help()}")
        return

    print("Running pipeline...")
    pipeline = build_pipeline(csv_path)
    ctx = AnalysisContext()
    ctx = pipeline.run(ctx)

    out_dir = Path(__file__).parent / "reports"
    out_dir.mkdir(exist_ok=True)

    pdf_path = out_dir / "NIST_Al6xxx_Report.pdf"
    print(f"Generating PDF: {pdf_path}")
    generate_pdf_report(
        ctx,
        pdf_path,
        company_name="CurveIntel Analysis Engine",
        operator="Test Operator",
        test_standard="ASTM E8 / ISO 6892-1",
    )
    print(f"[OK] PDF saved: {pdf_path}")

    json_path = out_dir / "NIST_Al6xxx_Results.json"
    export_results_json(ctx, json_path)
    print(f"[OK] JSON saved: {json_path}")
    print(f"\nPDF size: {pdf_path.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    main()
