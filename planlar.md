# CurveIntel Baseline Status

> Durum isaretleri: tamamlandi `[x]`, devam ediyor `[/]`, bekliyor `[ ]`, ortam blokaji `[!]`

---

## Mevcut Gercek Durum

- [x] Faz 2 tabani kodda var: veritabani, auth, RBAC, audit trail
- [x] Faz 3 tabani kodda var: auth/api/db testleri, coverage hedefi asildi
- [x] Web uygulamasi artik DB-authoritative calisiyor
- [x] Docker giris akisi migration-first mantigina sahip
- [x] Repo A/B/C paketlerine ayrildi ve ayri commit akislari olusturuldu
- [x] Canli Docker/PostgreSQL smoke dogrulamasi tamamlandi
- [x] Manual smoke/test scriptleri artik local absolute path icermiyor
- [x] Ayrintili durum + kullanim + operator akisi dokumani eklendi
- [x] `v2.0.0` baseline release notes taslagi eklendi
- [x] Local `origin` remote URL tokenless HTTPS formatina cekildi
- [x] GitHub `main`, `v2.0.0` tag/release ve branch protection yayina alindi
- [x] Docker/PostgreSQL smoke sirasinda yakalanan NumPy scalar persist bug'i duzeltildi

---

## Faz 1: OSS + Temel Temizlik

