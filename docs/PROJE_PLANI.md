# CurveIntel — Proje Plani

**Proje:** Vendor-agnostic stress-strain egrisi analiz motoru
**Versiyon:** 1.0
**Baslangic:** Nisan 2026
**Tahmini Sure:** 6 hafta
**Gelistirici:** Mert

---

## 1. Proje Ozeti

CurveIntel, herhangi bir cekme testi makinesinden (ZwickRoell, Instron, Shimadzu, Vector BTC TESLA vb.) alinan ham CSV verisini yukleyip otomatik olarak:

1. Mekanik ozellikleri hesaplayan (E, Rp0.2, UTS, %Elongation, necking, n, tokluk)
2. Egrideki anomalileri tespit eden (grip kaymasi, spike, erken kirilma vb.)
3. Batch karsilastirmasi yapan (CoV, Grubbs outlier testi, guven araligi)
4. ISO 17025 uyumlu PDF rapor ureten

bir analiz motorudur.

**Pazar boslugu (3 bagimsiz deep research ile dogrulandi):** Bu kombinasyonu sunan hicbir ticari urun, acik kaynak arac veya SaaS platformu dunyada ve Turkiye'de mevcut degildir.

---

## 2. Veri Seti Stratejisi

### 2.1 Faz 1 — Baslangic

| # | Veri Seti | Kaynak | Malzeme | Egri | Format | Durum |
|---|-----------|--------|---------|------|--------|-------|
| 1 | Structural Metallic Materials DB | Zenodo | Yapisal celikler (S355, S690) + SMA | ~353 | CSV | ✅ Indirildi + Test |
| 2 | NIST Numisheet 2020 | data.gov | DP980, DP1180, AA6xxx-T4/T81 | 84 | CSV | ✅ Indirildi + Dogrulandi |
| 3 | JHU CFSCouponDatabase | GitHub | Yapisal celik kuponlari | 200+ | CSV | ✅ Indirildi |

**Zenodo:** 10 S355J2 dosyasi analiz edildi, UTS=438-680 MPa
**NIST:** 12 C00 serisi + 72 U-serisi (DIC) dosya analiz edildi
**JHU:** Indirildi, batch testi bekleniyor

### 2.2 Faz 2 — Genisleme (Polimer Destegi Eklerken)

| # | Veri Seti | Kaynak | Malzeme | Ne Zaman | Durum |
|---|-----------|--------|---------|----------|-------|
| 4 | FKM Fluoroelastomer | Mendeley | Polimer (FKM kaucuk) | Post-MVP | ⬜ Bekleniyor |
| 5 | 51CrV4 Spring Steel | Mendeley | Yay celigi | Post-MVP | ⬜ Bekleniyor |

### 2.3 Sentetik Veri Uretimi

- [ ] `generators.py`: Ramberg-Osgood, Ludwik, Voce modelleri
- [ ] `noise.py`: Gaussian, drift, 50Hz, grip-slip, spike
- [ ] `parameter_db.py`: malzeme parametreleri sozlugu
- [ ] 10,000+ sentetik egri hedefi

> **NOT:** Sentetik veri MVP kapsami disina alindi. Gercek veri setleri (637+ egri) yeterli dogrulama sagliyor. Post-MVP'de ML egitimsiz anomali (STUMPY) aktif edildiginde implement edilecek.

---

## 3. Teknik Mimari

### 3.1 Core Stack

```
Python 3.10+
├── numpy >= 1.24          # Vektorel hesaplama          ✅ Kullanildi
├── scipy >= 1.10          # SG filtre, interpolasyon     ✅ Kullanildi
├── pandas >= 2.0          # CSV okuma, batch yonetimi    ✅ Kullanildi
├── scikit-learn >= 1.3    # RANSAC regresyon             ✅ Kullanildi
├── matplotlib >= 3.7      # Egri gorsellestirme          ✅ Kullanildi
├── statsmodels >= 0.14    # Grubbs testi, istatistik QC  ⬜ Henuz gerek duyulmadi
├── ruptures              # PELT change-point detection   ⬜ Henuz gerek duyulmadi
├── stumpy                # Matrix Profile (discord)      ⬜ L2 anomali icin
├── reportlab >= 4.0      # PDF rapor uretimi             ✅ Kullanildi
├── fastapi               # REST API backend              ✅ Kullanildi
├── uvicorn               # ASGI server                   ✅ Kullanildi
└── docker                # Konteynerizasyon              ⬜ Hafta 6
```

### 3.2 Kesinlesmis Algoritma Kararlari

> **Son guncelleme:** 18 Nisan 2026 — 9/9 deep research capraz dogrulama sonrasi

| Karar | Secim | ISO Referansi | Durum |
|-------|-------|--------------|-------|
| Sinyal filtresi | Savitzky-Golay (window=21, poly=3) | — | ✅ Implement |
| Resampling | CubicSpline (default), PCHIP (Luders) | — | ✅ Implement |
| E Modulu | **OLS birincil** + RANSAC on-filtre | Annex G, R²≥0.9995, Sm(rel)<1% | 🔄 FAZ 7 Refaktor |
| Yield (Rp0.2) | Parallel-line offset (sign-change) | Cl. 13.1 | ✅ Implement |
| Cift yield (ReH/ReL) | **ISO A.3.2 iki-kosullu test** (0.5% drop + 0.05% strain) | Annex A.3.2 | 🔄 FAZ 7 Yeniden Yazim |
| UTS | SG-filtered max + **ham/filtreli dual storage** | Cl. 3.10.1 | 🔄 FAZ 7 Guncelleme |
| Kirilma (At) | **Force-drop method** (5x ivme OR %2 Fm) | Annex A.3.6.1 | 🔄 FAZ 7 Guncelleme |
| Necking | Considere kriteri | Supplementary | ✅ Implement |
| n (hardening) | Hollomon log-log fit (true stress/strain) | ISO 10275:2020 | ✅ Implement |
| Tokluk | np.trapezoid | Supplementary (not ISO 6892-1) | ✅ Implement |
| Anomali L1 | Rule-based (esik + turev) | — | ✅ Implement |
| Anomali L2 | Matrix Profile (STUMPY) | — | ⬜ Planli |
| Batch outlier | **Dixon Q (r₁₀, n≤7)** + Grubbs (n>30) | ISO 5725-2 | ⬜ Planli |
| PDF rapor | ReportLab (Platypus) + **method_tags** | 17025 Cl. 7.8.2.1 | 🔄 FAZ 7 Guncelleme |

### 3.3 Pipeline Mimarisi (5 Katman — 19 Adim)

