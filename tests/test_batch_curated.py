"""Curated batch test — sadece stress-strain formatindaki dosyalar."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from batch_analyze import analyze_single
from src.pipeline.reporting import export_results_csv

out_dir = Path(__file__).parent / "reports"
out_dir.mkdir(exist_ok=True)

# Ozet CSV'yi sifirla
summary = out_dir / "batch_summary.csv"
if summary.exists():
    summary.unlink()

# NIST C00 serisi
nist = Path(r"c:\Users\MSI\Desktop\Test_Cihazlari_Proje\veri_setleri\nist_numisheet")
csv_files = sorted(nist.glob("C00*-S-Stress-Strain.csv"))

# Zenodo S355
zenodo = Path(r"c:\Users\MSI\Desktop\Test_Cihazlari_Proje\veri_setleri\Zenodo Structural Metallic DB\Clean_Data_v1-0-0\Clean_Data\S355J2_Plates\S355J2_N_25mm")
if zenodo.exists():
    csv_files += sorted(zenodo.glob("S_*.csv"))

print(f"Toplam {len(csv_files)} dosya\n")

ok = fail = 0
for i, f in enumerate(csv_files, 1):
    print(f"[{i:2}/{len(csv_files)}] {f.name:55}", end=" ")
    try:
        ctx = analyze_single(f, out_dir)
        if ctx and ctx.has_data:
            export_results_csv(ctx, summary)
            p = ctx.properties
            uts = p.ultimate_tensile_mpa
            ys = p.yield_strength_mpa
            print(f"UTS={uts:.0f} Yield={ys:.0f}" if uts and ys else "---")
            ok += 1
        else:
            print("FAIL (no data)")
            fail += 1
    except Exception as e:
        print(f"ERR: {e}")
        fail += 1

print(f"\nSonuc: {ok}/{len(csv_files)} basarili | Ozet: {summary.name}")
