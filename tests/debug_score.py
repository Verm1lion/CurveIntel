"""Quality score breakdown for demo files."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.pipeline.base import AnalysisContext, Pipeline
from src.pipeline.ingestion import DataLoader, SchemaDetector, UnitConverter
from src.pipeline.preprocessing import SpikeFilter, ToeCompensation, Resampler, SavitzkyGolayFilter, MonotonicityChecker
from src.pipeline.extraction import (
    ElasticModulusDetector, YieldDetector, UTSDetector,
    ElongationDetector, NeckingDetector, StrainHardeningFitter, ToughnessCalculator,
)
from src.pipeline.anomaly import (
    GripSlippageDetector, SensorSaturationDetector,
    NoiseAnalyzer, CurveIntegrityChecker, PropertyValidator,
)
from src.pipeline.reporting import _quality_score

BASE = Path(r"c:\Users\MSI\Desktop\Test_Cihazlari_Proje\veri_setleri\nist_numisheet")

files = [
    BASE / "C00Al6xxxT4Numisheet2020R01T1.521W17.91-S-Stress-Strain.csv",
    BASE / "C00FeDP980Numisheet2020R01T1.424W17.93-S-Stress-Strain.csv",
    BASE / "C00FeDP1180Numisheet2020R01T1.046W17.93-S-Stress-Strain.csv",
]

for fpath in files:
    pipe = Pipeline([
        DataLoader(fpath), SchemaDetector(), UnitConverter(),
        SpikeFilter(window_size=5, threshold_sigma=3.0),
        MonotonicityChecker(),
        ToeCompensation(), Resampler(n_points=2000),
        SavitzkyGolayFilter(window_length=21, polyorder=3),
        ElasticModulusDetector(), YieldDetector(), UTSDetector(),
        ElongationDetector(), NeckingDetector(),
        StrainHardeningFitter(), ToughnessCalculator(),
        GripSlippageDetector(), SensorSaturationDetector(),
        NoiseAnalyzer(), CurveIntegrityChecker(), PropertyValidator(),
    ])
    ctx = AnalysisContext()
    ctx = pipe.run(ctx)

    score, grade = _quality_score(ctx)
    
    # Breakdown
    total = len(ctx.step_results)
    success = sum(1 for r in ctx.step_results if r.status.value == "success")
    warning = sum(1 for r in ctx.step_results if r.status.value == "warning")
    failure = sum(1 for r in ctx.step_results if r.status.value == "failure")
    
    pipeline_score = (success / total) * 40 if total > 0 else 0
    
    snr = ctx.extra.get("snr_db", 0)
    snr_score = 20 if snr >= 40 else (10 if snr >= 20 else 0)
    
    warn_count = sum(1 for a in ctx.anomalies if a.severity == "warning")
    crit_count = sum(1 for a in ctx.anomalies if a.severity == "critical")
    anomaly_penalty = min(20, warn_count * 3 + crit_count * 10)
    anomaly_score = 20 - anomaly_penalty
    
    p = ctx.properties
    consistency = 20
    if p.yield_strength_mpa and p.ultimate_tensile_mpa:
        if p.yield_strength_mpa > p.ultimate_tensile_mpa:
            consistency -= 10
    if p.elastic_modulus_gpa and not (1 <= p.elastic_modulus_gpa <= 600):
        consistency -= 10
    
    print(f"\n{'='*60}")
    print(f"FILE: {fpath.name}")
    print(f"SCORE: {score:.0f}/100 — {grade}")
    print(f"{'='*60}")
    print(f"  Pipeline: {pipeline_score:.1f}/40  ({success}/{total} success, {warning} warn, {failure} fail)")
    for r in ctx.step_results:
        if r.status.value != "success":
            print(f"    [{r.status.value:7s}] {r.step_name}: {r.message[:60]}")
    print(f"  SNR:      {snr_score}/20  (SNR={snr:.1f} dB)")
    print(f"  Anomaly:  {anomaly_score}/20  ({warn_count} warn, {crit_count} crit, penalty={anomaly_penalty})")
    for a in ctx.anomalies:
        print(f"    [{a.severity:8s}] {a.anomaly_type.value}: {a.description[:60]}")
    print(f"  Consist:  {consistency}/20  (E={p.elastic_modulus_gpa}, Ys={p.yield_strength_mpa}, UTS={p.ultimate_tensile_mpa})")
    print(f"  TOTAL:    {pipeline_score + snr_score + anomaly_score + consistency:.1f}/100")
