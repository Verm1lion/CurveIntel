# 🔬 CurveIntel

> **ISO 6892-1:2019 compliant tensile test analysis engine.**
> Vendor-agnostic · Deterministic · Open Source

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://python.org)
[![Docker](https://img.shields.io/badge/Docker-ready-2496ED.svg)](Dockerfile)

---

## ✨ What is CurveIntel?

CurveIntel is an **open-source post-test analysis engine** for universal testing machines (UTMs). It reads raw stress-strain CSV data from **any vendor**, computes mechanical properties per ISO 6892-1:2019, and generates ISO 17025-aligned PDF reports — all without requiring the original test machine software.

**The problem it solves:** Laboratories with mixed-vendor machine fleets (Instron + ZwickRoell + Shimadzu + ...) struggle with incompatible software ecosystems, manual Excel calculations, and audit trail gaps. CurveIntel normalizes all data into one deterministic, reproducible pipeline.

### Key Features

- 🧮 **7 Mechanical Properties** — E-modulus (OLS/RANSAC), Rp0.2, ReH/ReL, Rm, At%, Ag%, strain hardening exponent (n)
- 🔍 **5-Layer Anomaly Detection** — Grip slippage, sensor saturation, noise (SNR), curve integrity, property validation
- 🏭 **8 Vendor Profiles** — ZwickRoell, Instron, Shimadzu, MTS, Tinius Olsen, DEVOTRANS, Hegewald & Peschke, NIST
- 📊 **Batch QC & SPC** — Dixon Q10, Grubbs outlier tests, CoV, 95% CI, X-bar/R charts with Nelson 8 rules
- 📄 **ISO 17025 Reports** — PDF with graphs, anomaly tables, pipeline logs, signature placeholders, UUID traceability
- 🌐 **Web Dashboard** — FastAPI-powered UI with drag-and-drop upload
- 🐳 **Docker Ready** — Single command deployment

---

## 🚀 Quick Start

### Option 1: pip

```bash
pip install numpy scipy pandas scikit-learn matplotlib fastapi uvicorn jinja2 python-multipart reportlab

# Clone and run
git clone https://github.com/Verm1lion/CurveIntel.git
cd CurveIntel
uvicorn web.app:app --reload
# Open http://localhost:8000
```

### Option 2: Docker

```bash
git clone https://github.com/Verm1lion/CurveIntel.git
cd CurveIntel
docker compose up -d
# Open http://localhost:8000
```

### Option 3: Python API

```python
from pathlib import Path
from batch_analyze import build_pipeline, analyze_single

csv_file = Path("your_test_data.csv")
ctx = analyze_single(csv_file, Path("reports/"))

print(f"E-modulus:       {ctx.properties.elastic_modulus_gpa:.1f} GPa")
print(f"Yield (Rp0.2):   {ctx.properties.yield_strength_mpa:.1f} MPa")
print(f"UTS (Rm):        {ctx.properties.ultimate_tensile_mpa:.1f} MPa")
print(f"Elongation (At): {ctx.properties.total_elongation_pct:.1f} %")
print(f"Quality:         {ctx.properties.quality_grade}")
```

---

## 🔧 Pipeline Architecture

CurveIntel processes each CSV through a **19-step deterministic pipeline**:

```
CSV File
  ├─ Ingestion ─────────────────────────────────────────────┐
  │   → DataLoader (encoding/separator auto-detect)         │
  │   → SchemaDetector (vendor profile matching)            │
  │   → UnitConverter (kN→MPa, mm→strain)                   │
  ├─ Preprocessing ─────────────────────────────────────────┤
  │   → SpikeFilter (median filter)                         │
  │   → MonotonicityChecker (cyclic data detection)         │
  │   → ToeCompensation (toe region correction)             │
  │   → Resampler (2000 points)                             │
  │   → SavitzkyGolayFilter (noise reduction)               │
  ├─ Extraction ────────────────────────────────────────────┤
  │   → ElasticModulusDetector (OLS + RANSAC, Annex G)      │
  │   → YieldDetector (0.2% offset / ReH-ReL)              │
  │   → UTSDetector (SG-filtered max stress)                │
  │   → ElongationDetector (At / Ag, Annex A.3.6.1)        │
  │   → NeckingDetector (Considère criterion)               │
  │   → StrainHardeningFitter (Hollomon n-K, ISO 10275)     │
  │   → ToughnessCalculator (trapezoidal integration)       │
  ├─ Anomaly Detection ────────────────────────────────────┤
  │   → GripSlippageDetector                                │
  │   → SensorSaturationDetector                            │
  │   → NoiseAnalyzer (SNR)                                 │
  │   → CurveIntegrityChecker (truncation)                  │
  │   → PropertyValidator (physical consistency)            │
  └─ Reporting ─────────────────────────────────────────────┘
      → PDF Report (ISO 17025 template)
      → JSON + CSV export
```

Each step is an isolated `PipelineStep` subclass with pre/post validation — making it easy to extend, test, or replace individual components.

---

## 📋 Supported CSV Formats

| Vendor | Profile | Encoding | Separator |
|--------|---------|----------|-----------|
| ZwickRoell testXpert II/III | 25 columns (DE/EN) | CP1252 | `;` |
| Instron Bluehill Universal | 34 columns (multi-lang) | UTF-8/16 | `,` |
| Shimadzu Trapezium X | 31 columns (JP/EN) | Shift-JIS | `,` |
| MTS TestSuite | 9 columns | UTF-8 | `tab` |
| Tinius Olsen Horizon | 12 columns | CP1252 | `,` |
| DEVOTRANS CKS-III | 13 columns (TR) | CP1254 | `;` |
| Hegewald & Peschke | 14 columns (DE) | CP1252 | `;` |
| NIST Numisheet | 5 columns | UTF-8 | `,` |
| **Generic CSV** | **auto-detect** | **auto** | **auto** |

**Adding a new vendor?** See [CONTRIBUTING.md](CONTRIBUTING.md) or open a [Vendor Support Request](https://github.com/Verm1lion/CurveIntel/issues/new?template=vendor_support.yml).

---

## 📊 Quality Scoring

Every analysis receives a deterministic quality grade:

| Score | Grade | Meaning |
|-------|-------|---------|
| ≥ 85 | **A+ (Excellent)** | High reliability, directly usable |
| ≥ 70 | **A (Good)** | Reliable results |
| ≥ 55 | **B (Use with Caution)** | Some issues detected |
| ≥ 40 | **C (Low Reliability)** | Verification required |
| < 40 | **D (Unreliable)** | Should not be used |

---

## 🧪 Validation

CurveIntel has been validated against **NIST Numisheet 2020** reference datasets:

- ✅ **22/22 batch tests passed** (4 materials: DP980, DP1180, Al6xxx-T4, Al6xxx-T81)
- ✅ **472-file audit**: 208 full results + 243 cyclic (correctly detected) + 21 metadata + **0 crashes**
- ✅ Deterministic: same input → same output, every time

See [docs/validation_report.md](docs/validation_report.md) for methodology and results.

---

## 🔌 API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Web dashboard |
| `/guide` | GET | Interactive usage guide |
| `/api/health` | GET | Health check |
| `/api/analyze` | POST | Upload CSV + run analysis |
| `/api/results` | GET | List all results (JSON) |
| `/api/report/{id}/pdf` | GET | Download ISO PDF report |
| `/api/results/{id}` | DELETE | Delete single result |
| `/api/results/clear` | DELETE | Clear all results |

---

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for:

- Development setup instructions
- Code style guidelines (Ruff)
- Pull request process
- How to add new vendor profiles

**Good first issues** are labeled with [`good-first-issue`](https://github.com/Verm1lion/CurveIntel/labels/good-first-issue).

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

## ⚠️ Disclaimer

> CurveIntel is designed to support ISO/IEC 17025:2017 Clause 7.11 (Data Control and Information Management) requirements. However, it is **not** an accredited testing laboratory, does not grant accreditation, and has not been certified by any accreditation body (e.g., TÜRKAK, UKAS, A2LA).
>
> All calculation results are provided for **informational and quality assurance support purposes only**. Final responsibility for test results, material acceptance decisions, and regulatory compliance rests entirely with the laboratory operator and the qualified engineer.
