"""Manual curated batch smoke script kept import-safe for pytest."""

from __future__ import annotations

from pathlib import Path

from batch_analyze import analyze_single
from src.pipeline.reporting import export_results_csv


def main() -> None:
    """Run the manual curated batch smoke flow."""

    out_dir = Path(__file__).parent / "reports"
    out_dir.mkdir(exist_ok=True)

    summary = out_dir / "batch_summary.csv"
    if summary.exists():
        summary.unlink()

    nist_dir = Path(r"c:\Users\MSI\Desktop\Test_Cihazlari_Proje\veri_setleri\nist_numisheet")
    csv_files = sorted(nist_dir.glob("C00*-S-Stress-Strain.csv"))

    zenodo_dir = Path(
        r"c:\Users\MSI\Desktop\Test_Cihazlari_Proje\veri_setleri\Zenodo Structural Metallic DB\Clean_Data_v1-0-0\Clean_Data\S355J2_Plates\S355J2_N_25mm"
    )
    if zenodo_dir.exists():
        csv_files += sorted(zenodo_dir.glob("S_*.csv"))

    print(f"Toplam {len(csv_files)} dosya\n")

    ok = 0
    fail = 0
    for index, csv_file in enumerate(csv_files, 1):
        print(f"[{index:2}/{len(csv_files)}] {csv_file.name:55}", end=" ")
        try:
            ctx = analyze_single(csv_file, out_dir)
            if ctx and ctx.has_data:
                export_results_csv(ctx, summary)
                properties = ctx.properties
                uts = properties.ultimate_tensile_mpa
                ys = properties.yield_strength_mpa
                print(f"UTS={uts:.0f} Yield={ys:.0f}" if uts and ys else "---")
                ok += 1
            else:
                print("FAIL (no data)")
                fail += 1
        except Exception as exc:
            print(f"ERR: {exc}")
            fail += 1

    print(f"\nSonuc: {ok}/{len(csv_files)} basarili | Ozet: {summary.name}")


if __name__ == "__main__":
    main()
