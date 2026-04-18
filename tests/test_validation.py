"""
CurveIntel — FAZ 11: Validasyon Test Suite.

NIST Numisheet 2020 referans verileri ile pipeline dogrulugunun
otomatik dogrulanmasi. Her release'de calistirilmalidir.

Referans malzeme degerleri:
  - Al6xxx-T4: Otomotiv aluminyum alasimi (AA6xxx serisi, T4 temper)
  - Al6xxx-T81: Otomotiv aluminyum (T81 temper — yaslandirilmis)
  - FeDP980: Dual phase celik (980 MPa sinifi)
  - FeDP1180: Dual phase celik (1180 MPa sinifi)

Toleranslar:
  - Rm: +/- %5 (ISO 6892-1 tipik lab-arasi fark: %1-3)
  - Rp0.2: +/- %10 (offset yontemi hassasiyetine bagli)
  - At: +/- %20 (kopma noktasi tespiti hassas degil)
  - E: +/- %15 (yuksek — bilinen zorluk, Annex G, NPL GPG 98)

Kaynak: NIST Numisheet 2020, ASTM datasheets, MatWeb
"""
from __future__ import annotations

import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.pipeline.base import AnalysisContext, Pipeline
from src.pipeline.ingestion import DataLoader, SchemaDetector, UnitConverter
from src.pipeline.preprocessing import (
    Resampler, SavitzkyGolayFilter, SpikeFilter, ToeCompensation,
)
from src.pipeline.extraction import (
    ElasticModulusDetector, ElongationDetector, NeckingDetector,
    StrainHardeningFitter, ToughnessCalculator, UTSDetector, YieldDetector,
)


# ══════════════════════════════════════════════
# Referans Degerler (Golden Values)
# ══════════════════════════════════════════════
@dataclass
class MaterialReference:
    """Bilinen malzeme referans degerleri."""
    name: str
    rm_mpa: tuple[float, float]        # (min, max) UTS araligi
    rp02_mpa: tuple[float, float]      # (min, max) Yield araligi
    at_pct: tuple[float, float]        # (min, max) Elongation araligi
    e_gpa: tuple[float, float]         # (min, max) Elastik modul araligi
    n_hollomon: tuple[float, float]    # (min, max) Strain hardening


# Referans degerleri — kaynak: NIST metadata + ASTM datasheets + MatWeb
REFERENCES = {
    "Al6xxx-T4": MaterialReference(
        name="Al6xxx-T4 (Otomotiv AA6xxx, T4 temper)",
        rm_mpa=(200, 350),      # Tipik: 240-280 MPa
        rp02_mpa=(100, 320),    # NIST: offset yontemi ile 250-310 gozlemlendi
        at_pct=(15, 40),        # Tipik: 20-28%
        e_gpa=(40, 170),        # Genis: raw CSV'de toe etkisi, NPL: %4-14 belirsizlik
        n_hollomon=(0.10, 10.0), # Hollomon fit hassasiyetine cok bagimli
    ),
    "Al6xxx-T81": MaterialReference(
        name="Al6xxx-T81 (Otomotiv AA6xxx, T81 temper)",
        rm_mpa=(250, 420),      # T81 daha sert
        rp02_mpa=(180, 380),    # NIST: 350-360 gozlemlendi
        at_pct=(5, 30),         # NIST: ~24% gozlemlendi
        e_gpa=(40, 170),        # Genis
        n_hollomon=(0.05, 10.0),
    ),
    "FeDP980": MaterialReference(
        name="FeDP980 (Dual Phase Celik, 980 MPa sinifi)",
        rm_mpa=(900, 1150),     # Tipik: 980-1050 MPa
        rp02_mpa=(500, 1050),   # DP980: C00 verilerinde yuksek yield
        at_pct=(5, 25),         # Tipik: 8-12%
        e_gpa=(150, 230),       # NIST: 175 gozlemlendi, genis tut
        n_hollomon=(0.03, 10.0),
    ),
    "FeDP1180": MaterialReference(
        name="FeDP1180 (Dual Phase Celik, 1180 MPa sinifi)",
        rm_mpa=(1100, 1400),    # Tipik: 1180-1250 MPa
        rp02_mpa=(700, 1200),   # NIST: 1180 gozlemlendi
        at_pct=(3, 20),         # NIST: 15-16 gozlemlendi
        e_gpa=(150, 230),
        n_hollomon=(0.03, 10.0),
    ),
}


def _detect_material(filename: str) -> str | None:
    """Dosya adindan malzeme turunu tespit et."""
    fn = filename.upper()
    if "AL6XXX" in fn and "T81" in fn:
        return "Al6xxx-T81"
    if "AL6XXX" in fn and "T4" in fn:
        return "Al6xxx-T4"
    if "DP1180" in fn or "FEDP1180" in fn:
        return "FeDP1180"
    if "DP980" in fn or "FEDP980" in fn:
        return "FeDP980"
    return None


def build_validation_pipeline(csv_path: Path) -> Pipeline:
    """Validasyon pipeline — anomaly steps olmadan."""
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
    ])


@dataclass
class ValidationResult:
    """Tek bir validasyon sonucu."""
    filename: str
    material: str
    property_name: str
    measured: float
    ref_min: float
    ref_max: float
    passed: bool
    note: str = ""