### 1.1 Repo Temizligi
- [x] `__pycache__`, rapor ve upload artifact temizligi
- [x] debug/test artigi dosyalarin temizlenmesi
- [x] open-source topluluk dosyalari (`LICENSE`, `CONTRIBUTING`, `SECURITY`, template'ler)

### 1.2 Kod Kalitesi
- [x] `ruff format --check .`
- [x] `ruff check .`
- [/] Pipeline tarafinda kalan TR comment/docstring borcu parcali olarak temizleniyor
- [ ] Tum pipeline modullerinde tek dil standardi tamamlanacak

### 1.3 Proje Yuzeyi
- [x] `examples/README.md`
- [x] `examples/sample_nist.csv`
- [x] `pyproject.toml` v2.0.0 metadata

### 1.4 Public Push Readiness
- [x] manual smoke scriptlerinden local Windows path'leri kaldirildi
- [x] `CURVEINTEL_DATASET_ROOT` tabanli optional dataset resolution eklendi
- [x] `docs/current_status_and_usage.md` ile gercek kullanim akisi yazildi
- [x] `docs/release_notes_v2.0.0.md` ile release body taslagi hazirlandi
- [x] local Git remote icindeki embedded token kaldirildi

---

## Faz 2: DB + Auth + Audit Baseline

### 2.1 Persistence
- [x] `src/curveintel/db/`
- [x] SQLAlchemy modelleri ve repository katmani
- [x] Alembic migration altyapisi
- [x] SQLite + PostgreSQL uyumlulugu

### 2.2 Auth + RBAC
- [x] `src/curveintel/auth/`
- [x] JWT cookie auth
- [x] bootstrap-first-admin akisi
- [x] roller: `admin`, `analyst`, `viewer`

### 2.3 Audit Trail
- [x] append-only audit log
- [x] login/register/analyze/download/delete olaylari loglaniyor
- [x] `GET /api/audit-logs` admin erisimi

### 2.4 Web Refactor
- [x] `web/app.py` RAM store yerine DB kullaniyor
- [x] `/login` sayfasi ve auth redirect akisi
- [x] dashboard persisted results ve audit paneli

---

## Faz 3: Test + CI Baseline

### 3.1 Test Durumu
- [x] `tests/test_db.py`
- [x] `tests/test_auth.py`
- [x] `tests/test_api.py`
- [x] `tests/test_postgres_smoke.py`
- [x] `pytest -q`
- [x] `pytest --cov=src --cov-report=term-missing -q`

### 3.2 CI Durumu
- [x] Ruff + pytest matrix
- [x] Docker image build + startup health check
- [x] Ayri PostgreSQL smoke job

---

## Faz 3.5: Baseline Hardening

### 3.5.1 Repo Hijyeni
- [x] `.gitignore` coverage artifactlarini kapsiyor
- [x] Mixed diff icindeki baseline-disi degisiklikler siniflandirildi
- [x] Baseline tek feature-set olarak commitlendi

### 3.5.2 Runtime Truth Alignment
- [x] README env/runtime contract gercek davranisla hizalandi
- [x] guide persistence anlatimi DB-backed modele cekildi
- [x] dashboard legal/disclaimer dili guncellendi
- [x] examples yuzeyi artik dosya gercegiyle uyumlu

### 3.5.3 Local Ops Verification
- [x] `docker compose up --build -d`
- [x] container loglarinda `alembic upgrade head` dogrulamasi
- [x] `/api/health` canli kontrolu
- [x] `/` -> `/login` redirect canli kontrolu
- [x] `/login` sayfasi canli kontrolu
- [x] canli auth/analyze/download/delete/audit smoke
- [x] PostgreSQL migration bug'i duzeltildi (`ENUM create_type=False`)
- [x] PostgreSQL enum value mapping bug'i duzeltildi (`admin` vs `ADMIN`)
- [x] Starlette template response uyumluluk bug'i duzeltildi

### 3.5.4 Commit Extraction Plani
- [x] Baseline'a girecek dosya listesi netlesti
- [x] Ikinci faza ayrilacak kalite/script/test diff'i netlesti
- [x] Sadece baseline dosyalari stage edilip tekrar gozden gecirildi
- [x] Baseline icin tek release-candidate commit hazirlandi
- [x] Follow-up pipeline kalite diff'i ayri commit olarak ele alindi

---

## Faz 4: Admin Backoffice

### 4.1 User Management
- [x] `GET /api/users`
- [x] `PATCH /api/users/{id}`
- [x] son aktif admin'i koruyan guard
- [x] dashboard icinde kullanici yonetimi tablosu

### 4.2 Audit Review Surface
- [x] action/status/actor/entity filtreleri
- [x] audit detay gorunumu (metadata + before/after snapshot)
- [x] no-data admin durumunda da audit gorunumu

### 4.3 Role-aware Dashboard
- [x] admin workspace copy
- [x] analyst workspace copy
- [x] viewer read-only workspace copy
- [x] role'e gore action ve management yuzeyi ayrimi

---

## Scope Ayrimi

### Baseline'a Ait Degisiklikler
- [x] `pyproject.toml`, `src/__init__.py`
- [x] `src/curveintel/` altindaki yeni persistence/auth/web settings modulleri
- [x] `alembic/`, `alembic.ini`
- [x] `web/app.py`, `web/templates/login.html`
- [x] `tests/test_db.py`, `tests/test_auth.py`, `tests/test_api.py`, `tests/test_postgres_smoke.py`
- [x] `tests/conftest.py`, `tests/support.py`, `tests/__init__.py`
- [x] `Dockerfile`, `docker-compose.yml`, `docker-entrypoint.sh`
- [x] `.env.example`, `.gitignore`, `.github/workflows/ci.yml`
- [x] `README.md`, `CHANGELOG.md`, `docs/vendor_integration.md`
- [x] `docs/current_status_and_usage.md`
- [x] `web/templates/dashboard.html`, `web/templates/guide.html`
- [x] `examples/README.md`, `examples/sample_nist.csv`
- [x] hardening dokumani olarak `planlar.md`

### Sonraya Ayrilmasi Gereken Karisik Diff Adaylari
- [ ] `batch_analyze.py`
- [ ] `src/models/enums.py`
- [ ] `src/pipeline/anomaly.py`
- [ ] `src/pipeline/base.py`
- [ ] `src/pipeline/batch_qc.py`
- [ ] `src/pipeline/extraction.py`
- [ ] `src/pipeline/ingestion.py`
- [ ] `src/pipeline/preprocessing.py`
- [ ] `src/pipeline/reporting.py`
- [ ] `src/pipeline/vendor_profiles.py`
- [ ] `tests/diagnostic_all_csv.py`
- [ ] `tests/test_batch_curated.py`
- [ ] `tests/test_nist.py`
- [ ] `tests/test_pipeline.py`
- [ ] `tests/test_pipeline_steps.py`
- [ ] `tests/test_report.py`
- [ ] `tests/test_useries.py`
- [ ] `tests/test_validation.py`
- [ ] Faz 1.2 kalite borcu kapsamindaki ek pipeline yorum/docstring temizlikleri

---

## Commit Paketleri

### Paket A: `baseline-hardening-v2-rc`
- [x] Amac: DB/auth/audit/web refactor'unu tek release-candidate commit olarak sabitlemek
- [x] Commit: `9be6ffa` (`Stabilize DB auth audit baseline`)
- [x] Dahil edilenler:
  `pyproject.toml`, `src/__init__.py`, `src/curveintel/**`, `alembic/**`, `alembic.ini`, `web/app.py`, `web/templates/login.html`, `web/templates/dashboard.html`, `web/templates/guide.html`, `tests/test_db.py`, `tests/test_auth.py`, `tests/test_api.py`, `tests/test_postgres_smoke.py`, `tests/conftest.py`, `tests/support.py`, `tests/__init__.py`, `Dockerfile`, `docker-compose.yml`, `docker-entrypoint.sh`, `.env.example`, `.gitignore`, `.github/workflows/ci.yml`, `README.md`, `CHANGELOG.md`, `docs/vendor_integration.md`, `examples/README.md`, `examples/sample_nist.csv`, `planlar.md`
- [x] Gate:
  `ruff check .`, `ruff format --check .`, `pytest -q`, `pytest --cov=src --cov-report=term-missing -q`, canli `docker compose` + PostgreSQL smoke zaten dogrulandi

### Paket B: `pipeline-quality-followup`
- [x] Amac: runtime-disi pipeline kalite borcunu ve manuel smoke script temizligini ayri bir degisiklik seti yapmak
- [x] Commit: `5313c18` (`Clean up pipeline quality follow-up`)
- [x] Dahil edilenler:
  `batch_analyze.py`, `src/models/enums.py`, `src/pipeline/anomaly.py`, `src/pipeline/base.py`, `src/pipeline/batch_qc.py`, `src/pipeline/extraction.py`, `src/pipeline/ingestion.py`, `src/pipeline/preprocessing.py`, `src/pipeline/reporting.py`, `src/pipeline/vendor_profiles.py`, `tests/diagnostic_all_csv.py`, `tests/test_batch_curated.py`, `tests/test_nist.py`, `tests/test_pipeline.py`, `tests/test_pipeline_steps.py`, `tests/test_report.py`, `tests/test_useries.py`, `tests/test_validation.py`
- [x] Gate:
  pipeline testlerinin ve manuel smoke script'lerinin role/runtime baseline'ini kirletmedigi tekrar dogrulanacak

### Paket C: `admin-backoffice-phase-1`
- [x] Amac: baseline sabitlendikten sonra ilk urunsel gelistirme fazina gecmek
- [x] Commit: `23ef866` (`Add admin backoffice controls`)
- [x] Hedefler:
  kullanici listeleme/yonetme, audit filtreleme ve detay gorunumu, role-aware dashboard sadelestirmesi

---

## Sonraki Mantikli Adimlar

1. PostgreSQL scalar persist fix'ini push et ve `v2.0.0` tag'ini son kapanis commit'ine tasidiktan sonra release'i guncelle.
2. GitHub repo ops'ta kalan dusuk riskli hijyen islerini kapat:
   issue labels ve 2-3 good-first-issue.
3. Istenirse local Docker disinda demo deployment hazirla.

### Uygulama Notu
- A, B ve C commitleri ayrildi; teknik baseline tamamlandi.
- GitHub release yayinda; branch protection ve CI required checks ayarlandi.
- Local Docker/PostgreSQL demo uvicorn'a gore daha gercekci kabul edildi ve bu akista dogrulandi.
- Sonraki teknik isler baseline stabilizasyonu degil, release/ops hijyeni odakli.

---

## Release Sonrasi / Ops

- [x] GitHub repo topics + description
- [x] branch protection
- [ ] issue labels ve good-first-issues
- [/] local Docker demo dogrulandi; harici demo deployment opsiyonel
- [x] `v2.0.0` tag/release stratejisi yeni baseline commit'ine gore netlestirildi
- [x] `v2.0.0` release notes taslagi hazirlandi
- [x] `v2.0.0` tag ve GitHub release yayini

---

## Kill Criteria Notu

- [x] K3 runtime tarafinda dogrulandi: PostgreSQL + audit trail + coklu vendor profili calisiyor
- [x] K3 baseline commit zinciri olusturularak kapatildi

---

**Son guncelleme:** 27 Nisan 2026 - Local Docker/PostgreSQL demo smoke gecti; NumPy scalar persist bug'i duzeltildi; GitHub release ve branch protection yayinda, kalan isler issue hijyeni ve opsiyonel harici demo deployment.
