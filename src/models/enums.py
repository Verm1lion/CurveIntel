"""
CurveIntel enum definitions.

Malzeme türleri, akma davranışları ve anomali tipleri için
standartlaştırılmış enum değerleri.
"""
from enum import Enum, auto


class MaterialType(str, Enum):
    """Malzeme türü sınıflandırması."""
    STEEL_STRUCTURAL = "structural_steel"      # S355, S690 vb.
    STEEL_DP = "dual_phase_steel"              # DP980, DP1180
    STEEL_LOW_CARBON = "low_carbon_steel"      # Q235, AISI 1018
    STEEL_STAINLESS = "stainless_steel"        # 316L, 304
    ALUMINUM = "aluminum"                       # AA6xxx, 7075
    POLYMER = "polymer"                         # FKM, PLA, PDMS
    COMPOSITE = "composite"                     # CFRP
    UNKNOWN = "unknown"


class YieldBehavior(str, Enum):
    """Akma davranışı sınıflandırması."""
    CONTINUOUS = "continuous"           # Sürekli akma — 0.2% offset kullanılır
    DISCONTINUOUS = "discontinuous"    # Çift akma (Lüders bantları) — ReH/ReL
    UNDEFINED = "undefined"            # Henüz belirlenmedi


class AnomalyType(str, Enum):
    """Tespit edilebilecek anomali türleri."""
    GRIP_SLIPPAGE = "grip_slippage"            # Kavrama kayması
    SPIKE = "spike"                             # Elektriksel sıçrama
    PREMATURE_FRACTURE = "premature_fracture"  # Erken kırılma
    TOE_REGION = "toe_region"                   # Başlangıç oturma artefaktı
    TRUNCATION = "truncation"                   # Veri kesilmesi
    SENSOR_SATURATION = "sensor_saturation"     # Sensör saturasyonu
    HIGH_NOISE = "high_noise"                   # Yüksek gürültü
    DOUBLE_YIELD = "double_yield"               # Çift akma (anomali DEĞİL, bilgi)


class StepStatus(str, Enum):
    """Her pipeline adımının sonuç durumu."""
    SUCCESS = "success"
    WARNING = "warning"
    FAILURE = "failure"


class StressStrainType(str, Enum):
    """Stress-strain veri türü."""
    ENGINEERING = "engineering"   # Mühendislik (nominal) değerleri
    TRUE = "true"                 # Gerçek (true) değerleri
    RAW = "raw"                   # Ham kuvvet-deplasman
