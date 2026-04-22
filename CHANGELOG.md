# Changelog

All notable changes to CurveIntel will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2026-04-22

### Changed
- **Open Source Release:** Project relicensed from Proprietary to MIT License
- **README:** Complete rewrite in English with badges, pipeline diagram, validation results
- **pyproject.toml:** Updated to v2.0.0 with proper classifiers, URLs, and MIT license

### Added
- **LICENSE** — MIT License
- **CONTRIBUTING.md** — Development setup, code style, PR process, vendor integration guide
- **CODE_OF_CONDUCT.md** — Contributor Covenant v2.1
- **SECURITY.md** — Vulnerability reporting policy
- **GitHub Templates** — Bug report, feature request, vendor support, PR template
- **examples/** — Sample CSV data directory

### Removed
- Debug scripts (`debug_score.py`, `debug_worst.py`, `diag_summary.py`)
- Internal planning documents (`docs/PROJE_PLANI.md`)
- Generated reports and uploads artifacts
- All `__pycache__/` directories

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

## [1.2.0] - 2026-04-19

### Added
- **Guide Page:** Kapsamli, animasyonlu rehber sayfasi (Hero, Neden CurveIntel, Nasil Kullanilir, Metrik Sozlugu, Kalite Skor Tablosu, Pipeline Timeline, SSS).
- **Dashboard Navbar:** Guide sayfasina gecis linki eklendi.
- **Material Detection:** Dosya isimlendirme formatlarindan malzeme turu (DP Celik, Aluminyum, Yapisal Celik vb.) Regex ile otomatik tespit ve PDF'e yanismasi eklendi.

### Fixed
- **PDF ISO Method:** Mekanik ozellikler tablosundaki "ISO Yontem / Method" sutununda yasanan metin tasmasi duzeltildi.
- **PDF Pipeline Log:** Pipeline loglarinda ve anomali tablosunda yasanan Turkce karakter bozulmasi Helvetica uyumu icin sanitize isleminden gecirildi.

## [1.1.0] - 2026-04-19

### Added
- **MonotonicityChecker:** Running-maximum drop algorithm ile siklik/cyclic veri tespiti
  - %1 strain range threshold, >=5 reversal → cyclic flag
  - SpikeFilter sonrasi, ToeCompensation oncesi calisir (ham veri uzerinde)
- **Extraction Guards:** 7 detector'a `is_cyclic` guard eklendi — siklik veride saçma property hesabi engellendi
- **NON_MONOTONIC anomaly type:** AnomalyType enum'a eklendi
- **Per-file PDF download:** Batch Results tablosundaki her satira PDF indirme butonu eklendi
- **Cyclic warning banner:** Dashboard'da siklik veri uyarisi gosteriliyor
- **Upload guard:** `-attributes.csv` metadata dosyalari client-side reddediliyor

### Changed
- **PDF rapor:** API endpoint artik `reporting.py`'deki profesyonel 3 sayfalik ISO raporunu kullaniyor
  (grafik + anomali tablosu + pipeline log + imza alani + yasal not)
- **Kalite skoru esikleri:** 5 kademeli sisteme gecildi:
  - A+ (>=85, Mukemmel), A (>=70, Iyi), B (>=55, Dikkatle Kullanilabilir), C (>=40, Dusuk), D (<40, Guvenilmez)

### Fixed
- PDF endpoint basit tek sayfalik ozet uretiyor, `generate_pdf_report()` hic cagrilmiyordu
- Navbar'daki belirsiz "Download PDF" butonu kaldirildi (birden fazla dosyada hangi dosya belli degildi)

### Removed
- Navbar'daki global "Download PDF" butonu (per-file buton ile degistirildi)

### Validation
- **472 dosya audit:** 208 FULL_RESULT + 243 CYCLIC + 21 NO_DATA + 0 ERROR
- Siklik dosyalarda UTS=34786 MPa gibi sacma sonuclar artik uretilmiyor

## [Unreleased]
- Vector BTC TESLA CSV profile
- Docker deployment (FAZ 12)
- Turkish UI localization (FAZ 12)
- PTB TraCIM integration (future)
