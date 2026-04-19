"""
CurveIntel — Katman 1: Data Ingestion.

CSV dosyasını okuyup, kolon adlarını tanıyıp, birimleri dönüştüren modüller.
Giriş: ham CSV dosya yolu + kullanıcı metadata
Çıkış: AnalysisContext.stress / .strain dizileri (MPa / boyutsuz)
"""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd

from src.models.enums import MaterialType, StressStrainType
from src.pipeline.base import AnalysisContext, PipelineStep, StepResult


# ── Kolon adı eşleme sözlüğü ──
# Farklı cihaz/format/dil varyasyonlarını standart isimlere eşler
_STRESS_PATTERNS: list[re.Pattern] = [
    re.compile(r"(?i)^(eng[ineering_.\s]*)?stress.*\(?mpa\)?"),
    re.compile(r"(?i)^sigma"),
    re.compile(r"(?i)^stress"),
    re.compile(r"(?i)^Sigma_true"),
    re.compile(r"(?i)^Eng_Stress"),
    re.compile(r"(?i)^true[\s_]?stress"),
    re.compile(r"(?i)^S[\s_]?Stress"),
    re.compile(r"(?i)^[ET]stress$"),       # NIST: Estress, Tstress
    re.compile(r"(?i)^spannung"),          # Almanca: Spannung/Zugspannung
    re.compile(r"(?i)^zugspannung"),       # Almanca: ZwickRoell
    re.compile(r"(?i)^contrainte"),        # Fransizca
    re.compile(r"(?i)^gerilme"),           # Turkce: DEVOTRANS
    re.compile(r"(?i)^tensile[\s_]?stress"),  # Instron Bluehill
    re.compile(r"(?i)^axial[\s_]?stress"),    # MTS TestSuite
]

_STRAIN_PATTERNS: list[re.Pattern] = [
    re.compile(r"(?i)^(eng[ineering_.\s]*)?strain"),
    re.compile(r"(?i)^epsilon"),
    re.compile(r"(?i)^e_true"),
    re.compile(r"(?i)^Eng_Strain"),
    re.compile(r"(?i)^true[\s_]?strain"),
    re.compile(r"(?i)^strain"),
    re.compile(r"(?i)^[ET]strain$"),       # NIST: Estrain, Tstrain
    re.compile(r"(?i)^dehnung"),           # Almanca: Dehnung
    re.compile(r"(?i)^deformation"),       # Genel
    re.compile(r"(?i)^birim[\s_]?(uzama|sekil)"),  # Turkce: DEVOTRANS
    re.compile(r"(?i)^%[\s_]?uzama"),              # Turkce: % Uzama
    re.compile(r"(?i)^tensile[\s_]?strain"),  # Instron Bluehill
    re.compile(r"(?i)^axial[\s_]?strain"),    # MTS TestSuite
]

_FORCE_PATTERNS: list[re.Pattern] = [
    re.compile(r"(?i)^force"),
    re.compile(r"(?i)^load"),
    re.compile(r"(?i)^kuvvet"),             # Turkce: DEVOTRANS
    re.compile(r"(?i)^Force_\(kN\)"),
    re.compile(r"(?i)^F[\s_]?\("),
    re.compile(r"(?i)^standardkraft"),      # Almanca: ZwickRoell
    re.compile(r"(?i)^kraft"),              # Almanca: Hegewald
    re.compile(r"(?i)^prufkraft"),          # Almanca: ZwickRoell
    re.compile(r"(?i)^charge"),             # Fransizca
    re.compile(r"(?i)^carga"),              # Ispanyolca
    re.compile(r"(?i)^axial[\s_]?force"),   # MTS TestSuite
    re.compile(r"(?i)^test[\s_]?force"),    # Shimadzu EN
]

