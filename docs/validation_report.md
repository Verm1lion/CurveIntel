# CurveIntel Validation Report

## Overview

This document details the validation methodology and results for CurveIntel's calculation engine against established reference datasets.

## Reference Dataset: NIST Numisheet 2020

The primary validation uses the **NIST Numisheet Benchmark 2020** dataset, which provides reference tensile test data for interlaboratory comparison studies.

### Materials Tested

| Material | Alloy | Condition | Specimens |
|----------|-------|-----------|-----------|
| DP980 | Dual-Phase Steel | As-received | Multiple |
| DP1180 | Dual-Phase Steel | As-received | Multiple |
| Al6xxx-T4 | Aluminum 6xxx | T4 Temper | Multiple |
| Al6xxx-T81 | Aluminum 6xxx | T81 Temper | Multiple |

### Validation Methodology

1. **Input**: Raw NIST CSV files (stress-strain curves at multiple strain rates)
2. **Process**: Full CurveIntel pipeline (ingestion → preprocessing → extraction → anomaly)
3. **Compare**: CurveIntel-computed properties vs. NIST reference values
4. **Criteria**: Results must fall within NIST-reported uncertainty bands

### Results

| Batch | Material | Tests | Status | Notes |
|-------|----------|-------|--------|-------|
| Batch 1 | DP980 | 3 | ✅ PASS | All properties within tolerance |
| Batch 2 | DP980 | 3 | ✅ PASS | |
| Batch 3 | DP1180 | 3 | ✅ PASS | |
| Batch 4 | DP1180 | 3 | ✅ PASS | |
| Batch 5 | Al6xxx-T81 | 3 | ✅ PASS | |
| Batch 6 | Al6xxx-T81 | 2 | ✅ PASS | |
| Batch 7 | Al6xxx-T4 | 3 | ✅ PASS | |
| Batch 8 | Al6xxx-T4 | 2 | ✅ PASS | |
| **Total** | **4 materials** | **22** | **22/22 ✅** | **100% pass rate** |

## Full Corpus Audit: 472 Files

A comprehensive audit was performed on 472 CSV files from various sources and vendors.

### Results

| Category | Count | Percentage | Description |
|----------|-------|------------|-------------|
| **FULL_RESULT** | 208 | 44.1% | Successful monotonic analysis |
| **CYCLIC** | 243 | 51.5% | Cyclic/fatigue data correctly detected and skipped |
| **NO_DATA** | 21 | 4.4% | Metadata-only files (no stress-strain data) |
| **ERROR** | 0 | 0.0% | Zero crashes or unhandled exceptions |

### Key Findings

- **Zero crashes** across 472 diverse files
- **Cyclic detection** correctly identifies non-monotonic data (ratcheting, fatigue)
- **Vendor auto-detection** successfully matches files to correct profiles
- **Encoding handling** works across UTF-8, UTF-16, CP1252, CP1254, Shift-JIS

## Determinism

CurveIntel's pipeline is **fully deterministic**:
- Same input → same output, every run
- No random seeds, no stochastic elements in production mode
- RANSAC uses fixed `random_state=42` for reproducibility

## Limitations

1. Validation is against NIST reference data only; no independent third-party audit certificate exists
2. Cyclic/fatigue test analysis is not supported (correctly detected and rejected)
3. High-temperature and creep test standards are not currently implemented
4. Results should be verified by qualified engineers before use in production decisions

## ISO Standards Referenced

- **ISO 6892-1:2019** — Metallic materials, tensile testing, Part 1: Room temperature
- **ISO 6892-1:2019 Annex G** — Determination of modulus of elasticity
- **ISO 10275:2020** — Metallic materials, determination of strain hardening exponent
- **ISO/IEC 17025:2017** — General requirements for testing and calibration laboratories
