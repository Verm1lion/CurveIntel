# Example CSV Files

This directory contains sample CSV data for local testing and demonstration.

## Files

| File | Vendor | Material | Description |
|------|--------|----------|-------------|
| `sample_nist.csv` | NIST-style sample | DP980-style steel | Compact public-domain-inspired demo excerpt for smoke runs |
| `C00Al6xxxT4Numisheet2020R01T1.521W17.91-S-Stress-Strain.csv` | NIST Numisheet 2020 | AA6xxx-T4 aluminum | Full public stress-strain curve for realistic browser upload demos |

## Usage

```python
from pathlib import Path
from batch_analyze import build_pipeline, analyze_single

csv = Path("examples/sample_nist.csv")
ctx = analyze_single(csv, Path("reports/"))
print(f"Rm = {ctx.properties.ultimate_tensile_mpa:.1f} MPa")
```

For a browser smoke test, start the app, sign in as an admin or analyst, upload:

```text
examples/C00Al6xxxT4Numisheet2020R01T1.521W17.91-S-Stress-Strain.csv
```

The upload should produce a persisted result, dashboard summary, audit entry, and downloadable PDF report. Do not upload the matching `-attributes.csv` metadata file by itself; it describes column names and units but does not contain stress-strain measurements.

## Provenance

The full NIST example comes from the NIST Public Data Repository dataset "Data for Numisheet 2020 uniaxial tensile and tension/compression tests" (`ark:/88434/mds2-2202`, DOI `10.18434/M32202`). NIST's public data licensing statement is available at <https://www.nist.gov/open/license>.

## Adding New Samples

When contributing new vendor samples:

1. **Anonymize** all proprietary or client-identifying information
2. Include at least the first 100 data rows
3. Keep original encoding and separator
4. Add an entry to this README table
5. Verify the file works: `python batch_analyze.py examples/`

## Note

> Sample data in this directory is either sourced from NIST public data or
> synthetically reduced for repository use. No proprietary test data is included.
