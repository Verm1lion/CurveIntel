"""Manual curated batch smoke script kept import-safe for pytest."""

# ruff: noqa: E402

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from batch_analyze import analyze_single
from src.curveintel.manual_data import (
    get_nist_directory,
    get_nist_reference_csv,
    get_zenodo_reference_csv,
    manual_dataset_help,
)
from src.pipeline.reporting import export_results_csv


def main() -> None:
    """Run the manual curated batch smoke flow."""

    out_dir = Path(__file__).parent / "reports"
    out_dir.mkdir(exist_ok=True)

    summary = out_dir / "batch_summary.csv"
    if summary.exists():
        summary.unlink()

    csv_files: list[Path] = []

    nist_dir = get_nist_directory()
    if nist_dir is not None:
        csv_files.extend(sorted(nist_dir.glob("C00*-S-Stress-Strain.csv")))
    else:
        nist_sample = get_nist_reference_csv()
        if nist_sample is not None:
            csv_files.append(nist_sample)

    zenodo_sample = get_zenodo_reference_csv()
    if zenodo_sample is not None:
        csv_files.append(zenodo_sample)

    csv_files = list(dict.fromkeys(csv_files))
    if not csv_files:
        print(f"[SKIP] No curated manual smoke files were found. {manual_dataset_help()}")
        return

    print(f"Total files: {len(csv_files)}\n")

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

    print(f"\nResult: {ok}/{len(csv_files)} successful | Summary: {summary.name}")


if __name__ == "__main__":
    main()
