"""
CurveIntel — Katman 4: Anomaly Detection.

Stress-strain egrisinde kalite problemlerini otomatik tespit eden moduller.
Hibrit yaklasim: Istatistiksel + Sinyal-tabanli + Pattern-tabanli

Tespit edilen anomaliler:
  - Grip slippage: Ani stress dususleri (kavrama kaymasi)
  - Sensor saturation: Duz plato bolgeleri (veri kaybı)
  - High noise: SNR analizi (dusuk sinyal/gurultu orani)
  - Premature fracture: Beklenen elongation'dan erken kirılma
  - Truncation: Veri kesilmesi (eksik kopma bolmesi)
  - Luders band genisligi: Cift yield durumunda bilgi
"""
from __future__ import annotations

import numpy as np
from scipy.signal import savgol_filter

from src.models.enums import AnomalyType
from src.pipeline.base import AnalysisContext, PipelineStep, StepResult


class GripSlippageDetector(PipelineStep):
    """
    Kavrama kaymasi (grip slippage) tespiti.

    Yontem:
    1. Stress turevi (dsigma/depsilon) hesapla
    2. Beklenen turev araligini belirle (elastik modul bazinda)
    3. Ani buyuk negatif turev spike'larini tespit et
       (elastik modulun 2x'inden buyuk negatif dusus)
    4. Eger dusus sonrasi stress tekrar orijinal seviyeye donuyorsa -> slippage
    """

    def __init__(self, drop_threshold: float = 0.15, recovery_pct: float = 0.80):
        self._drop_threshold = drop_threshold  # UTS'nin %'si olarak dusus esigi
        self._recovery_pct = recovery_pct      # Recovery icin gereken oran

    @property
    def name(self) -> str:
        return "GripSlippageDetector"

    def process(self, ctx: AnalysisContext) -> StepResult:
        if not ctx.has_data:
            return self._failure("Veri yok.")

        stress = ctx.stress
        strain = ctx.strain
        n = len(stress)

        if n < 50:
            return self._success("Yeterli veri yok, slippage kontrolu atlandi.")

        max_stress = np.max(stress)
        min_drop = max_stress * self._drop_threshold

        # Stress farkini hesapla (ardisik noktalar arasi)
        stress_diff = np.diff(stress)

        slippage_count = 0
        slippage_locations: list[float] = []

        i = 0
        while i < len(stress_diff):
            # Buyuk negatif dusus tespit et
            if stress_diff[i] < -min_drop:
                drop_start = i
                drop_magnitude = abs(stress_diff[i])
                pre_drop_stress = stress[i]

                # Recovery kontrolu: dusus sonrasi stress geri donuyor mu?
                search_end = min(i + 50, n - 1)
                post_region = stress[i + 1 : search_end]

                if len(post_region) > 0:
                    max_recovery = np.max(post_region)
                    recovery_ratio = max_recovery / pre_drop_stress if pre_drop_stress > 0 else 0

                    if recovery_ratio >= self._recovery_pct:
                        slippage_count += 1
                        loc = float(strain[drop_start])
                        slippage_locations.append(loc)
                        ctx.add_anomaly(
                            anomaly_type=AnomalyType.GRIP_SLIPPAGE,
                            confidence=min(0.95, recovery_ratio),
                            description=(
                                f"Kavrama kaymasi: strain={loc:.4f}, "
                                f"dusus={drop_magnitude:.1f} MPa, "
                                f"recovery={recovery_ratio * 100:.0f}%"
                            ),
                            strain_location=loc,
                            severity="warning",
                        )
                        i = search_end  # Bu bolgeyi atla
                        continue
            i += 1

        if slippage_count == 0:
            return self._success("Kavrama kaymasi tespit edilmedi.")

        return self._warning(
            f"{slippage_count} kavrama kaymasi tespit edildi. "
            f"Konumlar: {[f'{s:.4f}' for s in slippage_locations[:5]]}"
        )


