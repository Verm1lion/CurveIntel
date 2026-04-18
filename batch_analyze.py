"""
CurveIntel — Batch Analiz Motoru.

Bir dizindeki tum CSV dosyalarini tarar, her biri icin tam pipeline
calistirip PDF rapor + CSV/JSON export uretir.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.pipeline.base import AnalysisContext, Pipeline
from src.pipeline.ingestion import DataLoader, SchemaDetector, UnitConverter
from src.pipeline.preprocessing import (
    Resampler, SavitzkyGolayFilter, SpikeFilter, ToeCompensation,
)
from src.pipeline.extraction import (
    ElasticModulusDetector, ElongationDetector, NeckingDetector,
    StrainHardeningFitter, StrainRateValidator, ToughnessCalculator,
    UTSDetector, YieldDetector,
)
from src.pipeline.anomaly import (
    GripSlippageDetector, SensorSaturationDetector,
    NoiseAnalyzer, CurveIntegrityChecker, PropertyValidator,
)
from src.pipeline.reporting import (
    generate_pdf_report, export_results_json, export_results_csv,
)
from src.pipeline.batch_qc import (
    run_batch_qc, format_batch_summary, generate_batch_plots,
)


def build_pipeline(csv_path: Path) -> Pipeline:
    """Standart 19-adimlik pipeline olustur."""
    return Pipeline([
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
    ])


def analyze_single(csv_path: Path, output_dir: Path) -> AnalysisContext | None:
    """Tek bir CSV dosyasini analiz et ve raporla."""
    pipeline = build_pipeline(csv_path)
    ctx = AnalysisContext()
    ctx = pipeline.run(ctx)

    stem = csv_path.stem

    # PDF rapor
    pdf_path = output_dir / f"{stem}_report.pdf"
    try:
        generate_pdf_report(ctx, pdf_path)
    except Exception as e:
        print(f"  [!!] PDF hatasi: {e}")

    # JSON export
    json_path = output_dir / f"{stem}_results.json"
    try:
        export_results_json(ctx, json_path)
    except Exception as e:
        print(f"  [!!] JSON hatasi: {e}")

    return ctx


def batch_analyze(input_dir: str | Path, output_dir: str | Path | None = None):
    """
    Bir dizindeki tum CSV dosyalarini batch olarak analiz et.

    Args:
        input_dir: CSV dosyalarinin bulundugu dizin
        output_dir: Raporlarin kaydedilecegi dizin (None ise input_dir/reports)
    """
    input_dir = Path(input_dir)
    if output_dir is None:
        output_dir = input_dir / "curveintel_reports"
    else:
        output_dir = Path(output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)

    # CSV dosyalarini bul (alt dizinler dahil)
    csv_files = sorted(input_dir.rglob("*.csv"))
    csv_files = [f for f in csv_files if "report" not in f.stem.lower()
                 and "summary" not in f.stem.lower()
                 and "map" not in f.stem.lower()]

    if not csv_files:
        print(f"  [XX] {input_dir} altinda CSV dosyasi bulunamadi.")
        return

    print("=" * 70)
    print(f"  CurveIntel Batch Analiz")
    print(f"  Dizin: {input_dir}")
    print(f"  CSV sayisi: {len(csv_files)}")
    print(f"  Cikti: {output_dir}")
    print("=" * 70)

    # Ozet CSV yolu
    summary_csv = output_dir / "batch_summary.csv"
    if summary_csv.exists():
        summary_csv.unlink()  # Eski ozeti sil

    success_count = 0
    fail_count = 0
    all_contexts = []
    t_total = time.perf_counter()

    for i, csv_path in enumerate(csv_files, 1):
        rel = csv_path.relative_to(input_dir)
        print(f"\n  [{i}/{len(csv_files)}] {rel}")

        t0 = time.perf_counter()
        try:
            ctx = analyze_single(csv_path, output_dir)
            if ctx and ctx.has_data:
                # Ozet CSV'ye ekle
                export_results_csv(ctx, summary_csv)

                p = ctx.properties
                uts = f"{p.ultimate_tensile_mpa:.0f}" if p.ultimate_tensile_mpa else "---"
                ys = f"{p.yield_strength_mpa:.0f}" if p.yield_strength_mpa else "---"
                dt = (time.perf_counter() - t0) * 1000

                print(f"         [OK] UTS={uts} MPa, Yield={ys} MPa | {dt:.0f} ms")
                success_count += 1
                all_contexts.append(ctx)
            else:
                print(f"         [XX] Pipeline veri uretmedi")
                fail_count += 1
        except Exception as e:
            print(f"         [XX] Hata: {e}")
            fail_count += 1

    total_time = time.perf_counter() - t_total

    print("\n" + "=" * 70)
    print(f"  BATCH SONUC")
    print(f"  Basarili: {success_count}/{len(csv_files)}")
    print(f"  Basarisiz: {fail_count}/{len(csv_files)}")
    print(f"  Toplam sure: {total_time:.1f} s")
    print(f"  Ozet CSV: {summary_csv}")
    print(f"  Raporlar: {output_dir}")
    print("=" * 70)

    # ─── Batch QC Analizi ───
    if all_contexts and len(all_contexts) >= 2:
        print("\n  [QC] Batch istatistik analizi baslatiliyor...")
        qc_report = run_batch_qc(all_contexts)
        print(format_batch_summary(qc_report))

        # Overlay + Box-whisker grafikleri
        plot_files = generate_batch_plots(all_contexts, qc_report, output_dir)
        for pf in plot_files:
            print(f"  [GRAFIK] {pf.name}")
    else:
        print("\n  [QC] Batch QC icin en az 2 basarili numune gerekli.")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        input_path = sys.argv[1]
        output_path = sys.argv[2] if len(sys.argv) > 2 else None
        batch_analyze(input_path, output_path)
    else:
        # Varsayilan: NIST verisini test et
        nist_dir = Path(r"c:\Users\MSI\Desktop\Test_Cihazlari_Proje\veri_setleri\nist_numisheet")
        output = Path(r"c:\Users\MSI\Desktop\Test_Cihazlari_Proje\curveintel\reports")
        batch_analyze(nist_dir, output)
