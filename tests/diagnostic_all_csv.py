"""
CurveIntel - Tam Veri Seti Teşhis Scripti
Tüm CSV dosyalarını pipeline'dan geçirip durumlarını raporlar.
"""
import sys, os, time, csv
from pathlib import Path

# Proje root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.pipeline.base import Pipeline, AnalysisContext
from src.pipeline.ingestion import DataLoader, SchemaDetector, UnitConverter
from src.pipeline.preprocessing import SpikeFilter, ToeCompensation, Resampler, SavitzkyGolayFilter, MonotonicityChecker
from src.pipeline.extraction import (
    ElasticModulusDetector, YieldDetector, UTSDetector,
    ElongationDetector, NeckingDetector, StrainHardeningFitter, ToughnessCalculator,
    StrainRateValidator,
)
from src.pipeline.anomaly import (
    GripSlippageDetector, SensorSaturationDetector,
    NoiseAnalyzer, CurveIntegrityChecker, PropertyValidator,
)


def build_pipeline(csv_path: Path) -> Pipeline:
    return Pipeline([
        DataLoader(csv_path),
        SchemaDetector(),
        UnitConverter(),
        SpikeFilter(window_size=5, threshold_sigma=3.0),
        MonotonicityChecker(),
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


def analyze_file(csv_path: Path) -> dict:
    """Tek dosyayı analiz et, sonuçları dict olarak döndür."""
    result = {
        "file": csv_path.name,
        "dir": csv_path.parent.name,
        "rel_path": str(csv_path.relative_to(DATASET_ROOT)),
        "size_kb": round(csv_path.stat().st_size / 1024, 1),
        "status": "UNKNOWN",
        "n_points": 0,
        "has_data": False,
        "E_gpa": None,
        "yield_mpa": None,
        "uts_mpa": None,
        "elongation_pct": None,
        "score": None,
        "grade": None,
        "errors": [],
        "warnings": [],
        "duration_ms": 0,
        "fail_reason": None,
    }

    try:
        # İlk 3 satırı oku - dosya formatını anla
        with open(csv_path, "r", errors="replace") as f:
            head = [f.readline().strip() for _ in range(3)]
        result["head_preview"] = " | ".join(head[:2])[:100]

        t0 = time.perf_counter()
        pipeline = build_pipeline(csv_path)
        ctx = AnalysisContext()
        ctx = pipeline.run(ctx)
        dt = (time.perf_counter() - t0) * 1000
        result["duration_ms"] = round(dt, 1)

        result["has_data"] = ctx.has_data
        result["n_points"] = ctx.n_points

        if not ctx.has_data or ctx.n_points == 0:
            result["status"] = "NO_DATA"
            result["fail_reason"] = "Pipeline ran but no stress-strain data extracted"
            return result

        p = ctx.properties
        result["E_gpa"] = round(p.elastic_modulus_gpa, 1) if p.elastic_modulus_gpa else None
        result["yield_mpa"] = round(p.yield_strength_mpa, 1) if p.yield_strength_mpa else None
        result["uts_mpa"] = round(p.ultimate_tensile_mpa, 1) if p.ultimate_tensile_mpa else None
        result["elongation_pct"] = round(p.elongation_at_break_pct, 1) if p.elongation_at_break_pct else None

        # Quality score
        from src.pipeline.reporting import _quality_score
        score, grade = _quality_score(ctx)
        result["score"] = round(score, 0)
        result["grade"] = grade

        # Hangi property'ler eksik?
        missing = []
        if not p.elastic_modulus_gpa: missing.append("E")
        if not p.yield_strength_mpa: missing.append("Yield")
        if not p.ultimate_tensile_mpa: missing.append("UTS")
        if not p.elongation_at_break_pct: missing.append("Elong")
        result["missing_props"] = missing

        # Anomaliler
        for a in ctx.anomalies:
            if a.severity in ("warning", "critical"):
                result["warnings"].append(f"{a.anomaly_type.value}: {a.description[:60]}")

        # Step hataları
        for r in ctx.step_results:
            if r.status.value == "failure":
                result["errors"].append(f"{r.step_name}: {r.message[:60]}")

        # Durumu belirle
        is_cyclic = ctx.extra.get("is_cyclic", False)
        result["is_cyclic"] = is_cyclic

        if is_cyclic:
            result["status"] = "CYCLIC"
            result["fail_reason"] = f"Cyclic data ({ctx.extra.get('strain_reversals', 0)} reversals)"
        elif result["uts_mpa"] and result["uts_mpa"] > 0:
            if len(missing) <= 1:
                result["status"] = "FULL_RESULT"
            else:
                result["status"] = "PARTIAL_RESULT"
        elif result["n_points"] > 0:
            result["status"] = "DATA_ONLY"  # Veri var ama property yok
        else:
            result["status"] = "NO_DATA"

    except Exception as e:
        result["status"] = "ERROR"
        result["fail_reason"] = f"{type(e).__name__}: {str(e)[:100]}"

    return result


# ── Main ──
DATASET_ROOT = Path(r"c:\Users\MSI\Desktop\Test_Cihazlari_Proje\veri_setleri")
OUTPUT_CSV = Path(__file__).parent / "diagnostic_results.csv"

if __name__ == "__main__":
    csv_files = sorted(DATASET_ROOT.rglob("*.csv"))
    print(f"[DIAGNOSTIC] {len(csv_files)} CSV dosyasi bulundu\n")

    results = []
    status_counts = {"FULL_RESULT": 0, "PARTIAL_RESULT": 0, "DATA_ONLY": 0, "CYCLIC": 0, "NO_DATA": 0, "ERROR": 0}

    for i, f in enumerate(csv_files, 1):
        r = analyze_file(f)
        results.append(r)
        status_counts[r["status"]] = status_counts.get(r["status"], 0) + 1

        # Progress
        icon = {"FULL_RESULT": "[OK]", "PARTIAL_RESULT": "[PT]", "DATA_ONLY": "[DO]", "CYCLIC": "[CY]", "NO_DATA": "[ND]", "ERROR": "[ER]"}.get(r["status"], "[??]")
        props = f"E={r['E_gpa']} Ys={r['yield_mpa']} UTS={r['uts_mpa']}" if r["uts_mpa"] else (r["fail_reason"] or "no props")[:50]
        print(f"  [{i:3d}/{len(csv_files)}] {icon} {r['dir']}/{r['file'][:50]:50s} | {r['status']:15s} | {props}")

    # Özet
    print(f"\n{'='*80}")
    print(f"SONUÇLAR ({len(csv_files)} dosya)")
    print(f"{'='*80}")
    for status, count in sorted(status_counts.items()):
        pct = count / len(csv_files) * 100
        bar = "█" * int(pct / 2) + "░" * (50 - int(pct / 2))
        print(f"  {status:20s} {count:4d} ({pct:5.1f}%) {bar}")

    # Fail nedenleri
    print(f"\n{'='*80}")
    print("BAŞARISIZ DOSYALAR (NO_DATA + ERROR)")
    print(f"{'='*80}")
    fails = [r for r in results if r["status"] in ("NO_DATA", "ERROR")]
    if fails:
        # Grup: neden
        reasons = {}
        for r in fails:
            reason = r.get("fail_reason", "unknown") or "no stress-strain columns"
            reasons.setdefault(reason[:60], []).append(r["file"])
        for reason, files in sorted(reasons.items(), key=lambda x: -len(x[1])):
            print(f"\n  [{len(files)} dosya] {reason}")
            for fn in files[:5]:
                print(f"    - {fn}")
            if len(files) > 5:
                print(f"    ... ve {len(files)-5} dosya daha")

    # CSV export
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "status", "is_cyclic", "dir", "file", "n_points", "E_gpa", "yield_mpa", "uts_mpa",
            "elongation_pct", "score", "grade", "duration_ms", "fail_reason",
            "missing_props", "warnings", "errors", "size_kb", "rel_path"
        ])
        writer.writeheader()
        for r in results:
            row = dict(r)
            row["missing_props"] = ",".join(r.get("missing_props", []))
            row["warnings"] = " | ".join(r.get("warnings", []))
            row["errors"] = " | ".join(r.get("errors", []))
            row.pop("has_data", None)
            row.pop("head_preview", None)
            writer.writerow(row)

    print(f"\n[OUTPUT] Detaylı sonuçlar: {OUTPUT_CSV}")
