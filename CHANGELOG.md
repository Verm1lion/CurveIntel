# Changelog

All notable changes to CurveIntel will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-04-18

### Added
- **Core Pipeline:** 19-step analysis pipeline (ingestion -> extraction -> anomaly -> reporting)
- **Elastic Modulus (E):** OLS + RANSAC, ISO 6892-1 Annex G
- **Yield Detection:** Rp0.2 offset + ReH/ReL discontinuous yield (ISO A.3.2)
- **UTS Detection:** SG-filtered max stress, dual storage
- **Elongation:** Force-drop fracture detection (Annex A.3.6.1)
- **Strain Hardening:** Hollomon power law (ISO 10275)
- **Toughness:** Trapezoidal integration
- **Anomaly Detection:** Grip slippage, sensor saturation, noise, curve integrity, property validation
- **Batch QC (FAZ 9):** Dixon Q10 (n<=7), Grubbs (n>=8), CoV, 95% CI, overlay + box-whisker plots
- **SPC (FAZ 9.5):** X-bar/R chart, Nelson 8 rules, sigma zone coloring
- **Strain Rate Validation (FAZ 8.5):** ISO 6892-1 Table B.1, report code generation
- **ISO 17025 Legal Framework (FAZ 8):** Cl. 7.8.2.1 mandatory fields, safe disclaimers, signature placeholders
- **Multi-Vendor Ingestion (FAZ 10):** 8 vendor profiles (ZwickRoell, Instron, Shimadzu, MTS, Tinius Olsen, DEVOTRANS, Hegewald, NIST)
- **Locale-Aware Parsing:** Encoding chain (UTF-8/16, Shift-JIS, CP1252/1254), decimal/separator auto-detection
- **Multilingual Column Mapping:** DE, EN, JP, TR, FR, ES support (143 total mappings)
- **Validation Suite (FAZ 11.1):** NIST Numisheet 2020 regression test (96 files, 4 materials, 100% pass rate)
- **Algorithm Specification (FAZ 11.2):** Full documentation with ISO references
- **PDF Reports:** ISO 17025 compliant, UUID tracking, method tags
- **JSON/CSV Export:** Machine-readable output
- **Web Dashboard:** Streamlit-based UI with drag-and-drop upload

### Security
- No "ISO 17025 certified" claims (TURKAK R10-06 compliance)
- Approved legal disclaimer text (TR/EN)
- Report UUID traceability (CI-XXXXXX format)

## [Unreleased]
- Vector BTC TESLA CSV profile
- Docker deployment (FAZ 12)
- Turkish UI localization (FAZ 12)
- PTB TraCIM integration (future)