_DISPLACEMENT_PATTERNS: list[re.Pattern] = [
    re.compile(r"(?i)^displacement"),
    re.compile(r"(?i)^extension"),
    re.compile(r"(?i)^extensometer"),    # DIC extensometer
    re.compile(r"(?i)^deplasman"),       # Turkce
    re.compile(r"(?i)^crosshead"),
    re.compile(r"(?i)^position"),
    re.compile(r"(?i)^disp"),
    re.compile(r"(?i)^Displacement_"),   # NIST: Displacement_(mm)
    re.compile(r"(?i)^uzama"),           # Turkce: DEVOTRANS
    re.compile(r"(?i)^standardweg"),     # Almanca: ZwickRoell
    re.compile(r"(?i)^weg"),             # Almanca: Hegewald
    re.compile(r"(?i)^traversenweg"),    # Almanca: ZwickRoell
    re.compile(r"(?i)^traverse"),        # Almanca: ZwickRoell
    re.compile(r"(?i)^stroke"),          # Shimadzu EN
    re.compile(r"(?i)^travel"),          # Tinius Olsen
    re.compile(r"(?i)^allongement"),     # Fransizca
    re.compile(r"(?i)^axial[\s_]?displacement"),  # MTS
    re.compile(r"(?i)^grip[\s_]?separation"),     # Shimadzu EN
]

_TIME_PATTERNS: list[re.Pattern] = [
    re.compile(r"(?i)^time"),
    re.compile(r"(?i)^zeit"),            # Almanca: ZwickRoell
    re.compile(r"(?i)^prufzeit"),        # Almanca: ZwickRoell
    re.compile(r"(?i)^test[\s_]?time"),  # EN: ZwickRoell
    re.compile(r"(?i)^temps"),           # Fransizca
    re.compile(r"(?i)^zaman"),           # Turkce: DEVOTRANS
    re.compile(r"(?i)^t\s*\("),          # t (s), t (sec)
    re.compile(r"(?i)^elapsed"),
]


def _match_column(col: str, patterns: list[re.Pattern]) -> bool:
    """Kolon adının pattern listesiyle eşleşip eşleşmediğini kontrol et."""
    col_clean = col.strip()
    return any(p.search(col_clean) for p in patterns)


def _detect_separator(filepath: Path) -> str:
    """
    CSV ayracini otomatik tespit et.

    Strateji:
      1. Header + 2 veri satiri oku
      2. Tab, noktali virgul, virgul sayisini karsilastir
      3. En yuksek sayi ile ayrac sec
      4. German locale edge case: ; ayirici + , ondalik
    """
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            lines = [f.readline() for _ in range(10)]
    except Exception:
        return ","

    lines = [l for l in lines if l.strip() and not l.strip().startswith("#")]
    if not lines:
        return ","

    # Header + ilk veri satiri
    sample = "\n".join(lines[:5])

    tab_count = sample.count("\t")
    semi_count = sample.count(";")
    comma_count = sample.count(",")

    # Tab en fazlaysa tab
    if tab_count > semi_count and tab_count > comma_count:
        return "\t"
    # Noktali virgul en fazlaysa (German/Turkish locale)
    if semi_count > comma_count:
        return ";"
    return ","


def _parse_dimensions_from_filename(filename: str) -> tuple[float | None, float | None]:
    """
    Dosya adindan numune boyutlarini cikart.

    NIST format: ...T1.489W12.71.csv → thickness=1.489, width=12.71
    Genel: T<sayi>W<sayi> paterni

    Returns:
        (thickness_mm, width_mm) veya (None, None)
    """
    m = re.search(r'T(\d+\.\d+)W(\d+\.\d+)', filename)
    if m:
        return float(m.group(1)), float(m.group(2))
    return None, None