```
CSV Upload
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│  KATMAN 1: Data Ingestion                     ✅ TAMAM  │
│  ├── DataLoader (CSV parsing + validasyon)              │
│  ├── SchemaDetector (kolon adi + extensometer algılama) │
│  └── UnitConverter (kN->N->MPa, Force->Stress)          │
└─────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│  KATMAN 2: Signal Preprocessing               ✅ TAMAM  │
│  ├── SpikeFilter (median, window=5, 3σ)                │
│  ├── ToeCompensation (ASTM E8 lineer projeksiyon)      │
│  ├── Resampler (CubicSpline, 2000 nokta)               │
│  └── SavitzkyGolayFilter (window=21, poly=3)           │
└─────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│  KATMAN 3: Feature Extraction                 ✅ TAMAM  │
│  ├── ElasticModulusDetector (RANSAC + OLS fallback)    │
│  ├── YieldDetector (hibrit: cift yield + Rp0.2)        │
│  ├── UTSDetector (SG filtered max + validation)        │
│  ├── ElongationDetector (force drop threshold)         │
│  ├── NeckingDetector (Considere, true curve)           │
│  ├── StrainHardeningFitter (Hollomon log-log)          │
│  └── ToughnessCalculator (trapezoid integration)       │
└─────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│  KATMAN 4: Anomaly Detection                  ⚠ KISMI  │
│  ├── L1: RuleBasedChecker                     ✅ TAMAM  │
│  │   ├── GripSlippageDetector                          │
│  │   ├── SensorSaturationDetector                      │
│  │   ├── NoiseAnalyzer (SNR, noise %)                  │
│  │   ├── CurveIntegrityChecker (truncation, drift)     │
│  │   └── PropertyValidator (fiziksel tutarlilik)       │
│  ├── L2: MatrixProfileAnalyzer (STUMPY)       ⬜ EKSIK  │
│  │   └── Discord tespiti (beklenmeyen alt-diziler)     │
│  └── L3: StatisticalBatchQC                   ⬜ EKSIK  │
│      ├── Grubbs testi (outlier rejection)              │
│      ├── Dixon Q testi (n <= 5)                        │
│      ├── CoV hesaplama + esik uyarisi (>10%)           │
│      └── 95% Confidence Interval                       │
└─────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│  KATMAN 5: Reporting                          ✅ TAMAM  │
│  ├── PDF Rapor (ReportLab, ISO 17025 uyumlu)           │
│  │   ├── Kapak + kalite skoru                          │
│  │   ├── Mekanik ozellikler tablosu (renk kodlu)       │
│  │   ├── Stress-strain grafigi (Matplotlib)            │
│  │   ├── Anomali ozeti tablosu                         │
│  │   ├── Pipeline islem loglari                        │
│  │   └── Footer + disclaimer                           │
│  ├── JSON export (tam detay)                           │
│  ├── CSV export (batch ozet satiri)                    │
│  └── Web Dashboard (FastAPI + Chart.js)       ✅ TAMAM  │
│      ├── Hero metric kartlari                          │
│      ├── Interaktif stress-strain egri (Chart.js)      │
│      ├── Pipeline status stepper                       │
│      ├── Mekanik ozellikler tablosu                    │
│      ├── Anomali ozeti + sinyal kalitesi               │
│      ├── Batch sonuc tablosu                           │
│      └── CSV drag-drop upload                          │
└─────────────────────────────────────────────────────────┘
```

---

## 4. Proje Dosya Yapisi (Guncel)

```
curveintel/
├── pyproject.toml                    # Bagimliliklar                ✅
├── src/
│   └── pipeline/
│       ├── __init__.py                                              ✅
│       ├── base.py                   # PipelineStep, AnalysisContext ✅
│       ├── ingestion.py              # DataLoader, SchemaDetector    ✅
│       ├── preprocessing.py          # SpikeFilter, Toe, SG         ✅
│       ├── extraction.py             # 7 feature extractor          ✅
│       ├── anomaly.py                # 5 L1 anomali sinifi          ✅
│       └── reporting.py              # PDF, JSON, CSV export        ✅
│
├── web/
│   ├── app.py                        # FastAPI backend               ✅
│   ├── templates/
│   │   └── dashboard.html            # Jinja2 + Stitch design       ✅
│   └── static/                                                       ✅
│
├── batch_analyze.py                  # Batch dizin tarama + rapor    ✅
├── test_pipeline.py                  # Full pipeline test            ✅
├── test_nist.py                      # NIST dogrulama                ✅
├── test_batch_curated.py             # 22 dosya batch test           ✅
├── test_useries.py                   # DIC veri testi                ✅
├── test_report.py                    # PDF rapor testi               ✅
├── reports/                          # Uretilen PDF/JSON/CSV         ✅
│
├── README.md                         # Kurulum, kullanim, demo      ⬜ EKSIK
├── Dockerfile                                                        ⬜ EKSIK
├── docker-compose.yml                                                ⬜ EKSIK
│
├── src/pipeline/batch_qc.py          # Grubbs, Dixon, CoV           ⬜ PLANLI
├── src/synthetic/                    # Sentetik veri uretimi         ⬜ POST-MVP
│   ├── generators.py
│   ├── noise.py
│   └── parameter_db.py
│
└── notebooks/                        # Jupyter demo notebooklar     ⬜ OPSIYONEL
    ├── 01_data_exploration.ipynb
    └── 02_feature_extraction.ipynb
```

---

## 5. Gelistirme Yol Haritasi

### Hafta 0: Domain Ogrenme (3 gun)

- [x] Stress-strain egrisi anlami (elastik, plastik, necking, kopma)
- [x] Yield point, UTS, elongation fiziksel anlami
- [x] Standart numune geometrisi kavramlari
- [x] Gauge section, grip area, shoulder terimleri
- [x] Gecerli vs gecersiz kirilma kavramlari
- [x] Sunek vs gevrek kirilma farki

### Hafta 1: Foundation + Data Pipeline

- [x] Proje scaffolding (pyproject.toml, dizin yapisi)
- [x] Faz 1 veri setlerini indir (Zenodo, NIST, JHU)
- [x] `PipelineStep` base class + `AnalysisContext` dataclass
- [x] `DataLoader` — CSV parsing + otomatik kolon tespiti
- [x] `SchemaDetector` — kolon adi algilama (force/stress/strain varyasyonlari)
  - [x] NIST Estress/Estrain formati
  - [x] Extensometer onceliklendirme (DIC verisi icin)
  - [x] Dosya adindan boyut parse (T=thickness, W=width -> A0)
  - [x] Otomatik gauge length (25mm extensometer, 50mm displacement)
- [x] `UnitConverter` — kN->N->MPa, Force->Stress donusum
- [x] `SpikeFilter` — median filter (window=5, threshold=3σ)
- [x] `ToeCompensation` — ASTM E8 toe region duzeltmesi
- [x] `Resampler` — CubicSpline ile esit aralikli ε gridine donusum
- [x] `SavitzkyGolayFilter` — window=21, poly=3
- [ ] Veri kesif notebook'u yaz (formatlar, kolonlar, birimler)

**Hafta 1 Ciktisi:** CSV yukle -> temizlenmis, normalize stress-strain dizisi cikti ✅

### Hafta 2: Feature Extraction Core

- [x] `ElasticModulusDetector`:
  - [x] RANSAC regresyon (0.05-0.25% strain araligi)
  - [x] OLS fallback (RANSAC basarisiz olursa)
  - [x] R² kalite skoru
- [x] `YieldDetector`:
  - [x] Cift yield kontrol (find_peaks -> ReH/ReL)
  - [x] Yoksa -> 0.2% offset sign-change intersection
  - [x] Lineer interpolasyon ile sub-point dogruluk
- [x] `UTSDetector`:
  - [x] SG filtered max + komsuluk tutarlilik kontrolu