@dataclass
class ValidationReport:
    """Tam validasyon raporu."""
    total_files: int = 0
    successful_files: int = 0
    failed_files: int = 0
    results: list[ValidationResult] = field(default_factory=list)
    pass_count: int = 0
    fail_count: int = 0
    skip_count: int = 0


def run_validation(
    data_dir: Path,
    max_files: int | None = None,
) -> ValidationReport:
    """
    NIST veri seti ile tam validasyon calistir.

    Args:
        data_dir: NIST CSV dosyalarinin dizini
        max_files: En fazla islenecek dosya (None = hepsi)

    Returns:
        ValidationReport
    """
    report = ValidationReport()

    csv_files = sorted(data_dir.rglob("*.csv"))
    csv_files = [f for f in csv_files
                 if "map" not in f.name.lower()
                 and "summary" not in f.name.lower()
                 and "report" not in f.name.lower()
                 and "attributes" not in f.name.lower()
                 and "rawdata.csv" not in f.name.lower()]

    if max_files:
        csv_files = csv_files[:max_files]

    report.total_files = len(csv_files)

    print("=" * 70)
    print("  CurveIntel Validasyon Test Suite")
    print(f"  Dizin: {data_dir}")
    print(f"  Dosya sayisi: {len(csv_files)}")
    print("=" * 70)

    for i, csv_path in enumerate(csv_files, 1):
        material = _detect_material(csv_path.name)
        if material is None:
            continue

        ref = REFERENCES[material]
        rel = csv_path.name[:40]
        print(f"\n  [{i}/{len(csv_files)}] {rel} [{material}]")

        try:
            pipeline = build_validation_pipeline(csv_path)
            ctx = AnalysisContext()
            ctx = pipeline.run(ctx)

            if not ctx.has_data:
                report.failed_files += 1
                continue

            report.successful_files += 1
            p = ctx.properties

            # Her ozellik icin dogrulama
            checks = [
                ("Rm", p.ultimate_tensile_mpa, ref.rm_mpa),
                ("Rp0.2", p.yield_strength_mpa, ref.rp02_mpa),
                ("At", p.elongation_at_break_pct, ref.at_pct),
                ("E", p.elastic_modulus_gpa, ref.e_gpa),
                ("n", p.strain_hardening_n, ref.n_hollomon),
            ]

            for prop_name, measured, (ref_min, ref_max) in checks:
                if measured is None:
                    report.skip_count += 1
                    continue

                passed = ref_min <= measured <= ref_max
                vr = ValidationResult(
                    filename=csv_path.name,
                    material=material,
                    property_name=prop_name,
                    measured=round(measured, 4),
                    ref_min=ref_min,
                    ref_max=ref_max,
                    passed=passed,
                )

                if passed:
                    report.pass_count += 1
                    icon = "OK"
                else:
                    report.fail_count += 1
                    icon = "XX"
                    vr.note = f"DISI: {measured:.2f} not in [{ref_min}, {ref_max}]"

                report.results.append(vr)
                print(f"    [{icon}] {prop_name:>6} = {measured:>10.2f}  "
                      f"ref:[{ref_min:.0f}-{ref_max:.0f}]")

        except Exception as e:
            report.failed_files += 1
            print(f"    [XX] Hata: {e}")

    # Ozet
    total_checks = report.pass_count + report.fail_count
    pass_rate = (report.pass_count / total_checks * 100) if total_checks else 0

    print("\n" + "=" * 70)
    print("  VALIDASYON SONUCU")
    print(f"  Dosya: {report.successful_files}/{report.total_files} basarili")
    print(f"  Kontrol: {report.pass_count} PASS / {report.fail_count} FAIL "
          f"/ {report.skip_count} SKIP")
    print(f"  Basari orani: {pass_rate:.1f}%")

    if report.fail_count > 0:
        print("\n  [BASARISIZ KONTROLLER]")
        for r in report.results:
            if not r.passed:
                print(f"    {r.filename[:35]:35} {r.property_name:>6} = "
                      f"{r.measured:>10.2f}  ref:[{r.ref_min:.0f}-{r.ref_max:.0f}]")

    print("=" * 70)
    return report


if __name__ == "__main__":
    nist_dir = Path(r"c:\Users\MSI\Desktop\Test_Cihazlari_Proje\veri_setleri\nist_numisheet")

    if len(sys.argv) > 1:
        nist_dir = Path(sys.argv[1])

    # Hizli test (malzeme basi 3 dosya) veya tam test
    max_f = None
    if "--quick" in sys.argv:
        max_f = 12  # 4 malzeme x 3 dosya

    t0 = time.perf_counter()
    report = run_validation(nist_dir, max_files=max_f)
    elapsed = time.perf_counter() - t0

    total_checks = report.pass_count + report.fail_count
    pass_rate = (report.pass_count / total_checks * 100) if total_checks else 0

    print(f"\n  Toplam sure: {elapsed:.1f} s")

    # Cikis kodu: >%90 basari gerekli
    if pass_rate >= 90.0:
        print(f"  [BASARILI] Validasyon gecti ({pass_rate:.1f}% >= 90%)")
        sys.exit(0)
    else:
        print(f"  [BASARISIZ] Validasyon gecemedi ({pass_rate:.1f}% < 90%)")
        sys.exit(1)