class SensorSaturationDetector(PipelineStep):
    """
    Sensor saturasyonu tespiti — duz plato bolgeleri.

    Yontem:
    1. Rolling window ile yerel standart sapma hesapla
    2. Standart sapma ~ 0 olan uzun bolgeler = saturasyon
    3. Bu bolgeler verinin gercek davranisini yansitmiyor olabilir

    ASTM notu: Stress platosu (Luders) ile saturasyonu ayirt etmek icin
    strain araligi kontrolu yapilir.
    """

    def __init__(self, window: int = 30, std_threshold: float = 0.5, min_length: int = 20):
        self._window = window
        self._std_threshold = std_threshold
        self._min_length = min_length

    @property
    def name(self) -> str:
        return "SensorSaturationDetector"

    def process(self, ctx: AnalysisContext) -> StepResult:
        if not ctx.has_data:
            return self._failure("Veri yok.")

        stress = ctx.stress
        strain = ctx.strain
        n = len(stress)

        if n < self._window * 2:
            return self._success("Veri yetersiz — saturasyon kontrolu atlandi.")

        # Rolling standart sapma
        rolling_std = np.array([
            np.std(stress[max(0, i - self._window // 2):i + self._window // 2])
            for i in range(n)
        ])

        # Cok dusuk standart sapma bolgeleri bul
        flat_mask = rolling_std < self._std_threshold

        # Ardisik duz bolgeleri grupla
        saturation_regions = []
        region_start = None
        for i in range(n):
            if flat_mask[i]:
                if region_start is None:
                    region_start = i
            else:
                if region_start is not None and (i - region_start) >= self._min_length:
                    saturation_regions.append((region_start, i - 1))
                region_start = None

        # Son bolge kontrolu
        if region_start is not None and (n - region_start) >= self._min_length:
            saturation_regions.append((region_start, n - 1))

        # Luders platosu ayrimi: yield bolgesi civarisindaysa anomali DEGIL
        yield_strain = ctx.extra.get("yield_strain", 0)
        true_saturations = []

        for start, end in saturation_regions:
            region_strain_start = strain[start]
            region_strain_end = strain[end]
            # Yield civarinda degilse -> gercek saturasyon
            if not (region_strain_start < yield_strain * 2 and
                    region_strain_end < yield_strain * 3):
                true_saturations.append((start, end))
                ctx.add_anomaly(
                    anomaly_type=AnomalyType.SENSOR_SATURATION,
                    confidence=0.85,
                    description=(
                        f"Sensor saturasyonu: strain={region_strain_start:.4f}-"
                        f"{region_strain_end:.4f}, uzunluk={end - start + 1} nokta"
                    ),
                    strain_location=float(region_strain_start),
                    severity="warning",
                )

        if not true_saturations:
            return self._success("Sensor saturasyonu tespit edilmedi.")

        return self._warning(
            f"{len(true_saturations)} saturasyon bolgesi tespit edildi."
        )


class NoiseAnalyzer(PipelineStep):
    """
    Sinyal-gurultu orani (SNR) analizi.

    Yontem:
    1. Orijinal sinyal ile SG-filtered sinyal arasindaki farki hesapla
    2. Fark = gurultu tahmini
    3. SNR = 20 * log10(RMS_signal / RMS_noise) dB
    4. SNR < 20 dB -> yuksek gurultu uyarisi
    """

    def __init__(self, snr_threshold_db: float = 20.0):
        self._snr_threshold = snr_threshold_db

    @property
    def name(self) -> str:
        return "NoiseAnalyzer"

    def process(self, ctx: AnalysisContext) -> StepResult:
        if not ctx.has_data:
            return self._failure("Veri yok.")

        stress = ctx.stress
        n = len(stress)

        if n < 30:
            return self._success("Veri yetersiz — gurultu analizi atlandi.")

        # SG filtresi ile yumusatilmis sinyal
        window = min(51, n)
        if window % 2 == 0:
            window -= 1
        if window < 5:
            return self._success("Veri yetersiz — gurultu analizi atlandi.")

        smooth = savgol_filter(stress, window_length=window, polyorder=3)
        noise = stress - smooth

        rms_signal = np.sqrt(np.mean(stress ** 2))
        rms_noise = np.sqrt(np.mean(noise ** 2))

        if rms_noise < 1e-10:
            snr_db = 100.0  # Pratik olarak sonsuz SNR
        else:
            snr_db = 20 * np.log10(rms_signal / rms_noise)

        noise_pct = (rms_noise / rms_signal * 100) if rms_signal > 0 else 0

        ctx.extra["snr_db"] = snr_db
        ctx.extra["noise_rms_mpa"] = float(rms_noise)
        ctx.extra["noise_pct"] = noise_pct

        if snr_db < self._snr_threshold:
            ctx.add_anomaly(
                anomaly_type=AnomalyType.HIGH_NOISE,
                confidence=min(0.95, 1 - snr_db / self._snr_threshold),
                description=(
                    f"Yuksek gurultu: SNR={snr_db:.1f} dB "
                    f"(esik={self._snr_threshold:.0f} dB), "
                    f"RMS noise={rms_noise:.2f} MPa ({noise_pct:.1f}%)"
                ),
                severity="warning",
            )
            return self._warning(
                f"SNR={snr_db:.1f} dB (esik alti). "
                f"Gurultu: {rms_noise:.2f} MPa ({noise_pct:.1f}%)"
            )

        return self._success(
            f"SNR={snr_db:.1f} dB (iyi). "
            f"Gurultu: {rms_noise:.2f} MPa ({noise_pct:.1f}%)"
        )


class CurveIntegrityChecker(PipelineStep):
    """
    Egri butunluk kontrolu — kesilme, erken kirilma, monotonluk.

    Kontroller:
    1. Kopma noktasi var mi? (Stress sifira dusuyor mu?)
    2. Eger E ve UTS biliniyorsa, beklenen elongation hesapla
    3. Gercek elongation << beklenen -> premature fracture
    4. Veri son noktasi hala yuksek stress -> truncation
    """

    @property
    def name(self) -> str:
        return "CurveIntegrityChecker"

    def process(self, ctx: AnalysisContext) -> StepResult:
        if not ctx.has_data:
            return self._failure("Veri yok.")

        stress = ctx.stress
        strain = ctx.strain
        uts = ctx.properties.ultimate_tensile_mpa
        findings: list[str] = []

        # ── Kontrol 1: Truncation tespiti ──
        # Son %5'lik bolgenin ortalama stresi UTS'nin %50'sinden buyukse -> truncation
        if uts and uts > 0:
            tail_size = max(10, len(stress) // 20)
            tail_mean = np.mean(stress[-tail_size:])
            tail_ratio = tail_mean / uts

            if tail_ratio > 0.50:
                ctx.add_anomaly(
                    anomaly_type=AnomalyType.TRUNCATION,
                    confidence=min(0.90, tail_ratio),
                    description=(
                        f"Veri kesilmesi: Son bolge stresi={tail_mean:.1f} MPa "
                        f"(UTS'nin {tail_ratio * 100:.0f}%'i). "
                        f"Kopma bolgesi eksik olabilir."
                    ),
                    strain_location=float(strain[-1]),
                    severity="warning",
                )
                findings.append(f"truncation (tail={tail_ratio * 100:.0f}%)")

        # ── Kontrol 2: Premature fracture tespiti ──
        # Elongation < 2% ve UTS > 200 MPa -> suphe
        elongation = ctx.properties.elongation_at_break_pct
        if elongation and uts and elongation < 2.0 and uts > 200:
            ctx.add_anomaly(
                anomaly_type=AnomalyType.PREMATURE_FRACTURE,
                confidence=0.70,
                description=(
                    f"Olasi erken kirilma: Elongation={elongation:.1f}% "
                    f"(UTS={uts:.0f} MPa icin beklenenden dusuk)"
                ),
                strain_location=float(strain[-1]),
                severity="warning",
            )
            findings.append(f"premature fracture (elong={elongation:.1f}%)")

        # ── Kontrol 3: Negatif stress bolgeleri ──
        neg_ratio = np.sum(stress < 0) / len(stress)
        if neg_ratio > 0.10:
            findings.append(f"negatif stress orani={neg_ratio * 100:.0f}%")

        if not findings:
            return self._success("Egri butunlugu iyi — anomali yok.")

        return self._warning(f"Bulgular: {', '.join(findings)}")


class PropertyValidator(PipelineStep):
    """
    Hesaplanan mekanik ozelliklerin fiziksel tutarliligini dogrula.

    Kontrollar:
    1. E degeri makul aralikta mi? (1-600 GPa)
    2. Yield < UTS mi?
    3. Uniform elongation < total elongation mi?
    4. n degeri makul aralikta mi? (0.01 — 1.0)
    5. Tokluk pozitif mi?
    """

    @property
    def name(self) -> str:
        return "PropertyValidator"

    def process(self, ctx: AnalysisContext) -> StepResult:
        p = ctx.properties
        issues: list[str] = []

        # E kontrolu
        if p.elastic_modulus_gpa is not None:
            if not (1 <= p.elastic_modulus_gpa <= 600):
                issues.append(
                    f"E={p.elastic_modulus_gpa:.1f} GPa -> makul aralik disi (1-600)"
                )

        # Yield < UTS kontrolu
        if p.yield_strength_mpa and p.ultimate_tensile_mpa:
            if p.yield_strength_mpa > p.ultimate_tensile_mpa * 1.05:
                issues.append(
                    f"Yield ({p.yield_strength_mpa:.0f}) > UTS ({p.ultimate_tensile_mpa:.0f}) "
                    f"-> fiziksel olarak tutarsiz"
                )

        # Uniform < Total elongation
        if p.uniform_elongation_pct and p.elongation_at_break_pct:
            if p.uniform_elongation_pct > p.elongation_at_break_pct * 1.1:
                issues.append(
                    f"Uniform elong ({p.uniform_elongation_pct:.1f}%) > "
                    f"Total elong ({p.elongation_at_break_pct:.1f}%) -> tutarsiz"
                )

        # n degeri
        if p.strain_hardening_n is not None:
            if not (0.01 <= p.strain_hardening_n <= 1.0):
                issues.append(
                    f"n={p.strain_hardening_n:.3f} -> makul aralik disi (0.01-1.0)"
                )

        # Tokluk
        if p.toughness_mj_m3 is not None and p.toughness_mj_m3 <= 0:
            issues.append(f"Tokluk={p.toughness_mj_m3:.2f} MJ/m3 -> negatif/sifir")

        if not issues:
            return self._success("Tum mekanik ozellikler fiziksel olarak tutarli.")

        for issue in issues:
            ctx.add_anomaly(
                anomaly_type=AnomalyType.SPIKE,  # Genel kalite uyarisi
                confidence=0.75,
                description=f"Ozellik dogrulama: {issue}",
                severity="warning",
            )

        return self._warning(f"{len(issues)} tutarsizlik: {'; '.join(issues)}")