class DataLoader(PipelineStep):
    """
    CSV dosyasini oku ve AnalysisContext.raw_df'e yukle.

    Otomatik vendor tespiti, encoding ve ayrac secimi yapar.
    Yorum satirlarini (#) atlar.
    """

    def __init__(self, filepath: str | Path):
        self._filepath = Path(filepath)

    @property
    def name(self) -> str:
        return "DataLoader"

    def process(self, ctx: AnalysisContext) -> StepResult:
        if not self._filepath.exists():
            return self._failure(f"Dosya bulunamadi: {self._filepath}")

        # Vendor tespiti
        vendor_name = "Generic"
        encoding = "utf-8"
        sep = None

        try:
            from src.pipeline.vendor_profiles import (
                detect_vendor, detect_encoding,
            )
            profile = detect_vendor(self._filepath)
            if profile:
                vendor_name = profile.name
                encoding = detect_encoding(self._filepath)
                sep = profile.default_separator
                ctx.extra["vendor_profile"] = profile.name
                ctx.extra["vendor_encoding"] = encoding
        except ImportError:
            pass

        # Fallback separator
        if sep is None:
            sep = _detect_separator(self._filepath)

        # CSV oku (encoding chain ile)
        df = None
        encodings_to_try = [encoding, "utf-8", "windows-1252", "windows-1254", "latin-1"]
        # Tekrarlari kaldir
        seen = set()
        unique_encodings = []
        for e in encodings_to_try:
            if e not in seen:
                seen.add(e)
                unique_encodings.append(e)

        for enc in unique_encodings:
            try:
                df = pd.read_csv(
                    self._filepath,
                    sep=sep,
                    comment="#",
                    engine="python",
                    on_bad_lines="skip",
                    encoding=enc,
                )
                encoding = enc
                break
            except (UnicodeDecodeError, UnicodeError):
                continue
            except Exception as e:
                return self._failure(f"CSV okuma hatasi: {e}")

        if df is None or df.empty or len(df.columns) < 2:
            return self._failure("CSV bos veya yetersiz kolon iceriyor.")

        # Kolon adlarindaki fazla bosluklari temizle
        df.columns = [c.strip() for c in df.columns]

        ctx.raw_df = df
        ctx.metadata.source_file = str(self._filepath.name)

        return self._success(
            f"{len(df)} satir, {len(df.columns)} kolon yuklendi "
            f"[{vendor_name}, {encoding}]. "
            f"Kolonlar: {list(df.columns[:6])}{'...' if len(df.columns) > 6 else ''}"
        )



