# Vendor Integration Guide

## Overview

CurveIntel supports multiple test machine vendors through a **profile-based** CSV parsing system. Each vendor has a profile that defines column mappings, encoding, separators, and unit conventions.

## Currently Supported Vendors

| # | Vendor | Software | Columns | Encoding | Separator |
|---|--------|----------|---------|----------|-----------|
| 1 | ZwickRoell | testXpert II/III | 25 (DE/EN) | CP1252 | `;` |
| 2 | Instron | Bluehill Universal | 34 (multi-lang) | UTF-8/16 | `,` |
| 3 | Shimadzu | Trapezium X | 31 (JP/EN) | Shift-JIS | `,` |
| 4 | MTS | TestSuite | 9 | UTF-8 | `tab` |
| 5 | Tinius Olsen | Horizon | 12 | CP1252 | `,` |
| 6 | DEVOTRANS | CKS-III | 13 (TR) | CP1254 | `;` |
| 7 | Hegewald & Peschke | LabMaster | 14 (DE) | CP1252 | `;` |
| 8 | NIST | Numisheet 2020 | 5 | UTF-8 | `,` |

## How Vendor Detection Works

1. **DataLoader** reads the first 50 lines of the CSV with encoding auto-detection
2. **SchemaDetector** compares column headers against all registered vendor profiles
3. The profile with the highest match score wins
4. If no profile matches above threshold → **Generic CSV** fallback with auto-detection

## Adding a New Vendor Profile

### Step 1: Collect Sample Data

You need at least one complete CSV file from the target machine, including:
- All header rows (some machines have multi-line headers)
- At least 100 data rows
- Known encoding and separator

### Step 2: Create the Profile

Edit `src/pipeline/vendor_profiles.py` and add a new entry:

```python
VENDOR_PROFILES["your_vendor"] = VendorProfile(
    name="YourVendor ModelName",
    # Column name mappings (case-insensitive regex patterns)
    force_columns=["Force", "Kraft", "Load"],      # kN or N
    displacement_columns=["Displacement", "Weg"],   # mm
    stress_columns=["Stress", "Spannung"],           # MPa
    strain_columns=["Strain", "Dehnung"],            # mm/mm or %
    time_columns=["Time", "Zeit"],                   # s
    # File format
    encoding="utf-8",
    separator=",",
    decimal=".",
    skip_rows=0,           # Header rows to skip before column names
    # Units (for automatic conversion)
    force_unit="kN",       # kN, N, lbf
    displacement_unit="mm", # mm, in
    stress_unit="MPa",     # MPa, GPa, psi, ksi
    strain_unit="mm/mm",   # mm/mm, %, in/in
)
```

### Step 3: Test the Profile

```bash
# Test with your sample CSV
python -c "
from batch_analyze import analyze_single
from pathlib import Path
ctx = analyze_single(Path('your_sample.csv'), Path('reports/'))
print(f'Vendor: {ctx.vendor_detected}')
print(f'Rm = {ctx.properties.ultimate_tensile_mpa:.1f} MPa')
"
```

### Step 4: Add to Test Suite

Create a test in `tests/` that validates your vendor profile against known expected values.

### Step 5: Submit

1. Open a [Vendor Support Request](https://github.com/Verm1lion/CurveIntel/issues/new?template=vendor_support.yml) issue
2. Submit a PR with:
   - Updated `vendor_profiles.py`
   - Sample CSV in `examples/` (anonymized)
   - Test file
   - Updated vendor table in `README.md`

## Column Mapping Details

CurveIntel uses **regex-based multilingual column matching** supporting:

| Language | Force | Stress | Strain | Displacement |
|----------|-------|--------|--------|-------------|
| English | Force, Load | Stress | Strain | Displacement, Extension |
| German | Kraft | Spannung | Dehnung | Weg, Traverse |
| Japanese | 荷重 | 応力 | ひずみ | 変位 |
| Turkish | Kuvvet, Yük | Gerilme | Uzama | Deplasman |
| French | Force, Charge | Contrainte | Déformation | Déplacement |
| Spanish | Fuerza, Carga | Tensión | Deformación | Desplazamiento |

**Total: 143 column mappings across 6 languages.**

## Encoding Detection Chain

For files with unknown encoding, CurveIntel tries:

1. UTF-8 (with BOM detection)
2. UTF-16 (LE/BE)
3. Shift-JIS (Japanese machines)
4. CP1252 (Western European — Zwick, Tinius Olsen)
5. CP1254 (Turkish — DEVOTRANS)
6. Latin-1 (fallback)

## Troubleshooting

### "No vendor profile matched"

- Check if your CSV has unusual header rows (metadata before column names)
- Try setting `skip_rows` in the profile
- Verify encoding is correctly detected (open in a hex editor if needed)

### Wrong units detected

- Verify `force_unit` and `stress_unit` in the profile
- Check if the machine exports in N vs kN, or % vs mm/mm
- CurveIntel converts everything to MPa (stress) and mm/mm (strain) internally
