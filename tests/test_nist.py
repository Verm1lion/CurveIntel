"""NIST Numisheet pipeline test — Aluminum 6xxx-T4"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.pipeline.base import AnalysisContext, Pipeline
from src.pipeline.ingestion import DataLoader, SchemaDetector, UnitConverter
from src.pipeline.preprocessing import Resampler, SavitzkyGolayFilter, SpikeFilter, ToeCompensation
from src.pipeline.extraction import (
    ElasticModulusDetector, ElongationDetector, NeckingDetector,
    StrainHardeningFitter, ToughnessCalculator, UTSDetector, YieldDetector,
)

csv_path = Path(
    r"c:\Users\MSI\Desktop\Test_Cihazlari_Proje\veri_setleri"
    r"\nist_numisheet\C00Al6xxxT4Numisheet2020R01T1.521W17.91-S-Stress-Strain.csv"
)

print("=" * 65)
print(f"  NIST Numisheet Test: {csv_path.name}")
print("=" * 65)

pipeline = Pipeline([
    DataLoader(csv_path),
    SchemaDetector(),
    UnitConverter(),
    SpikeFilter(),
    ToeCompensation(),
    Resampler(n_points=2000),
    SavitzkyGolayFilter(),
    ElasticModulusDetector(),
    YieldDetector(),
    UTSDetector(),
    ElongationDetector(),
    NeckingDetector(),
    StrainHardeningFitter(),
    ToughnessCalculator(),
])

ctx = AnalysisContext()
ctx = pipeline.run(ctx)

for r in ctx.step_results:
    icon = {"success": "[OK]", "warning": "[!!]", "failure": "[XX]"}[r.status.value]
    print(f"  {icon} {r.step_name:<25} {r.message}")

p = ctx.properties
print(f"\n  E = {p.elastic_modulus_gpa:.1f} GPa" if p.elastic_modulus_gpa else "")
print(f"  Yield = {p.yield_strength_mpa:.1f} MPa" if p.yield_strength_mpa else "")
print(f"  UTS = {p.ultimate_tensile_mpa:.1f} MPa" if p.ultimate_tensile_mpa else "")
print(f"  Elongation = {p.elongation_at_break_pct:.1f}%" if p.elongation_at_break_pct else "")
print(f"  n = {p.strain_hardening_n:.3f}" if p.strain_hardening_n else "")
print(f"  Tokluk = {p.toughness_mj_m3:.2f} MJ/m3" if p.toughness_mj_m3 else "")

# Grafik
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(12, 7))
    ax.plot(ctx.strain, ctx.stress, "b-", linewidth=1.0)
    uts_idx = ctx.extra.get("uts_idx")
    if uts_idx and p.ultimate_tensile_mpa:
        ax.plot(ctx.strain[uts_idx], p.ultimate_tensile_mpa, "r^", ms=10, label=f"UTS={p.ultimate_tensile_mpa:.0f} MPa")
    ys = ctx.extra.get("yield_strain")
    if ys and p.yield_strength_mpa:
        ax.plot(ys, p.yield_strength_mpa, "go", ms=10, label=f"Yield={p.yield_strength_mpa:.0f} MPa")
    ax.set_xlabel("Strain"); ax.set_ylabel("Stress (MPa)")
    ax.set_title(f"NIST - {csv_path.stem}")
    ax.legend(); ax.grid(True, alpha=0.3)
    fig.savefig(Path(__file__).parent / "test_nist.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("\n  [GRAFIK] test_nist.png")
except: pass