class SchemaDetector(PipelineStep):
    """
    Kolon adlarını analiz ederek stress/strain veya force/displacement
    kolonlarını otomatik tespit et.

    Tespit edilen kolonları ctx.extra["detected_columns"] dict'ine yazar.
    """

    @property
    def name(self) -> str:
        return "SchemaDetector"

    def process(self, ctx: AnalysisContext) -> StepResult:
        if ctx.raw_df.empty:
            return self._failure("raw_df bos -- once DataLoader calistirilmali.")

        columns = list(ctx.raw_df.columns)
        detected: dict[str, str] = {}

        # 1. Vendor column map ile esleme (varsa)
        vendor_name = ctx.extra.get("vendor_profile")
        if vendor_name:
            try:
                from src.pipeline.vendor_profiles import ALL_PROFILES
                for profile in ALL_PROFILES:
                    if profile.name == vendor_name:
                        for col in columns:
                            col_clean = col.strip()
                            # Birim parantezini kaldir: "Load (kN)" -> "Load"
                            col_base = re.sub(r"\s*\(.*\)\s*$", "", col_clean)
                            mapped = (profile.column_map.get(col_clean)
                                      or profile.column_map.get(col_base))
                            if mapped and mapped not in detected:
                                detected[mapped] = col
                        break
            except ImportError:
                pass

        # 2. Regex pattern esleme (mevcut — genel fallback)
        for col in columns:
            if _match_column(col, _STRESS_PATTERNS) and "stress" not in detected:
                detected["stress"] = col
            elif _match_column(col, _STRAIN_PATTERNS) and "strain" not in detected:
                detected["strain"] = col
            elif _match_column(col, _FORCE_PATTERNS) and "force" not in detected:
                detected["force"] = col
            elif _match_column(col, _DISPLACEMENT_PATTERNS) and "displacement" not in detected:
                detected["displacement"] = col
            elif _match_column(col, _TIME_PATTERNS) and "time" not in detected:
                detected["time"] = col

        # Extensometer'a oncelik ver (DIC verisinde daha dogru strain kaynagi)
        for col in columns:
            if re.search(r"(?i)^extensometer", col.strip()):
                detected["displacement"] = col
                break

        ctx.extra["detected_columns"] = detected


        # Zaman kolonunu ctx.extra'ya kaydet (StrainRateValidator icin)
        if "time" in detected:
            time_col = detected["time"]
            time_data = pd.to_numeric(ctx.raw_df[time_col], errors="coerce").dropna().values
            if len(time_data) > 10:
                ctx.extra["time_array"] = time_data

        # Dosya adindan boyutlari parse et (NIST format: T<thickness>W<width>)
        source = ctx.metadata.source_file
        if source:
            t, w = _parse_dimensions_from_filename(source)
            if t and w:
                if ctx.metadata.thickness_mm is None:
                    ctx.metadata.thickness_mm = t
                if ctx.metadata.width_mm is None:
                    ctx.metadata.width_mm = w
                if ctx.metadata.cross_section_area_mm2 is None:
                    ctx.metadata.cross_section_area_mm2 = t * w

        # Dosya adindan malzeme turu tespit et
        if source and ctx.metadata.material_type == MaterialType.UNKNOWN:
            fn = source.upper()
            if re.search(r"(?:DP|DUAL.?PHASE)\s*\d{3,4}", fn):
                ctx.metadata.material_type = MaterialType.STEEL_DP
            elif re.search(r"(?:AL\d|ALUM|AA\d)", fn) or "ALUMINUM" in fn or "ALUMINIUM" in fn:
                ctx.metadata.material_type = MaterialType.ALUMINUM
            elif re.search(r"(?:SS|STAINLESS|AISI\s*3\d{2}|316L|304L?)", fn):
                ctx.metadata.material_type = MaterialType.STEEL_STAINLESS
            elif re.search(r"(?:FE\w|STEEL|S\d{3}|Q\d{3})", fn):
                ctx.metadata.material_type = MaterialType.STEEL_STRUCTURAL
            elif re.search(r"(?:CFRP|COMPOSITE|CARBON.?FIBER)", fn):
                ctx.metadata.material_type = MaterialType.COMPOSITE
            elif re.search(r"(?:PLA|FKM|PDMS|POLYMER|NYLON|ABS|PETG)", fn):
                ctx.metadata.material_type = MaterialType.POLYMER

        # Stress-strain dogrudan bulundu mu?
        if "stress" in detected and "strain" in detected:
            ctx.stress_type = StressStrainType.ENGINEERING
            stress_col = detected["stress"].lower()
            if "true" in stress_col or "sigma_true" in stress_col:
                ctx.stress_type = StressStrainType.TRUE
            return self._success(
                f"Stress-strain tespit edildi: "
                f"stress='{detected['stress']}', strain='{detected['strain']}' "
                f"(tur: {ctx.stress_type.value})"
            )

        # Force-displacement bulundu mu?
        if "force" in detected and "displacement" in detected:
            ctx.stress_type = StressStrainType.RAW

            # Extensometer varsa, onu strain kaynagi olarak isaretle
            has_ext = "extensometer" in detected["displacement"].lower()

            # A0 ve L0 otomatik ayarla (yoksa)
            if ctx.metadata.cross_section_area_mm2 is None:
                # Boyut bilgisi dosya adindan parse edilemediyse
                return self._failure(
                    f"Force tespit edildi ('{detected['force']}') ancak A0 bilinmiyor. "
                    f"Dosya adindan boyut parse edilemedi."
                )

            if ctx.metadata.gauge_length_mm is None:
                # Extensometer icin standart gauge length
                if has_ext:
                    ctx.metadata.gauge_length_mm = 25.0  # NIST standart
                else:
                    ctx.metadata.gauge_length_mm = 50.0  # ASTM E8 standart

            a0 = ctx.metadata.cross_section_area_mm2
            l0 = ctx.metadata.gauge_length_mm
            ext_note = " (extensometer)" if has_ext else ""

            return self._warning(
                f"Force-displacement{ext_note} tespit edildi: "
                f"force='{detected['force']}', disp='{detected['displacement']}'. "
                f"A0={a0:.2f} mm2, L0={l0:.1f} mm (otomatik)"
            )

        # Son care: sadece Force varsa bile bildir
        if "force" in detected:
            return self._failure(
                f"Sadece force tespit edildi ('{detected['force']}'), "
                f"displacement/extensometer kolonu bulunamadi. "
                f"Mevcut: {columns[:10]}..."
            )

        return self._failure(
            f"Stress/strain veya force/displacement kolonlari bulunamadi. "
            f"Mevcut kolonlar: {columns[:10]}..."
        )


