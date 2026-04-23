# Example CSV Files

This directory contains sample CSV data for local testing and demonstration.

## Files

| File | Vendor | Material | Description |
|------|--------|----------|-------------|
| `sample_nist.csv` | NIST-style sample | DP980-style steel | Compact public-domain-inspired demo excerpt for smoke runs |

## Usage

```python
from pathlib import Path
from batch_analyze import build_pipeline, analyze_single

csv = Path("examples/sample_nist.csv")
ctx = analyze_single(csv, Path("reports/"))
print(f"Rm = {ctx.properties.ultimate_tensile_mpa:.1f} MPa")
```

## Adding New Samples

When contributing new vendor samples:

1. **Anonymize** all proprietary or client-identifying information
2. Include at least the first 100 data rows
3. Keep original encoding and separator
4. Add an entry to this README table
5. Verify the file works: `python batch_analyze.py examples/`

## Note

> All sample data in this directory is either from public domain sources (NIST)
> or synthetically reduced for repository use. No proprietary test data is included.
