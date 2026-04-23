"""Manual NIST pipeline smoke script kept import-safe for pytest."""

from __future__ import annotations

from pathlib import Path

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
from src.pipeline.preprocessing import Resampler, SavitzkyGolayFilter, SpikeFilter, ToeCompensation


def main() -> None:
    """Run the manual NIST smoke flow."""

    csv_path = Path(
        r"c:\Users\MSI\Desktop\Test_Cihazlari_Proje\veri_setleri"
        r"\nist_numisheet\C00Al6xxxT4Numisheet2020R01T1.521W17.91-S-Stress-Strain.csv"
    )

    print("=" * 65)
    print(f"  NIST Numisheet Test: {csv_path.name}")
    print("=" * 65)

    pipeline = Pipeline(
        [
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
        ]
    )

    ctx = AnalysisContext()
    ctx = pipeline.run(ctx)

    for result in ctx.step_results:
        icon = {"success": "[OK]", "warning": "[!!]", "failure": "[XX]"}[result.status.value]
        print(f"  {icon} {result.step_name:<25} {result.message}")

    properties = ctx.properties
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
    print(f"  n = {properties.strain_hardening_n:.3f}" if properties.strain_hardening_n else "")
    print(
        f"  Tokluk = {properties.toughness_mj_m3:.2f} MJ/m3" if properties.toughness_mj_m3 else ""
    )

    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(12, 7))
        ax.plot(ctx.strain, ctx.stress, "b-", linewidth=1.0)
        uts_idx = ctx.extra.get("uts_idx")
        if uts_idx and properties.ultimate_tensile_mpa:
            ax.plot(
                ctx.strain[uts_idx],
                properties.ultimate_tensile_mpa,
                "r^",
                ms=10,
                label=f"UTS={properties.ultimate_tensile_mpa:.0f} MPa",
            )
        yield_strain = ctx.extra.get("yield_strain")
        if yield_strain and properties.yield_strength_mpa:
            ax.plot(
                yield_strain,
                properties.yield_strength_mpa,
                "go",
                ms=10,
                label=f"Yield={properties.yield_strength_mpa:.0f} MPa",
            )
        ax.set_xlabel("Strain")
        ax.set_ylabel("Stress (MPa)")
        ax.set_title(f"NIST - {csv_path.stem}")
        ax.legend()
        ax.grid(True, alpha=0.3)
        fig.savefig(Path(__file__).parent / "test_nist.png", dpi=150, bbox_inches="tight")
        plt.close()
        print("\n  [GRAFIK] test_nist.png")
    except Exception:
        pass


if __name__ == "__main__":
    main()