class UnitConverter(PipelineStep):
    """
    Tespit edilen kolonlardan stress (MPa) ve strain (boyutsuz) dizilerini üret.

    3 senaryo:
    1. Stress-strain zaten mevcut → doğrudan al
    2. Force-displacement mevcut → A₀, L₀ ile dönüştür
    3. Birim dönüşümü (kN→N, %strain→fraction)
    """

    @property
    def name(self) -> str:
        return "UnitConverter"

    def process(self, ctx: AnalysisContext) -> StepResult:
        detected = ctx.extra.get("detected_columns", {})
        df = ctx.raw_df

        if not detected:
            return self._failure("Kolon tespiti yapılmamış — SchemaDetector çalıştırılmalı.")

        # ── Senaryo 1: Stress-Strain doğrudan mevcut ──
        if "stress" in detected and "strain" in detected:
            stress_raw = pd.to_numeric(df[detected["stress"]], errors="coerce").dropna().values
            strain_raw = pd.to_numeric(df[detected["strain"]], errors="coerce").dropna().values

            # Uzunluk eşitle (NaN'ler farklı satırlarda olabilir)
            min_len = min(len(stress_raw), len(strain_raw))
            stress_raw = stress_raw[:min_len]
            strain_raw = strain_raw[:min_len]

            if len(stress_raw) < 10:
                return self._failure(f"Yetersiz veri noktası: {len(stress_raw)}")

            # Strain yüzde mi? (>1 ise muhtemelen yüzde)
            if np.median(strain_raw[strain_raw > 0]) > 1.0:
                strain_raw = strain_raw / 100.0

            # Stress Pa cinsinden mi? (>1e6 ise muhtemelen Pa)
            if np.median(stress_raw[stress_raw > 0]) > 1e6:
                stress_raw = stress_raw / 1e6  # Pa → MPa

            ctx.stress = stress_raw.astype(np.float64)
            ctx.strain = strain_raw.astype(np.float64)

            return self._success(
                f"{len(ctx.stress)} nokta. "
                f"Stress aralığı: {ctx.stress.min():.1f} — {ctx.stress.max():.1f} MPa, "
                f"Strain aralığı: {ctx.strain.min():.4f} — {ctx.strain.max():.4f}"
            )

        # ── Senaryo 2: Force-Displacement → Stress-Strain dönüşümü ──
        if "force" in detected and "displacement" in detected:
            a0 = ctx.metadata.cross_section_area_mm2
            l0 = ctx.metadata.gauge_length_mm

            if a0 is None or l0 is None:
                return self._failure(
                    "Force-displacement verisi var ancak A0 ve/veya L0 eksik. "
                    "Metadata'da cross_section_area_mm2 ve gauge_length_mm saglayin."
                )

            force = pd.to_numeric(df[detected["force"]], errors="coerce").dropna().values
            disp = pd.to_numeric(df[detected["displacement"]], errors="coerce").dropna().values

            min_len = min(len(force), len(disp))
            force = force[:min_len]
            disp = disp[:min_len]

            # Birim tespiti: kN ise -> N'ye cevir
            force_col_lower = detected["force"].lower()
            if "kn" in force_col_lower or np.max(np.abs(force)) < 500:
                force = force * 1000  # kN -> N

            # Extensometer ise strain = ext_value / L0
            # Displacement ise strain = disp / L0
            disp_col = detected["displacement"].lower()
            is_extensometer = "extenso" in disp_col

            # Engineering stress (MPa) = Force (N) / A0 (mm2)
            ctx.stress = (force / a0).astype(np.float64)
            # Engineering strain = dL / L0
            ctx.strain = (disp / l0).astype(np.float64)
            ctx.stress_type = StressStrainType.ENGINEERING

            src = "extensometer" if is_extensometer else "displacement"
            return self._success(
                f"Force->Stress donusumu tamamlandi ({src}). {len(ctx.stress)} nokta. "
                f"A0={a0:.2f} mm2, L0={l0} mm"
            )

        return self._failure("Donusturulebilecek veri bulunamadi.")
