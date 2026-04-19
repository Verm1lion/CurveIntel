# CurveIntel

**ISO 6892-1:2019 uyumlu cekme testi analiz motoru.**

CurveIntel, mekanik test cihazlarindan alinan stress-strain CSV verilerini otomatik olarak analiz eder,
mekanik ozellikleri (E, Rp0.2, Rm, At, n) hesaplar ve ISO 17025 Cl. 7.8.2.1 sartlarini karsilayan
raporlar uretir.

---

## Ozellikler

- **7 mekanik ozellik**: E, Rp0.2/ReH/ReL, Rm, At, Ag, n, Ut
- **5 anomali tespiti**: Grip kaymasi, sensor saturasyonu, gurultu, egri butunlugu, ozellik dogrulama
- **Siklik veri tespiti**: MonotonicityChecker ile cyclic/ratcheting dosyalar otomatik tespit edilir
- **Batch QC**: Dixon Q10 + Grubbs outlier, CoV, 95% CI, SPC (Nelson 8 kurali)
- **8 vendor destegi**: ZwickRoell, Instron, Shimadzu, MTS, Tinius Olsen, DEVOTRANS, Hegewald, NIST
- **Coklu dil**: DE, EN, JP, TR, FR, ES kolon isimleri
- **ISO 17025 uyumlu raporlama**: PDF (grafik + anomali + pipeline log + imza alani) + JSON + CSV export
- **5 kademeli kalite skoru**: A+ (Mukemmel) → D (Guvenilmez)

## Hizli Baslangic

### 1. Kurulum (pip)

```bash
pip install numpy scipy pandas scikit-learn matplotlib fastapi uvicorn jinja2 python-multipart reportlab
```

### 2. Tek Dosya Analizi

```python
from pathlib import Path
from batch_analyze import build_pipeline, analyze_single

csv = Path("numune.csv")
ctx = analyze_single(csv, Path("reports/"))
print(f"Rm = {ctx.properties.ultimate_tensile_mpa:.1f} MPa")
```

### 3. Web Dashboard

```bash
cd curveintel
uvicorn web.app:app --reload
# http://localhost:8000
```

### 4. Batch Analiz

```bash
python batch_analyze.py /path/to/csv/dizini
```

### 5. Docker

```bash
docker compose up -d
# http://localhost:8000
```

## Pipeline Adimlari

```
CSV Dosyasi
  → DataLoader (encoding/separator auto-detect)
  → SchemaDetector (vendor profil eslesme)
  → UnitConverter (kN→MPa, mm→strain)
  → SpikeFilter (median filtre)
  → MonotonicityChecker (siklik veri tespiti)
  → ToeCompensation (bas bolge duzeltme)
  → Resampler (2000 nokta)
  → SavitzkyGolayFilter (gurultu azaltma)
  → ElasticModulusDetector (OLS / Chord)
  → YieldDetector (0.2% offset / ReH-ReL)
  → UTSDetector (max stress)
  → ElongationDetector (At / Ag)
  → NeckingDetector (Considere kriteri)
  → StrainHardeningFitter (Hollomon n-K)
  → ToughnessCalculator (trapez integral)
  → GripSlippageDetector
  → SensorSaturationDetector
  → NoiseAnalyzer (SNR)
  → CurveIntegrityChecker (truncation)
  → PropertyValidator (fiziksel tutarlilik)
→ PDF Rapor (ISO 17025 sablonu)
```

## Kalite Skoru

| Skor | Grade | Anlami |
|------|-------|--------|
| >= 85 | **A+ (Mukemmel)** | Yuksek guvenilirlik, dogrudan kullanilabilir |
| >= 70 | **A (Iyi)** | Guvenilir sonuclar |
| >= 55 | **B (Dikkatle Kullanilabilir)** | Bazi sorunlar mevcut |
| >= 40 | **C (Dusuk Guvenilirlik)** | Dogrulama gerekli |
| < 40 | **D (Guvenilmez)** | Kullanilmamali |

## Desteklenen CSV Formatlari

| Vendor | Profil | Encoding | Ayirici |
|--------|--------|----------|---------|
| ZwickRoell testXpert II/III | 25 kolon (DE/EN) | CP1252 | ; |
| Instron Bluehill Universal | 34 kolon (multi-lang) | UTF-8/16 | , |
| Shimadzu Trapezium X | 31 kolon (JP/EN) | Shift-JIS | , |
| MTS TestSuite | 9 kolon | UTF-8 | tab |
| Tinius Olsen Horizon | 12 kolon | CP1252 | , |
| DEVOTRANS CKS-III | 13 kolon (TR) | CP1254 | ; |
| Hegewald & Peschke | 14 kolon (DE) | CP1252 | ; |
| NIST Numisheet | 5 kolon | UTF-8 | , |
| Generic CSV | auto-detect | auto | auto |

## API Endpoints

| Endpoint | Method | Aciklama |
|----------|--------|----------|
| `/` | GET | Dashboard (HTML) |
| `/guide` | GET | Kullanim Kilavuzu (HTML) |
| `/api/health` | GET | Health check |
| `/api/analyze` | POST | CSV upload + analiz |
| `/api/results` | GET | Tum sonuclar (JSON) |
| `/api/report/{id}/pdf` | GET | ISO PDF rapor indirme |
| `/api/results/{id}` | DELETE | Tek sonuc silme |
| `/api/results/clear` | DELETE | Tum sonuclari temizle |

## Validasyon (472 Dosya Audit)

```
FULL_RESULT:    208 (%44.1)  — Basarili monotonic analiz
CYCLIC:         243 (%51.5)  — Siklik veri (dogru tespit, atlanma)
NO_DATA:         21 (%4.4)   — Metadata dosyalari
ERROR:            0 (%0.0)   — Sifir crash
```

## Proje Yapisi

```
curveintel/
  src/
    pipeline/
      base.py              # Pipeline altyapisi + AnalysisContext
      ingestion.py          # CSV okuma + vendor detection
      vendor_profiles.py    # 8 vendor profili
      preprocessing.py      # Filtreleme + resampling + MonotonicityChecker
      extraction.py         # 7 mekanik ozellik hesaplama
      anomaly.py            # 5 anomali dedektoru
      reporting.py          # PDF rapor (grafik + anomali + pipeline log)
      batch_qc.py           # Istatistik + SPC
    models/
      enums.py              # AnomalyType, StressType, MaterialType
  web/
    app.py                  # FastAPI backend
    templates/
      dashboard.html        # Ana dashboard
      guide.html            # Animasyonlu kullanim kilavuzu
    static/                 # CSS/JS
  tests/
    diagnostic_all_csv.py   # 472 dosya audit script
  docs/
    algorithm_specification.md
  batch_analyze.py          # CLI batch analiz
  Dockerfile
  docker-compose.yml
  CHANGELOG.md
```

## Lisans

Proprietary - Tum haklari saklidir.

## Hukuki Not

> Bu yazilim ISO/IEC 17025:2017 Madde 7.11 (Veri Kontrolu ve Bilgi Yonetimi)
> gereksinimlerini karsilayacak altyapi ile tasarlanmistir.
> Akredite bir test laboratuvari degildir, akreditasyon vermez ve
> akreditasyon kuruluslari tarafindan onaylanmamistir.
