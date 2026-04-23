"""Manual PDF report smoke script kept import-safe for pytest."""

from __future__ import annotations

from pathlib import Path

from batch_analyze import build_pipeline
from src.pipeline.base import AnalysisContext
from src.pipeline.reporting import export_results_json, generate_pdf_report


def main() -> None:
    """Run the manual single-file report smoke flow."""

    csv_path = Path(
        r"c:\Users\MSI\Desktop\Test_Cihazlari_Proje\veri_setleri"
        r"\nist_numisheet\C00Al6xxxT4Numisheet2020R01T1.521W17.91-S-Stress-Strain.csv"
    )

    print("Pipeline calisiyor...")
    pipeline = build_pipeline(csv_path)
    ctx = AnalysisContext()
    ctx = pipeline.run(ctx)

    out_dir = Path(__file__).parent / "reports"
    out_dir.mkdir(exist_ok=True)

    pdf_path = out_dir / "NIST_Al6xxx_Report.pdf"
    print(f"PDF olusturuluyor: {pdf_path}")
    generate_pdf_report(
        ctx,
        pdf_path,
        company_name="CurveIntel Analysis Engine",
        operator="Test Operatoru",
        test_standard="ASTM E8 / ISO 6892-1",
    )
    print(f"[OK] PDF kaydedildi: {pdf_path}")

    json_path = out_dir / "NIST_Al6xxx_Results.json"
    export_results_json(ctx, json_path)
    print(f"[OK] JSON kaydedildi: {json_path}")
    print(f"\nDosya boyutu: {pdf_path.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    main()
