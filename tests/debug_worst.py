"""Debug LP cyclic files - reordered pipeline."""
import sys, numpy as np
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.pipeline.base import AnalysisContext, Pipeline
from src.pipeline.ingestion import DataLoader, SchemaDetector, UnitConverter
from src.pipeline.preprocessing import SpikeFilter, ToeCompensation, Resampler, SavitzkyGolayFilter, MonotonicityChecker

BASE = Path(r"c:\Users\MSI\Desktop\Test_Cihazlari_Proje\veri_setleri")

test_files = [
    (BASE / "nist_numisheet" / "C00FeDP980Numisheet2020R01T1.424W17.93-S-Stress-Strain.csv", "GOOD monotonic"),
    (BASE / "Zenodo Structural Metallic DB" / "Clean_Data_v1-0-0" / "Clean_Data" / "Fe-SMA" / "Fe-SMA_Cyclic-Calib" / "LP5_Specimen_1_processed_data.csv", "FeSMA LP5 Cyclic"),
]

for fpath, label in test_files:
    if not fpath.exists():
        print(f"[SKIP] {label} - not found")
        continue

    # Pipeline with MonotonicityChecker BEFORE toe/resample
    pipe = Pipeline([
        DataLoader(fpath), SchemaDetector(), UnitConverter(),
        SpikeFilter(window_size=5, threshold_sigma=3.0),
        MonotonicityChecker(),  # NOW BEFORE Resampler!
        ToeCompensation(), Resampler(n_points=2000),
        SavitzkyGolayFilter(window_length=21, polyorder=3),
    ])

    ctx = AnalysisContext()
    ctx = pipe.run(ctx)

    print(f"\n--- {label} ---")
    print(f"  has_data={ctx.has_data}, n_points={ctx.n_points}")
    print(f"  is_cyclic={ctx.extra.get('is_cyclic')}, reversals={ctx.extra.get('strain_reversals')}")

    for sr in ctx.step_results:
        if sr.step_name == "MonotonicityChecker":
            print(f"  MonotonicityChecker: {sr.status.value} - {sr.message}")
