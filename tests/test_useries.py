"""U-serisi DIC verisi pipeline testi — Force/Extensometer."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from batch_analyze import build_pipeline
from src.pipeline.base import AnalysisContext
from src.pipeline.reporting import generate_pdf_report

csv_path = Path(
    r"c:\Users\MSI\Desktop\Test_Cihazlari_Proje\veri_setleri"
    r"\nist_numisheet\U00FeDP980R01T1.405W12.7.csv"
)

print(f"Dosya: {csv_path.name}")
print(f"Boyut: {csv_path.stat().st_size / 1e6:.1f} MB")

pipeline = build_pipeline(csv_path)
ctx = AnalysisContext()
ctx = pipeline.run(ctx)

print("\n[PIPELINE SONUCLARI]")
for r in ctx.step_results:
    icon = {"success": "[OK]", "warning": "[!!]", "failure": "[XX]"}[r.status.value]
    print(f"  {icon} {r.step_name:<25} {r.message[:70]}")

p = ctx.properties
if ctx.has_data:
    print(f"\n  E = {p.elastic_modulus_gpa:.1f} GPa" if p.elastic_modulus_gpa else "")
    print(f"  Yield = {p.yield_strength_mpa:.1f} MPa" if p.yield_strength_mpa else "")
    print(f"  UTS = {p.ultimate_tensile_mpa:.1f} MPa" if p.ultimate_tensile_mpa else "")
    print(f"  Elongation = {p.elongation_at_break_pct:.1f}%" if p.elongation_at_break_pct else "")

    # PDF rapor
    out_dir = Path(__file__).parent / "reports"
    out_dir.mkdir(exist_ok=True)
    pdf = out_dir / f"{csv_path.stem}_report.pdf"
    generate_pdf_report(ctx, pdf)
    print(f"\n  [PDF] {pdf.name} ({pdf.stat().st_size / 1024:.0f} KB)")
