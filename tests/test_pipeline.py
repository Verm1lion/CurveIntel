"""
CurveIntel — Full Pipeline Test (Katman 1-4)
NIST Al6xxx-T4 verisiyle tum pipeline entegrasyon testi.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.pipeline.base import AnalysisContext, Pipeline
from src.pipeline.ingestion import DataLoader, SchemaDetector, UnitConverter
from src.pipeline.preprocessing import (
    Resampler,
    SavitzkyGolayFilter,
    SpikeFilter,
    ToeCompensation,
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
from src.pipeline.anomaly import (
    GripSlippageDetector,
    SensorSaturationDetector,
    NoiseAnalyzer,
    CurveIntegrityChecker,
    PropertyValidator,
)


def run_full_pipeline(csv_path: Path, label: str):
    print("=" * 70)
    print(f"  CurveIntel v0.1 — {label}")
    print(f"  Dosya: {csv_path.name}")
    print("=" * 70)

    pipeline = Pipeline(
        [
            # Katman 1: Data Ingestion
            DataLoader(csv_path),
            SchemaDetector(),
            UnitConverter(),
            # Katman 2: Signal Preprocessing
            SpikeFilter(window_size=5, threshold_sigma=3.0),
            ToeCompensation(),
            Resampler(n_points=2000),
            SavitzkyGolayFilter(window_length=21, polyorder=3),
            # Katman 3: Feature Extraction
            ElasticModulusDetector(),
            YieldDetector(),
            UTSDetector(),
            ElongationDetector(),
            NeckingDetector(),
            StrainHardeningFitter(),
            ToughnessCalculator(),
            StrainRateValidator(),
            # Katman 4: Anomaly Detection
            GripSlippageDetector(),
            SensorSaturationDetector(),
            NoiseAnalyzer(),
            CurveIntegrityChecker(),
            PropertyValidator(),
        ]
    )

    ctx = AnalysisContext()
    ctx = pipeline.run(ctx)

    # Sonuclar
    total_ms = 0
    ok = warn = fail = 0
    print("\n[PIPELINE ADIMLARI]")
    print("-" * 70)
    for r in ctx.step_results:
        icon = {"success": "[OK]", "warning": "[!!]", "failure": "[XX]"}[r.status.value]
        print(f"  {icon} {r.step_name:<25} {r.message[:70]}")
        total_ms += r.duration_ms
        if r.status.value == "success":
            ok += 1
        elif r.status.value == "warning":
            warn += 1
        else:
            fail += 1

    print(f"\n  Sonuc: {ok} OK, {warn} uyari, {fail} hata | Sure: {total_ms:.1f} ms")

    # Mekanik ozellikler
    p = ctx.properties
    print("\n[MEKANIK OZELLIKLER]")
    print("-" * 70)
    pairs = [
        ("E", f"{p.elastic_modulus_gpa:.1f} GPa" if p.elastic_modulus_gpa else "---"),
        (
            "Yield",
            f"{p.yield_strength_mpa:.1f} MPa ({p.yield_behavior.value})"
            if p.yield_strength_mpa
            else "---",
        ),
        ("UTS", f"{p.ultimate_tensile_mpa:.1f} MPa" if p.ultimate_tensile_mpa else "---"),
        ("Elongation", f"{p.elongation_at_break_pct:.1f}%" if p.elongation_at_break_pct else "---"),
        (
            "Uniform Elong.",
            f"{p.uniform_elongation_pct:.2f}%" if p.uniform_elongation_pct else "---",
        ),
        ("n (hardening)", f"{p.strain_hardening_n:.3f}" if p.strain_hardening_n else "---"),
        ("Tokluk", f"{p.toughness_mj_m3:.2f} MJ/m3" if p.toughness_mj_m3 else "---"),
    ]
    for name, val in pairs:
        print(f"  {name:<20} {val}")

    # SNR bilgisi
    snr = ctx.extra.get("snr_db")
    noise_pct = ctx.extra.get("noise_pct")
    if snr:
        print(f"\n  [SINYAL KALITESI] SNR={snr:.1f} dB, Gurultu={noise_pct:.2f}%")

    # Anomaliler
    info_count = sum(1 for a in ctx.anomalies if a.severity == "info")
    warn_count = sum(1 for a in ctx.anomalies if a.severity == "warning")
    crit_count = sum(1 for a in ctx.anomalies if a.severity == "critical")

    print(
        f"\n[ANOMALILER] Toplam: {len(ctx.anomalies)} "
        f"(info={info_count}, uyari={warn_count}, kritik={crit_count})"
    )
    print("-" * 70)
    for a in ctx.anomalies:
        print(f"  [{a.severity:8}] {a.anomaly_type.value}: {a.description[:65]}")

    # Grafik
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(12, 7))
        ax.plot(ctx.strain, ctx.stress, "b-", lw=1.0, label="Stress-Strain")

        # Yield
        ys = ctx.extra.get("yield_strain")
        if ys and p.yield_strength_mpa:
            ax.plot(
                ys, p.yield_strength_mpa, "go", ms=10, label=f"Yield={p.yield_strength_mpa:.0f} MPa"
            )

        # UTS
        uts_idx = ctx.extra.get("uts_idx")
        if uts_idx and p.ultimate_tensile_mpa:
            ax.plot(
                ctx.strain[uts_idx],
                p.ultimate_tensile_mpa,
                "r^",
                ms=10,
                label=f"UTS={p.ultimate_tensile_mpa:.0f} MPa",
            )

        # Necking
        neck_idx = ctx.extra.get("necking_idx")
        if neck_idx:
            ax.axvline(ctx.strain[neck_idx], color="orange", ls="--", alpha=0.7, label="Necking")

        # Anomali konumlari
        for a in ctx.anomalies:
            if a.strain_location and a.severity in ("warning", "critical"):
                ax.axvline(a.strain_location, color="red", ls=":", alpha=0.4)

        ax.set_xlabel("Strain (mm/mm)", fontsize=12)
        ax.set_ylabel("Stress (MPa)", fontsize=12)
        ax.set_title(f"CurveIntel Analysis — {csv_path.stem}", fontsize=14)
        ax.legend(fontsize=10, loc="lower right")
        ax.grid(True, alpha=0.3)

        plot_name = f"test_{label.lower().replace(' ', '_')}.png"
        fig.savefig(Path(__file__).parent / plot_name, dpi=150, bbox_inches="tight")
        plt.close()
        print(f"\n  [GRAFIK] {plot_name}")
    except Exception:
        pass

    print("\n")
    return ctx


def main():
    base = Path(r"c:\Users\MSI\Desktop\Test_Cihazlari_Proje\veri_setleri")

    # Test 1: NIST Al6xxx-T4
    nist_csv = (
        base / "nist_numisheet" / "C00Al6xxxT4Numisheet2020R01T1.521W17.91-S-Stress-Strain.csv"
    )
    if nist_csv.exists():
        run_full_pipeline(nist_csv, "NIST Al6xxx-T4")

    # Test 2: Zenodo S355J2
    zenodo_csv = (
        base
        / "Zenodo Structural Metallic DB"
        / "Clean_Data_v1-0-0"
        / "Clean_Data"
        / "S355J2_Plates"
        / "S355J2_N_25mm"
        / "S_8_00_N_5.csv"
    )
    if zenodo_csv.exists():
        run_full_pipeline(zenodo_csv, "Zenodo S355J2")


if __name__ == "__main__":
    main()
