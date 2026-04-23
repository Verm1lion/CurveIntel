# Vendor Integration Guide

## Overview

CurveIntel uses a profile-based CSV ingestion layer. A vendor profile describes how a machine export can be recognized and how its raw columns map to CurveIntel's canonical fields.

The implementation lives in [src/pipeline/vendor_profiles.py](../src/pipeline/vendor_profiles.py).

## Runtime Model

Each profile is a `VendorProfile` dataclass with these fields:

```python
@dataclass
class VendorProfile:
    name: str
    fingerprint_regex: str
    column_map: dict[str, str]
    default_encoding: str = "utf-8"
    default_decimal: str = "."
    default_separator: str = ","
    time_column: str | None = None
    notes: str = ""
```

Canonical target columns used by the ingestion pipeline:

- `force`
- `displacement`
- `stress`
- `strain`
- `time`
- `extensometer`

## Supported Profiles

| Vendor | Profile | Encoding | Separator | Notes |
| --- | --- | --- | --- | --- |
| ZwickRoell | testXpert II/III | `windows-1252` | `;` | German and English exports |
| Instron | Bluehill Universal | `utf-8` / `utf-16` | `,` | Multi-language exports |
| Shimadzu | Trapezium X | `shift_jis` | `,` | Japanese and English headers |
| MTS | TestSuite | `utf-8` | `tab` | Axial force/displacement naming |
| Tinius Olsen | Horizon | `windows-1252` | `,` | Standard English exports |
| DEVOTRANS | CKS-III | `windows-1254` | `;` | Turkish locale |
| Hegewald & Peschke | LabMaster | `windows-1252` | `;` | German locale |
| NIST | Numisheet 2020 | `utf-8` | `,` | Reference dataset |

## Detection Flow

1. `detect_vendor(filepath, max_lines=40)` reads the first lines of the file using the encoding fallback chain.
2. Each profile's `fingerprint_regex` is scored against that header block.
3. The best-scoring profile from `ALL_PROFILES` is selected.
4. `SchemaDetector` applies the chosen profile's `column_map`.
5. If no profile matches, CurveIntel falls back to generic column auto-detection.

Encoding fallback order:

1. `utf-8-sig`
2. `utf-16`
3. `shift_jis`
4. `windows-1252`
5. `windows-1254`
6. `latin-1`

## Adding a New Vendor Profile

1. Collect at least one representative export file with full headers and enough data rows to validate the mapping.
2. Add a new `VendorProfile` constant in `src/pipeline/vendor_profiles.py`.
3. Add the profile to `ALL_PROFILES`.

Recommended insertion rule:

- Put more specific formats before more generic ones.
- Keep profile order deterministic because detection picks the highest-scoring match from that ordered set.

Example:

```python
MY_VENDOR = VendorProfile(
    name="My Vendor Suite",
    fingerprint_regex=r"(?i)(?:MyVendor|MyVendorSuite|Specimen Name)",
    column_map={
        "Load": "force",
        "Extension": "displacement",
        "Stress": "stress",
        "Strain": "strain",
        "Time": "time",
    },
    default_encoding="utf-8",
    default_decimal=".",
    default_separator=",",
    time_column="Time",
    notes="Example profile.",
)

ALL_PROFILES.insert(0, MY_VENDOR)
```

4. Validate the profile against a known sample file.

```bash
python -c "from pathlib import Path; from src.pipeline.vendor_profiles import detect_vendor; print(detect_vendor(Path('sample.csv')).name)"
```

5. Add or extend automated coverage in `tests/` for the new format.
6. Update the vendor tables in this guide and in `README.md`.

## Troubleshooting

### No profile matched

- Inspect the first 40 header lines of the export file.
- Check whether the file uses an unexpected encoding or separator.
- Confirm the export includes stable header text that can be fingerprinted.
- Verify that generic fallback still identifies canonical columns.

### Wrong columns were mapped

- Review `column_map` for locale variants and spelling changes.
- Add aliases rather than replacing existing ones when supporting new export variants.
- Make sure the target values remain canonical keys such as `force` or `strain`.

### Wrong decimal or separator behavior

- Set `default_decimal` and `default_separator` to match the vendor export.
- Keep locale-specific defaults inside the vendor profile rather than in the generic detector.

### Encoding issues

- Prefer the narrowest known encoding for the vendor.
- If the vendor exports multiple encodings, keep the broadest safe default in the profile and rely on the fallback chain for alternate variants.

## Related Files

- [src/pipeline/vendor_profiles.py](../src/pipeline/vendor_profiles.py)
- [src/pipeline/ingestion.py](../src/pipeline/ingestion.py)
- [README.md](../README.md)
