# CurveIntel

**ISO 6892-1:2019 uyumlu cekme testi analiz motoru.**

CurveIntel, mekanik test cihazlarindan alinan stress-strain CSV verilerini otomatik olarak analiz eder,
mekanik ozellikleri (E, Rp0.2, Rm, At, n) hesaplar ve ISO 17025 Cl. 7.8.2.1 sartlarini karsilayan
raporlar uretir.

---

## Ozellikler

- **7 mekanik ozellik**: E, Rp0.2/ReH/ReL, Rm, At, Ag, n, Ut
- **5 anomali tespiti**: Grip kaymasi, sensor saturasyonu, gurultu, egri butunlugu, ozellik dogrulama
- **Batch QC**: Dixon Q10 + Grubbs outlier, CoV, 95% CI, SPC (Nelson 8 kuralı)
- **8 vendor destegi**: ZwickRoell, Instron, Shimadzu, MTS, Tinius Olsen, DEVOTRANS, Hegewald, NIST
- **Coklu dil**: DE, EN, JP, TR, FR, ES kolon isimleri
- **ISO 17025 uyumlu raporlama**: PDF + JSON + CSV export

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
| `/api/health` | GET | Health check |
| `/api/analyze` | POST | CSV upload + analiz |
| `/api/results` | GET | Tum sonuclar (JSON) |
| `/api/curve/{id}` | GET | Stress-strain egri verisi |

## Validasyon

```bash
# NIST referans veri seti ile dogrulama
python test_validation.py
# 96 dosya, 4 malzeme, %100 pass rate
```

## Proje Yapisi

```
curveintel/
  src/pipeline/
    base.py           # Pipeline altyapisi
    ingestion.py       # CSV okuma + vendor detection
    vendor_profiles.py # 8 vendor profili
    preprocessing.py   # Filtreleme + resampling
    extraction.py      # Mekanik ozellik hesaplama
    anomaly.py         # Anomali tespiti
    reporting.py       # PDF/JSON/CSV export
    batch_qc.py        # Istatistik + SPC
  web/
    app.py             # FastAPI backend
    templates/         # HTML sablonlari
    static/            # CSS/JS
  docs/
    algorithm_specification.md
  test_validation.py   # Regresyon test suite
  batch_analyze.py     # CLI batch analiz
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