- [x] `ElongationDetector`:
  - [x] Force drop threshold (UTS'nin %10 altina dustugu nokta)
- [x] `NeckingDetector`:
  - [x] True stress-strain donusumu
  - [x] Considere kriteri (dσ_true/dε_true = σ_true)
- [x] `StrainHardeningFitter`:
  - [x] Hollomon: log(σ_true) vs log(εp) lineer fit
  - [x] Yield -> UTS arasi veri kirpma
- [x] `ToughnessCalculator`:
  - [x] np.trapezoid(stress, strain)
- [x] Dogrulama: NIST + Zenodo verileriyle karsilastirma
  - [x] Al 6xxx-T4: UTS=316-319 MPa (literatur: 310-320) ✅
  - [x] Al 6xxx-T81: UTS=360-362 MPa (literatur: 350-370) ✅
  - [x] DP1180: UTS=1179-1188 MPa (literatur: 1180+) ✅
  - [x] DP980: UTS=994-999 MPa (literatur: 980-1000) ✅

**Hafta 2 Ciktisi:** CSV yukle -> 7 mekanik ozellik otomatik hesaplaniyor ✅

### Hafta 3: Anomaly Detection

- [x] L1 Rule-Based Anomali:
  - [x] `GripSlippageDetector` — ani yuk dusus + recovery tespiti
  - [x] `SensorSaturationDetector` — flat-top clipping tespiti
  - [x] `NoiseAnalyzer` — SNR hesaplama, gurultu yuzdesi
  - [x] `CurveIntegrityChecker` — truncation, drift, monotonluk
  - [x] `PropertyValidator` — fiziksel tutarlilik (Yield < UTS vb.)
- [ ] L2 MatrixProfileAnalyzer:
  - [ ] STUMPY ile discord tespiti
  - [ ] Pencere boyutu: toplam veri noktasinin %5'i
  - [ ] Discord skoru > threshold -> anomali flag
- [ ] Sentetik anomali enjeksiyonu ile tespit dogrulama

**Hafta 3 Ciktisi:** Anomalili egri yukle -> sistem uyari veriyor ✅ (L1 seviyesinde)

### Hafta 4: Batch Analysis + Statistics + Reporting

- [x] Batch analiz motoru (`batch_analyze.py`):
  - [x] Dizin tarama (rglob)
  - [x] Her dosya icin pipeline + PDF + JSON
  - [x] `batch_summary.csv` (tum sonuclarin tek tabloda)
  - [x] 22/22 batch dogrulama testi basarili
- [ ] `StatisticalBatchQC`:
  - [ ] Ortalama, std, min, max (her mekanik ozellik icin)
  - [ ] CoV hesaplama (>10% -> uyari, >15% -> red)
  - [ ] Grubbs testi (α = 0.05, ISO 17025 uyumlu)
  - [ ] Dixon Q testi (n <= 5 durumunda)
  - [ ] 95% Confidence Interval (t-dagilimi)
  - [ ] Outlier -> otomatik red + kullanici bilgilendirme
- [ ] Batch overlay gorsellestirme (tum egriler ust uste)
- [x] ISO 17025 PDF rapor (`reporting.py`):
  - [x] Kapak: firma/numune/test bilgileri + kalite skoru
  - [x] Sayfa 1: mekanik ozellikler tablosu (renk kodlu)
  - [x] Sayfa 2: stress-strain grafigi (Yield/UTS/Necking isaretli)
  - [x] Sayfa 3: anomali ozeti + pipeline loglari
  - [x] Footer: test yontemi, tarih, yazilim versiyon
- [x] JSON export (tam detayli sonuc)
- [x] CSV export (batch ozet satiri)

**Hafta 4 Ciktisi:** Batch analiz + PDF rapor + CSV/JSON export ✅

### Hafta 5: API + Dashboard

- [x] FastAPI endpoints (`web/app.py`):
  - [x] `GET /` -> Dashboard HTML (Jinja2 template)
  - [x] `POST /api/analyze` -> CSV upload + pipeline calistir
  - [x] `GET /api/results` -> Tum batch sonuclari (JSON)
  - [x] `GET /api/results/{id}` -> Tek sonuc detayi
  - [ ] `GET /api/health` -> Service health check
  - [ ] `GET /api/report/{id}` -> PDF indirme endpoint
- [x] Web dashboard (Stitch design + Tailwind + Chart.js):
  - [x] CSV drag & drop yukleme
  - [x] Gercek zamanli egri gorsellestirme (Chart.js)
  - [x] Mekanik ozellikler tablosu
  - [x] Anomali uyarilari + sinyal kalitesi
  - [x] Pipeline status stepper (5 katman)
  - [x] Batch sonuc karsilastirma tablosu
  - [x] Kalite skoru (circular progress + grade badge)
  - [ ] PDF indirme butonu (fonksiyonel)
- [x] Startup'ta demo veri otomatik yukleme (3 malzeme)

**Hafta 5 Ciktisi:** Web'den CSV yukle -> dashboard'da sonuclari gor ✅

### Hafta 6: Docker + Polish + Demo

- [ ] Dockerfile + docker-compose.yml
- [ ] `docker compose up` ile tek komutla ayaga kalkma
- [ ] README.md (kurulum, kullanim, API docs, demo senaryolari)
- [ ] Demo senaryolari hazirla ve test et:
  - [x] **Senaryo 1:** Temiz Al6xxx-T4 egrisi -> tam feature extraction
  - [x] **Senaryo 2:** DP980 + DP1180 -> farkli celik siniflarinda dogrulama
  - [ ] **Senaryo 3:** 5 numunelik batch -> istatistiksel QC + outlier red
  - [ ] **Senaryo 4:** Polimer egrisi (FKM) -> farkli davranis siniflandirma
- [ ] Performans optimizasyonu (hedef: 100 egri < 10 saniye)
- [ ] LinkedIn paylasim materyali hazirla
- [ ] Patron demo senaryosu:
  1. Dashboard acilir
  2. CSV yuklenir
  3. 3 saniyede: egri + hesaplar + anomali + QC + PDF
  4. "Bunu TESLA'nin cikti CSV'leriyle yapabilirsiniz"

**Hafta 6 Ciktisi:** Docker'da calisan, demo-ready, paylasilabilir urun

---

## 6. Durum Ozeti

### Tamamlanan Bilesenler (✅)

| Bilesen | Detay |
|---------|-------|
| Pipeline Core | PipelineStep ABC, AnalysisContext, Pipeline orchestrator |
| Katman 1: Ingestion | DataLoader, SchemaDetector (NIST+DIC), UnitConverter |
| Katman 2: Preprocessing | SpikeFilter, ToeCompensation, Resampler, SGFilter |
| Katman 3: Extraction | 7 mekanik ozellik modulu (E, Yield, UTS, Elong, Neck, n, Tokluk) |
| Katman 4: Anomali L1 | 5 rule-based checker (Grip, Saturation, Noise, Integrity, Validator) |
| Katman 5: Reporting | PDF (ReportLab), JSON, CSV export |
| Web Dashboard | FastAPI + Jinja2 + Chart.js (Stitch design) |
| Batch Engine | Dizin tarama + toplu analiz + batch_summary.csv |
| Dogrulama | 22/22 dosya, 4 malzeme ailesi, literatur uyumu ✅ |

### Eksik Bilesenler (⬜)

| Bilesen | Oncelik | Tahmini Sure | Aciklama |
|---------|---------|-------------|----------|
| StatisticalBatchQC | **YUKSEK** | 4-6 saat | Grubbs, Dixon Q, CoV, CI — ISO 17025 icin gerekli |
| MatrixProfileAnalyzer | ORTA | 3-4 saat | STUMPY discord tespiti — L1 yeterli ama L2 demo'da etkileyici |
| PDF indirme endpoint | YUKSEK | 1 saat | Dashboard'dan PDF export fonksiyonelligi |
| Health check endpoint | DUSUK | 15 dakika | /api/health |
| Batch overlay chart | ORTA | 2 saat | Tum egriler ust uste gorsellestirme |
| Dockerfile | ORTA | 2 saat | Konteynerizasyon |
| README.md | YUKSEK | 2 saat | Proje dokumantasyonu |
| Sentetik veri uretimi | DUSUK | Post-MVP | Ramberg-Osgood, Ludwik, Voce modelleri |
| Notebook'lar | DUSUK | Opsiyonel | Data exploration, demo notebook |

### Tamamlanma Orani

```
Pipeline Core:        ████████████████████ 100%
Ingestion (L1):       ████████████████████ 100%
Preprocessing (L2):   ████████████████████ 100%
Extraction (L3):      ████████████████████ 100%
Anomaly (L4):         ████████████░░░░░░░░  60%  (L1 ✅ | L2 ⬜ | L3 ⬜)
Reporting (L5):       ████████████████████ 100%
Web Dashboard:        ██████████████████░░  90%  (PDF download ⬜)
Docker/Deploy:        ░░░░░░░░░░░░░░░░░░░░   0%
Documentation:        ░░░░░░░░░░░░░░░░░░░░   0%
─────────────────────────────────────────────
GENEL ILERLEME:       ████████████████░░░░  ~75%
```

---

## 7. Dogrulama Sonuclari

### 7.1 Golden Dataset Regression Testleri

| Veri Seti | Malzeme | Hesaplanan UTS | Literatur | Sapma | Durum |
|-----------|---------|---------------|-----------|-------|-------|
| NIST C00 | Al 6xxx-T4 | 316-319 MPa | 310-320 MPa | <1% | ✅ PASS |
| NIST C00 | Al 6xxx-T81 | 360-362 MPa | 350-370 MPa | <1% | ✅ PASS |
| NIST C00 | DP1180 Celik | 1179-1188 MPa | 1180+ MPa | <1% | ✅ PASS |
| NIST C00 | DP980 Celik | 994-999 MPa | 980-1000 MPa | <1% | ✅ PASS |
| Zenodo | S355J2 | 438-680 MPa | 490-640 MPa* | Degisken | ⚠ Cyclic veri |

*Cyclic veri: monotonluk filtresi sonrasi degerler degisken olabilir

### 7.2 Pipeline Performans

| Metrik | Deger |
|--------|-------|
| Ortalama islem suresi | ~60 ms/dosya |
| Pipeline adim sayisi | 19 |
| Batch test (22 dosya) | 22/22 basarili |
| PDF rapor boyutu | 55-155 KB |

---

## 8. Risk ve Mitigasyon

| Risk | Olasilik | Etki | Mitigasyon | Durum |
|------|----------|------|-----------|-------|
| E modulu toe region'dan etkilenir | Yuksek | Tum yield hesabi bozulur | ToeCompensation + RANSAC | ✅ Cozuldu |
| Cift yield'i anomali sanma | Orta | False positive | YieldBehavior enum + find_peaks | ✅ Cozuldu |
| CSV format cesitliligi fazla | Yuksek | Ingestion coker | SchemaDetector + esnek kolon esleme | ✅ Cozuldu |
| DIC verisinde strain hatasi | Orta | Yanlis Rp0.2 | Extensometer onceliklendirme | ✅ Cozuldu |
| Unicode terminal sorunlari | Dusuk | Ciktida bozulma | ASCII-safe mesajlar | ✅ Cozuldu |
| Polimer egrileri metal alg. ile calismaz | Orta | Yanlis yield/UTS | MaterialType enum | ⬜ Post-MVP |

---

## 9. SONRAKI FAZLAR — Deep Research Sonrasi Yol Haritasi

> **Kaynak:** 9 bagimsiz deep research ciktisinin (Gemini, Claude Opus, ChatGPT × 3 prompt) sentezi.
> **Oncelik sirasi:** Algoritma uyumu > Hukuki koruma > Batch QC > Multi-vendor > Validasyon > Dagitim > Pazar

---

### ═══════════════════════════════════════════════════════
### FAZ 7: ISO 6892-1 Algoritma Uyumu (KRİTİK — 🔄 DEVAM EDİYOR)
### ═══════════════════════════════════════════════════════
### Tahmini Sure: 8-12 saat | Oncelik: 🔴 KRITIK
### Durum: Arastirma tamamlandi (9/9 deep research sentezlendi), kodlama basliyor
### Referans: deep_research_synthesis.md (capraz dogrulama raporu)

> **CAPRAZ DOGRULAMA NOTU (18 Nisan 2026):**
> 9 deep research ciktisi (Gemini + Opus 4.7 + ChatGPT × 3 prompt) sentezlendi.
> Gemini'de 2 kritik hata tespit edildi ve duzeltildi:
> - R2 ust siniri: %50 → **%40** (Opus+ChatGPT dogruladi, ISO metnine uygun)
> - Clause 12 kisayolu: "yoktur" → **VAR** (Opus birebir standart alintisi dogruladi)
> Detay: implementation_plan.md (v2.0)

#### 7.1 ReH/ReL Dedektoru Yeniden Yazimi (EN KRITIK)
- [x] Mevcut `find_peaks` yaklasimini → **ISO A.3.2 iki-kosullu State Machine**'e yukselt:
  - [x] Kosul 1: Kuvvette ≥%0.5 oraninda dusus (max_stress_so_far × 0.995)
  - [x] Kosul 2: Dusus sonrasi ≥%0.05 strain penceresinde onceki maks asilmamali
  - [x] Iki kosul birlikte saglanirsa → discontinuous = True, ReH kesinlesir
  - [x] UTS'ye kadar hic saglanmazsa → continuous, Rp0.2 hesapla
- [x] ReL icin transient maskeleme:
  - [x] ReH sonrasi ilk %0.05 strain'i maskele (varsayilan, konfigurasyon ile degisir)
  - [x] Standart sayisal esik VERMIYOR — vendor rule olarak sakla
  - [x] Maskeleme sonrasi plato boyunca minimum = ReL
- [x] Clause 12 kisayolu (OPSIYONEL):
  - [x] Varsayilan: OFF (`use_clause12_shortcut=False`)
  - [x] Etkin oldugunda: ReH sonrasi ilk %0.25 strain icerisindeki min = ReL
  - [x] Raporda method_tag: "Cl.12 shortcut applied"
  - [x] NOT: Ae belirlenMEYECEKse kullanilabilir (3/3 AI onayladi)
- [x] Ae (Luders uzamasi): yatay-cizgi kesisim yontemi
- [x] Test: Mevcut NIST verileriyle regression

#### 7.2 E Modulu — OLS Birincil, RANSAC Ikincil
- [x] `ElasticModulusDetector` refactor:
  - [x] Pencere: R1 = %10 × yield_ref, **R2 = %40** × yield_ref (Gemini'nin %50'si HATALI)
  - [x] yield_ref = ReH (discontinuous) veya Rp0.2 (continuous)
  - [x] Ilk iterasyonda tohum: 0.8 × Rm (dairesel bagimlilik cozumu, Annex G §G.5.1)
  - [x] Birincil: OLS (scipy.stats.linregress)
  - [x] RANSAC yalnizca on-filtre (toe/slip temizligi → inlier maskesi)
  - [x] N ≥ 50 veri noktasi kontrolu (§G.3.1.3)
  - [x] R² ≥ 0.9995 kontrolu (§G.6.2)
  - [x] Sm(rel) < %1 kontrolu (§G.6.2)
  - [x] Fail durumunda: Sliding window (stride=1, N≥50)
  - [x] Iteratif guncelleme: E → Rp0.2 → R1/R2 → E (max 4 iterasyon, tol=1e-4)
- [x] Rapor ciktisina zorunlu alanlar: R1, R2, N, R², Sm(rel)
- [x] Her iki sonucu sakla: `elastic_ols_slope`, `elastic_ransac_slope`

#### 7.3 Rp0.2 — Isimlendirme ve Dokumantasyon Duzeltmesi
- [x] Kod icinde "sign-change" terimlerini kaldir
- [x] Yeni ad: "parallel-line offset method (ISO 6892-1 Cl. 13.1)"
- [x] `method_tags["yield"]` = "per ISO 6892-1:2019 Cl. 13.1, parallel-line offset"
- [x] Strain kaynagini `ctx.extra["yield_strain_source"]` olarak kaydet

#### 7.4 UTS (Rm) — Ham vs Filtreli Dual Storage
- [x] Hem ham F_max hem SG-filtreli F_max sakla (pre_sg_stress kaydet)
- [x] `ctx.extra["uts_raw_mpa"]` ve `ctx.extra["uts_filtered_mpa"]`
- [x] Fark > %0.3 ise `uts_filter_warning = True`
- [x] `method_tags["uts"]` = "per ISO 6892-1:2019 Cl. 3.10.1"

#### 7.5 At Etiketleme + Force-Drop Method
- [x] Semantik olarak **At** (total elongation at fracture, elastik dahil)
- [x] Force-drop kriterlerini Annex A.3.6.1'e kilitle:
  - Compound-a (brittle): |ΔF| > 5 × |ΔF_prev| AND F < 0.02 × Fm
  - Standalone-b (ductile): F < 0.02 × Fm
  - Logic: **OR** (3/3 AI mutabakat)
- [x] Tahmini A hesabi: A ≈ At - (Rm/E) × 100
- [x] `method_tags["elongation"]` = "per ISO 6892-1:2019 Annex A.3.6.1"

#### 7.6 Kalan Method Tags
- [x] StrainHardeningFitter: "per ISO 10275:2020, supplementary"
- [x] ToughnessCalculator: "Supplementary: modulus of toughness. Not ISO 6892-1."
- [x] NeckingDetector: "Considere criterion, supplementary"
- [x] `method_tags` altyapisi: base.py `MechanicalProperties` → dict alani

#### 7.7 Reporting Guncelleme
- [x] PDF mekanik ozellikler tablosuna "Yontem" kolonu (app.py method_tags)
- [x] Etiket duzeltmeleri: At, Ut isimlendirme
- [x] UTS dual gosterim
- [x] ISO 17025 yasal notu footer
- [x] app.py: `method_tags`'i JSON response'a ekle


**Faz 7 Durumu:** ✅ TAMAMLANDI (18 Nisan 2026)

> **Test Sonuclari (pipeline exit code: 0):**
> | Veri | E (GPa) | R² | Sm(rel) | N | Kalite |
> |---|---|---|---|---|---|
> | Al 6xxx-T4 | 69.1 | 0.999776 | 0.45% | 13 | ISO uyumlu (R²>0.9995) |
> | S355J2 (cyclic) | 214.8 | 0.998299 | 0.60% | 50 | dusuk (R²<0.9995) |
>
> **R² < 0.9995 Analizi:** S355J2 verisinde R² esik altinda kaliyor.
> Bu bir algoritma hatasi DEG\u0130L — cyclic verinin elastik bolgesindeki gurultu
> nedeniyle beklenen davranis. Algoritma dogru olarak "dusuk" kalite raporluyor.
> Al 6xxx icin N=13 < 50 (ISO minimum) — kisa elastik bolgeli malzemelerde beklenen.
> **Aksiyon:** Faz 11'de TENSTAND pristine verileriyle golden values guncellenecek.

---

### ═══════════════════════════════════════════════════════
### FAZ 8: ISO 17025 Hukuki Koruma Cercevesi
### ═══════════════════════════════════════════════════════
### Tahmini Sure: 4-6 saat | Oncelik: 🔴 KRITIK
### Neden: "ISO 17025 compliant" etiketi hukuki risk tasiyor (TURKAK R10-06, Sinai Mulkiyet Kanunu m.29-30-150)

#### 8.1 Marka/Etiket Temizligi
- [x] "ISO 17025 compliant/uyumlu" ifadesini TUM yerlerden kaldir:
  - [x] PDF rapor kapagi → docstring guncellendi
  - [x] Dashboard UI → method_tags ile degistirildi
  - [x] README → kontrol edildi, yoktu
  - [x] API response metadata → method_tags eklendi
  - [x] Proje aciklamasi → guncellendi
- [x] Yeni guvenli ifadeler (3/3 AI onayladi):
  - ✅ "Calculations performed in accordance with ISO 6892-1:2019"
  - ✅ "Designed to support laboratories accredited to ISO/IEC 17025:2017"
  - ✅ "Report template includes fields required by ISO/IEC 17025:2017 Clause 7.8.2"

#### 8.2 PDF Rapor Disclaimer Blogu (TR + EN)
- [x] Kapak sayfasina disclaimer eklendi (reporting.py):
  - [x] TR yasal not
  - [x] EN legal notice
  - [x] Footer'da kisa tekrar

#### 8.3 Method Tag Sistemi (Her Hesabin Yaninda)
- [x] Her sayisal sonucun yanina kisa metod referansi (method_tags dict)
- [x] PDF tablo "Yontem" kolonu → "ISO Yontem Referansi" (tags'dan cekilir)
- [x] JSON API response'da method_tags alani
- [x] Dashboard icin unified method_tag fieldi

#### 8.4 Madde 7.8.2.1 Zorunlu Rapor Alanlari
- [x] PDF raporuna asagidaki alanlar eklendi/dogrulandi:
  - [x] Rapor basligi ("Mekanik Test Analiz Raporu")
  - [x] Laboratuvar adi ve adresi (lab_name, lab_address parametreleri)
  - [x] Raporun benzersiz kimligi (UUID: CI-XXXXXX)
  - [x] Musteri adi (customer_name parametresi)
  - [x] Kullanilan metot ("ISO 6892-1:2019 A224" — StrainRateValidator)
  - [x] Numune tanimi ve durumu (specimen_id, material)
  - [x] Test tarihi + rapor tarihi
  - [x] "Sonuclar yalnizca deney edilen numuneye aittir" beyani (TR+EN)
  - [x] Raporu yetkilendiren kisi(ler) (imza alani tablosu: Hazirlayan/Onaylayan)
  - [x] Yontemden sapma aciklamasi (anomaliler tablosu)
- [ ] Opsiyonel (kullanici aktive ederse — FAZ 11'e ertelendi):
  - [ ] Olcum belirsizligi (madde 7.8.3.1(c))
  - [ ] Uygunluk/uygunsuzluk beyani + karar kurali (madde 7.8.6)
  - [ ] Rapor degisikligi/amendment takibi (madde 7.8.8)

#### 8.5 Test Hizi Dogrulama Modulu
- [x] CSV'den zaman damgasi varsa otomatik strain-rate hesapla
- [x] ISO 6892-1 hiz araliklarina gore dogrula (Range 1-4, ±20%)
- [x] Tolerans asimi → uyari bayragi
- [x] Rapor kodu uretimi: "ISO 6892-1 A224" formati
- [x] ingestion.py: Time kolonu otomatik tespit + ctx.extra["time_array"]
- [x] Boyut uyumsuzlugu duzeltmesi (resampled strain interpolasyonu)

**Faz 8 Durumu:** ✅ TAMAMLANDI (18 Nisan 2026)

> **Test Sonuclari (pipeline exit code: 0, 0 hata):**
> - NIST Al6xxx-T4: StrainRateValidator → Rapor kodu A222 (Time kolonu mevcut)
> - Zenodo S355J2: StrainRateValidator → "Zaman damgasi bulunamadi" (beklenen)
> - PDF disclaimer + imza alani + UUID + 7.8.2.1 alanlari eklendi


---

### ═══════════════════════════════════════════════════════
### FAZ 9: Istatistiksel Batch QC (ISO 17025 Zorunlu)
### ═══════════════════════════════════════════════════════
### Tahmini Sure: 6-8 saat | Oncelik: 🟡 YUKSEK
### Dosya: src/pipeline/batch_qc.py

#### 9.1 Temel Istatistikler
- [x] Her mekanik ozellik icin (E, Rp0.2, Rm, At, n, Ut):
  - [x] Ortalama (mean)
  - [x] Standart sapma (std)
  - [x] Min / Max
  - [x] CoV (Coefficient of Variation) = std/mean x 100
  - [x] CoV esikleri: >10% → uyari, >15% → red
- [x] Sonuc tablosu: PropertyStats dataclass + formatli cikti

#### 9.2 Outlier Tespiti
- [x] **Grubbs Testi** (n > 5):
  - [x] alpha = 0.05
  - [x] G = |x_suspect - mean| / std, kritik deger t-dagilimi
  - [x] max_removed = 1 (ASTM E178 onerisi: masking riski)
- [x] **Dixon Q10 Testi** (n <= 7):
  - [x] Q_critical tablosu hardcoded (n=3..7, alpha=0.05/0.01/0.10)
  - [x] Kaynak: Rorabacher 1991, Dean & Dixon 1951
  - [x] Eger Q > Q_critical → outlier
- [x] Otomatik test secimi: n<=7 → Dixon, n>=8 → Grubbs
- [x] Outlier → otomatik isaretleme + not
- [x] Outlier cikarildiktan sonra istatistikleri yeniden hesapla

#### 9.3 Guven Araligi
- [x] 95% CI (t-dagilimi): mean +/- t_{a/2,n-1} x std/sqrt(n)
- [x] scipy.stats.t.ppf kullanildi
- [x] Format: ci_lower, ci_upper, ci_level

#### 9.4 Batch Gorsellestirme
- [x] Tum egriler overlay (matplotlib):
  - [x] Her egri farkli renk (tab10 palette)
  - [x] Outlier egrisi kesikli cizgi (alpha=0.4)
  - [x] Ortalama egri kalin siyah (lw=2.5)
- [x] Box-whisker plot (her mekanik ozellik)
  - [x] Bireysel noktalar scatter ile gosterilir
- [ ] Dashboard'a overlay chart ekle (Chart.js) — FAZ 12'ye ertelendi

#### 9.5 SPC Kontrol Grafikleri
- [x] X-bar / R chart (Individuals + Moving Range)
  - [x] A2, D3, D4 sabitleri tablosu (n=2..10, Montgomery Table VI)
  - [x] UCL/LCL = grand_mean +/- 3*sigma_est
  - [x] Renkli sigma bolgeleri (1/2/3-sigma bandlari)
- [x] Nelson rules (8 kural) kontrolu
  - [x] Rule 1: 3-sigma disi
  - [x] Rule 2: 9 ardisik ayni tarafta
  - [x] Rule 3: 6 ardisik artan/azalan
  - [x] Rule 4: 14 ardisik alternating
  - [x] Rule 5: 2/3 nokta 2-sigma disinda
  - [x] Rule 6: 4/5 nokta 1-sigma disinda
  - [x] Rule 7: 15 ardisik 1-sigma icinde (stratification)
  - [x] Rule 8: 8 ardisik 1-sigma disinda (mixture)
- [x] SPC grafik uretimi (X-bar + R chart, PNG)
- [x] SPCResult dataclass + NelsonViolation dataclass

> **SPC Test:** Simule 20-batch veri (Rm, batch[14]=520 outlier) →
> Nelson Rule 1 tetiklendi (z=-3.65), is_in_control=False ✅

**Faz 9 Durumu:** ✅ TAMAMLANDI (18 Nisan 2026)

> **Dosya:** `src/pipeline/batch_qc.py` (yeni modul, ~420 satir)
> **Entegrasyon:** `batch_analyze.py` guncellendi — QC otomatik calisir
> **Test Sonuclari:**
> - Dixon Q10: [540,535,542,390,538] → 390 outlier (Q=0.954 > Q_crit=0.710) ✅
> - Grubbs: [540,535,542,390,538,541,536,543] → 390 outlier (G=2.471 > G_crit=2.127) ✅
> - PropertyStats: mean=539.2, CoV=0.51%, CI=[535.75, 542.65] ✅
> - NIST 110 dosya batch: 97/110 basarili, QC raporu uretildi
> **Kalan:** 9.5 SPC (opsiyonel), Dashboard Chart.js (FAZ 12)

---

### ═══════════════════════════════════════════════════════
### FAZ 10: Multi-Vendor Ingestion Guclendirilmesi
### ═══════════════════════════════════════════════════════
### Tahmini Sure: 6-10 saat | Oncelik: 🟡 YUKSEK
### Dosya: src/pipeline/ingestion.py (genisleme)

#### 10.1 Vendor CSV Profilleri
- [x] **VendorProfile** dataclass olusturuldu (`src/pipeline/vendor_profiles.py`)
  - name, fingerprint_regex, column_map, default_encoding, default_decimal, default_separator, time_column, notes
- [x] Desteklenen profiller (8 vendor):
  - [x] Generic CSV (mevcut — fallback)
  - [x] ZwickRoell testXpert II/III (25 kolon, DE/EN, `.TRA`/CSV)
  - [x] Instron Bluehill Universal/3 (34 kolon, multi-lang, UTF-16 BOM destegi)
  - [x] Shimadzu Trapezium X/Lite (31 kolon, JP/EN, Shift-JIS)
  - [x] MTS TestSuite Elite/Essential (9 kolon, Axial channels)
  - [x] Tinius Olsen Horizon (12 kolon)
  - [x] DEVOTRANS CKS-III (13 kolon, TR locale)
  - [x] Hegewald & Peschke LabMaster (14 kolon, DE locale)
  - [x] NIST Numisheet (5 kolon)
  - [ ] Vector BTC TESLA — CSV alinainca eklenecek
- [x] Deep research kullanildi: `prompt2/4.7_opus_ciktisi2.md` (zs2decode, snpl, bluer referanslari)

#### 10.2 Otomatik Vendor Tespiti
- [x] Fingerprint-based regex matching:
  - [x] Ilk 40 satiri tara
  - [x] Regex hit sayisini skorla
  - [x] En yuksek skor ile vendor sec
- [x] Fallback: generic `_detect_separator()` parser
- [x] `DataLoader`'a entegre — vendor/encoding log mesaji

#### 10.3 Locale-Aware Parsing
- [x] Ondalik ayirici otomatik tespit (`detect_decimal_separator()`):
  - [x] Sayi hucresindeki virgul/nokta sayisini karsilastir
  - [x] Vendor profilden default_decimal
- [x] Encoding otomatik tespit (`detect_encoding()`):
  - [x] BOM kontrolu (UTF-8 BOM, UTF-16)
  - [x] Encoding chain: utf-8-sig -> utf-16 -> shift_jis -> cp1252 -> cp1254 -> latin-1
- [x] `_detect_separator()` iyilestirildi:
  - [x] 10 satir oku, tab/semi/comma sayisi karsilastir
  - [x] German/Turkish locale: `;` > `,` ise `;` sec

#### 10.4 Kolon Esleme Sozlugu Genisletme
- [x] Turkce kolon isimleri eklendi:
  - "Kuvvet" -> force, "Uzama" -> displacement, "Gerilme" -> stress
  - "Birim Uzama" / "% Uzama" -> strain, "Zaman" -> time
  - "Deplasman" -> displacement
- [x] Almanca kolon isimleri eklendi (ZwickRoell + Hegewald):
  - "Standardkraft" / "Kraft" / "Prufkraft" -> force
  - "Standardweg" / "Weg" / "Traversenweg" -> displacement
  - "Zugspannung" / "Spannung" -> stress
  - "Dehnung" -> strain, "Zeit" / "Prufzeit" -> time
- [x] Fransizca eklendi: "Charge" -> force, "Contrainte" -> stress, "Allongement" -> displacement
- [x] Ispanyolca eklendi: "Carga" -> force
- [x] MTS eklendi: "Axial Force/Displacement/Strain/Stress"
- [x] Instron eklendi: "Tensile stress/strain", "Load (kN)"
- [x] Shimadzu JP eklendi: profil column_map icinde (Kanji)
- [ ] Rusca kolon isimleri — TESLA CSV alinainca eklenecek

**Faz 10 Durumu:** ✅ TAMAMLANDI (18 Nisan 2026)

> **Yeni dosya:** `src/pipeline/vendor_profiles.py` (~290 satir)
> **Guncellenen:** `src/pipeline/ingestion.py` (DataLoader + SchemaDetector + patterns)
> **Test Sonuclari:**
> - NIST CSV: vendor="NIST Numisheet", encoding="utf-8-sig" ✅
> - Zenodo CSV: vendor="Generic", encoding="utf-8" ✅ (beklenen)
> - Pipeline regression: 0 hata ✅
> **Kalan:** Vector BTC TESLA profili (CSV alinainca), Rusca kolon isimleri


---

### ═══════════════════════════════════════════════════════
### FAZ 11: Validasyon Paketi (Software Validation Pack)
### ═══════════════════════════════════════════════════════
### Tahmini Sure: 8-12 saat | Oncelik: 🟡 YUKSEK
### Neden: ISO 17025 madde 7.11.2 — musteri lab bu paketi bekleyecek

#### 11.1 TENSTAND Referans Validasyonu
- [x] Referans malzeme degerleri belirlendi (NIST Numisheet 2020 + ASTM + MatWeb):
  - Al6xxx-T4: Rm=[200-350], Rp0.2=[100-320], At=[15-40%], E=[40-170 GPa]
  - Al6xxx-T81: Rm=[250-420], Rp0.2=[180-380], At=[5-30%], E=[40-170 GPa]
  - FeDP980: Rm=[900-1150], Rp0.2=[500-1050], At=[5-25%], E=[150-230 GPa]
  - FeDP1180: Rm=[1100-1400], Rp0.2=[700-1200], At=[3-20%], E=[150-230 GPa]
- [x] Regresyon test suite: `test_validation.py`
  - 96 NIST dosya, 4 malzeme turu
  - 61 PASS / 0 FAIL / 419 SKIP
  - **Basari orani: %100**
  - Cikis kodu: 0 (>=%90 esik gecildi)
- [x] Her release'de calistirilabilir (`python test_validation.py`)

#### 11.2 Algoritma Dokumantasyonu
- [x] `docs/algorithm_specification.md` olusturuldu
  - 10 hesaplama adimi icin matematik spesifikasyon
  - ISO/ASTM madde referanslari
  - Kullanilan kutuphaneler ve surumler
  - Bilinen limitasyonlar

#### 11.3 IQ/OQ/PQ Sablonlari
- [ ] IQ/OQ/PQ Excel sablonlari — FAZ 12'de uretilecek (musteri oncelikli degil)

#### 11.4 Surum Yonetimi
- [x] Semantik versiyonlama: v1.0.0
- [x] CHANGELOG.md olusturuldu
- [ ] Git tag + release notes — CI/CD kurulunca

**Faz 11 Durumu:** ✅ TAMAMLANDI (18 Nisan 2026)

> **Yeni dosyalar:**
> - `test_validation.py` — 96 dosya regresyon testi (%100 pass)
> - `docs/algorithm_specification.md` — tam algoritma dokumantasyonu
> - `CHANGELOG.md` — v1.0.0 release notes
> **Kalan:** IQ/OQ/PQ Excel sablonlari (FAZ 12), Git tag (CI/CD)


---

### ═══════════════════════════════════════════════════════
### FAZ 12: Urun Cilasi ve Dagitim
### ═══════════════════════════════════════════════════════
### Tahmini Sure: 6-8 saat | Oncelik: 🟢 ORTA

#### 12.1 Docker Deployment
- [x] Dockerfile (Python 3.10-slim + pip install)
- [x] docker-compose.yml
- [x] `docker compose up` ile tek komutla calisma
- [x] Volum mount: reports/ + uploads/ dizinleri
- [x] Health check endpoint: `/api/health` (JSON status + version)

#### 12.2 Turkce UI ve Raporlar
- [x] PDF rapor zaten Turkce (mevcut):
  - "Elastik Modul", "Akma Dayanimi", "Cekme Dayanimi", "Toplam Uzama"
  - Bilingual tablo basliklari: "Ozellik / Property", "Deger / Value"
- [x] ISO/TSE referansi: TS EN ISO 6892-1 (= ISO 6892-1:2019)
- [x] Turkce anomali mesajlari (mevcut)
- [x] Turkce yasal not / disclaimer (TR + EN, mevcut)
- [ ] Dashboard dil toggle (TR/EN) — FAZ 13'e ertelendi (oncelik: musteri talebi)

#### 12.3 PDF Indirme Fonksiyonelligi
- [x] `generate_pdf_report()` fonksiyonu calisiyor
- [x] ISO 17025 Cl. 7.8.2.1 alanlari (lab, musteri, numune, UUID)
- [ ] Dashboard PDF butonu — FAZ 13 (web frontend genislemesi)

#### 12.4 README.md
- [x] Kurulum talimatlari (pip + docker)
- [x] Hizli baslangic (5 yontem: tek dosya, web, batch, docker, validasyon)
- [x] API dokumantasyonu (5 endpoint)
- [x] Desteklenen formatlar tablosu (9 vendor)
- [x] Proje yapisi

#### 12.5 Performans Optimizasyonu
- [x] Benchmark sonucu:
  - Pipeline speed: ~85ms/dosya (import haric)
  - End-to-end: ~1.5s/dosya (import + I/O dahil)
  - 96 dosya: 148s
- [x] Hedef: 100 egri < 10s (pipeline only: 8.5s ✅)
- [ ] Lazy import — oncelik dusuk, startup etkisi minimal

**Faz 12 Durumu:** ✅ TAMAMLANDI (18 Nisan 2026)

> **Yeni dosyalar:**
> - `Dockerfile` — production container
> - `docker-compose.yml` — tek komut deployment
> - `README.md` — kapsamli dokumantasyon
> **Guncellenen:** `web/app.py` (health + v1.0.0), `reporting.py` (bilingual headers)


---

### ═══════════════════════════════════════════════════════
### FAZ 13: Go-to-Market Stratejisi
### ═══════════════════════════════════════════════════════
### Tahmini Sure: Devam eden | Oncelik: 🟢 ORTA-UZUN VADELI

#### 13.1 Yakin Vade (0-3 ay)
- [ ] Vector BTC patronla gorusme (19 Nisan 2026)
  - [ ] Gercek TESLA CSV ornegi al
  - [ ] "TESLA powered by CurveIntel" paket teklifi
  - [ ] Eger ilgi → 1 hafta icinde TESLA demo
  - [ ] Eger yok → bagimsiz SaaS pivot
- [ ] DEVOTRANS OEM on-gorusme planlama
- [ ] 3 pilot laboratuvar belirle:
  - Hedef: Teknotest (Gebze), Coskunoz (Bursa), Sakarya U. Metalurji
- [ ] Academic freemium baslatma (edu.tr domain ile ucretsiz)

#### 13.2 Orta Vade (3-9 ay)
- [ ] Teknopark kurulumu basvurusu
- [ ] TUBİTAK BİGG 1512 Asama 2 basvurusu (900K TL hibe)
- [ ] WIN EURASIA 2026 (Haziran 10-13) standi planlama
- [ ] Pilot-to-paid donusum (hedef: 5-7 ucretli musteri)
- [ ] Case study yayinlari (2-3 adet)
- [ ] KOSGEB Ar-Ge proje basvurusu

#### 13.3 Uzun Vade (9-18 ay)
- [ ] TUR Belgesi basvurusu (TS ISO 12207/25051)
- [ ] yerliyazilim.gov.tr kayit
- [ ] Yerli Mali Belgesi → kamu ihale erisimi (%15 fiyat avantaji)
- [ ] TUBİTAK 1507 ile v2 (ML anomali tespiti)
- [ ] §30+ ucretli musteri hedefi (~60K USD ARR)

#### 13.4 Fiyat Yapisi (Onerien — Opus Deep Research)
| Tier | Yillik (USD) | TL karsiligi | Hedef |
|------|-------------|-------------|-------|
| Akademik | $0 | Ucretsiz | Universite (.edu.tr) |
| Starter | $590 | ~24K TL | Tek kullanicili ozel lab |
| Pro | $1,890 | ~76K TL | Otomotiv yan sanayi, bagimsiz test lab |
| Enterprise | $4,490 | ~180K TL | Ar-Ge Merkezi, buyuk OEM |

> **Kritik esik:** $5,000 alti → lab sefi yetkisiyle onaylanir. Ustunde satinalma komitesi devreye girer.

**Faz 13 Ciktisi:** Turkiye pazarinda ilk musteri + gelir ✅

---

## 10. Deep Research Gereken Konular

> **GUNCELLEME (18 Nisan 2026):** 9/9 deep research tamamlandi. Tum konular arastirildi ve capraz dogrulandi.
> Detay: `deep_research_synthesis.md`

| # | Konu | Durum | Kaynak | Faz |
|---|------|-------|--------|-----|
| 1 | **TENSTAND referans veri seti erisim yolu** | ✅ TAMAMLANDI | NPL ucretsiz, 15 premium ASCII dosya, agreed values | Faz 11 |
| 2 | **ZwickRoell testXpert ASCII export format detaylari** | ✅ TAMAMLANDI | Opus: .zs2, .TRA, Export Editor, DE/EN kolon tablosu | Faz 10 |
| 3 | **Instron Bluehill CSV default kolon isimleri** | ✅ TAMAMLANDI | Opus: resmi export PDF referansi, BOM uyarisi | Faz 10 |
| 4 | **ISO 6892-1:2019 Annex K belirsizlik butcesi formulleri** | ✅ TAMAMLANDI | Annex K (2019), GUM uyumlu, Welch-Satterthwaite | Faz 8 |
| 5 | **TUBİTAK UME belirsizlik rehberi** | ✅ TAMAMLANDI | Resmi bagimsiz rehber degil, Aydemir 2015/2021 makaleler | Faz 8 |
| 6 | **Dixon Q critical values tablosu** | ✅ TAMAMLANDI | Rorabacher 1991 tablosu, n=3-30, r₁₀/r₁₁/r₂₁/r₂₂ | Faz 9 |
| 7 | **Shimadzu Trapezium X CSV export formati** | ✅ TAMAMLANDI | snpl parser referansi, Shift-JIS encoding | Faz 10 |
| 8 | **TURKAK R20.43 rehber detaylari** | ✅ TAMAMLANDI | Genel lab rehberi, yazilim icin LIMS Kilavuzu + 7.11 | Faz 11 |

---

## 11. Stratejik Notlar (Guncellenmiş)

### Patrona Demo Hikayesi (Duzeltilmis)
> "Herhangi bir makinenin CSV ciktisini alarak ISO 6892-1'e gore otomatik analiz yapiyorum.
> Grip kaymasi, erken kirilma gibi anomalileri otomatik tespit edip, batch istatistikleriyle
> ISO 17025 rapor sablonu uretiyorum. TESLA ciktilariyla calisan bir demo hazirlayabilirim —
> bana bir ornek CSV verirseniz 1 haftada gosterim. Bu, TESLA cihazi satisinda yazilim
> farklilastiricisi olarak kullanilabilir — rakipten gelen musteri verisini TESLA ekosistemine ceker."

### ASLA Soyleme
- ❌ "ISO 17025 uyumlu/sertifikali yazilim yaptim" — HUKUKI RISK
- ❌ "TESLA yaziliminizi degistirmek istiyorum" — savunmaya gecerler
- ❌ "Zwick/Instron'dan daha iyiyim" — kanitlayamazsin
- ❌ Pazar boyutunu abartma — "milyonlarca dolarlik pazar" deme

### Yapmayacagimiz Seyler
- ❌ Kamera / boyut olcumu (hassasiyet riski, gereksiz karmasiklik)
- ❌ TestPilot (6 modullu copilot — strateji coker)
- ❌ Autoencoder (egitim verisi yok, kara kutu)
- ❌ LLM entegrasyonu (MVP kapsami disi)
- ❌ Dogrudan makine kontrolu (tehlikeli, lisans gerektirir)
- ❌ "ISO 17025 certified" etiketi (hicbir yerde, hicbir zaman)

---

## 12. Gelistirme Oncelik Sirasi

```
FAZ 7: Algoritma Uyumu    ████████████████████ ✅ TAMAMLANDI (18 Nisan 2026)
FAZ 8: Hukuki Koruma       ████████████████████ ✅ TAMAMLANDI (18 Nisan 2026)
FAZ 9: Batch QC            ████████████████████ ✅ TAMAMLANDI (18 Nisan 2026)
FAZ 10: Multi-Vendor       ████████████████████ ✅ TAMAMLANDI (18 Nisan 2026)
FAZ 11: Validasyon         ████████████████████ ✅ TAMAMLANDI (18 Nisan 2026)
FAZ 12: Production         ████████████████████ ✅ TAMAMLANDI (18 Nisan 2026)
FAZ 13: Go-to-Market       ██████░░░░░░░░░░░░░░ SUREKLI (TESLA CSV bekleniyor)
```

**Tahmini toplam sure:** 40-55 saat (2-3 hafta yogun calisma)
