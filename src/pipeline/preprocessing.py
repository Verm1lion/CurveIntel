"""
CurveIntel — Katman 2: Signal Preprocessing.

Gürültü temizleme, toe region düzeltme ve resampling modülleri.
Giriş: AnalysisContext.stress / .strain (ham)
Çıkış: AnalysisContext.stress / .strain (temiz, eşit aralıklı)
"""
from __future__ import annotations

import numpy as np
from scipy.interpolate import CubicSpline, PchipInterpolator
from scipy.ndimage import median_filter
from scipy.signal import savgol_filter
from sklearn.linear_model import RANSACRegressor

from src.models.enums import AnomalyType
from src.pipeline.base import AnalysisContext, PipelineStep, StepResult


class SpikeFilter(PipelineStep):
    """
    Median filtreyle spike (anlık elektriksel sıçrama) temizleme.

    Yöntem: Orijinal sinyali median filter ile karşılaştır.
    Fark 3×σ_noise'u aşarsa → spike olarak işaretle ve median değeriyle değiştir.
    """

    def __init__(self, window_size: int = 5, threshold_sigma: float = 3.0):
        self._window = window_size
        self._threshold = threshold_sigma

    @property
    def name(self) -> str:
        return "SpikeFilter"

    def process(self, ctx: AnalysisContext) -> StepResult:
        if not ctx.has_data:
            return self._failure("Veri yok.")

        stress = ctx.stress.copy()
        median_stress = median_filter(stress, size=self._window)
        diff = np.abs(stress - median_stress)

        # Gürültü seviyesi tahmini (diff'in medianı)
        noise_level = np.median(diff[diff > 0]) if np.any(diff > 0) else 1.0
        spike_mask = diff > (self._threshold * noise_level)
        n_spikes = int(np.sum(spike_mask))

        if n_spikes > 0:
            # Spike noktalarını median değerle değiştir
            stress[spike_mask] = median_stress[spike_mask]
            ctx.stress = stress

            # Her spike'ı anomali olarak kaydet
            spike_locations = ctx.strain[spike_mask]
            for loc in spike_locations[:5]:  # İlk 5 tanesini logla
                ctx.add_anomaly(
                    anomaly_type=AnomalyType.SPIKE,
                    confidence=0.9,
                    description=f"Spike tespit edildi ve düzeltildi (strain={loc:.4f})",
                    strain_location=float(loc),
                    severity="info",
                )

            return self._warning(
                f"{n_spikes} spike tespit edildi ve median değerle değiştirildi."
            )

        return self._success("Spike bulunamadı.")


class ToeCompensation(PipelineStep):
    """
    Toe region (başlangıç oturma artefaktı) düzeltmesi — ASTM E8 Annex A1.

    Yöntem:
    1. Elastik bölgede RANSAC ile lineer fit yap
    2. Bu doğrunun strain eksenini kestiği noktayı bul (x-intercept)
    3. Strain eksenini kaydır (yeni origin)
    4. Negatif strain noktalarını kes
    """

    def __init__(
        self,
        fit_start_fraction: float = 0.10,
        fit_end_fraction: float = 0.40,
    ):
        """
        Args:
            fit_start_fraction: Stress max'ının yüzde kaçından itibaren fit başlasın
            fit_end_fraction: Stress max'ının yüzde kaçına kadar fit yapılsın
        """
        self._fit_start = fit_start_fraction
        self._fit_end = fit_end_fraction

    @property
    def name(self) -> str:
        return "ToeCompensation"

    def process(self, ctx: AnalysisContext) -> StepResult:
        if not ctx.has_data:
            return self._failure("Veri yok.")

        stress = ctx.stress
        strain = ctx.strain
        max_stress = np.max(stress)

        # Elastik bölge maskesi (stress'in %10-40'ı arası)
        mask = (stress >= max_stress * self._fit_start) & (
            stress <= max_stress * self._fit_end
        )

        if np.sum(mask) < 10:
            return self._warning(
                "Elastik bölgede yeterli veri noktası yok. "
                "Toe düzeltmesi atlandı."
            )

        X = strain[mask].reshape(-1, 1)
        y = stress[mask]

        try:
            ransac = RANSACRegressor(random_state=42)
            ransac.fit(X, y)
            slope = ransac.estimator_.coef_[0]
            intercept = ransac.estimator_.intercept_
        except Exception:
            # RANSAC başarısız olursa OLS fallback
            coeffs = np.polyfit(strain[mask], stress[mask], 1)
            slope, intercept = coeffs[0], coeffs[1]

        if slope <= 0:
            return self._warning(
                "Elastik bölge eğimi negatif veya sıfır — veri sorunu olabilir. "
                "Toe düzeltmesi atlandı."
            )

        # x-intercept (strain eksenini kestiği nokta)
        x_intercept = -intercept / slope

        # Toe region var mı kontrol et
        if abs(x_intercept) < 1e-6:
            return self._success("Toe region tespit edilmedi, düzeltme gereksiz.")

        # Strain eksenini kaydır
        new_strain = strain - x_intercept

        # Negatif strain noktalarını kes
        valid_mask = new_strain >= 0
        ctx.strain = new_strain[valid_mask]
        ctx.stress = stress[valid_mask]

        n_removed = int(np.sum(~valid_mask))

        if x_intercept > 0.001:  # Anlamlı toe region
            ctx.add_anomaly(
                anomaly_type=AnomalyType.TOE_REGION,
                confidence=0.85,
                description=(
                    f"Toe region tespit edildi (x-intercept={x_intercept:.5f}). "
                    f"Strain ekseni {x_intercept:.5f} kaydırıldı, "
                    f"{n_removed} nokta silindi."
                ),
                strain_location=0.0,
                severity="info",
            )

        # Elastik modülü extra'ya kaydet (ileride ElasticModulusDetector kullanır)
        ctx.extra["toe_elastic_slope"] = slope

        return self._success(
            f"Toe düzeltmesi uygulandı. x-intercept={x_intercept:.6f}, "
            f"{n_removed} nokta silindi."
        )


class Resampler(PipelineStep):
    """
    Eşit aralıklı strain gridine yeniden örnekleme.

    Neden: Makine verileri eşit zamanda örneklenir ama strain eşit aralıklı
    değildir. Eşit strain grid → türev hesaplamaları doğru olur.

    Yöntem:
    - CubicSpline (default): düzgün eğriler için
    - PCHIP (opsiyon): Lüders platosunda oscillasyon önler
    """

    def __init__(
        self,
        n_points: int = 2000,
        method: str = "cubic",
    ):
        self._n_points = n_points
        self._method = method

    @property
    def name(self) -> str:
        return "Resampler"

    def process(self, ctx: AnalysisContext) -> StepResult:
        if not ctx.has_data:
            return self._failure("Veri yok.")

        strain = ctx.strain
        stress = ctx.stress

        # Monotonluk kontrolü — strain monoton artmalı
        # Tekrarlanan ve geriye giden değerleri kaldır (cyclic veri desteği)
        mono_mask = np.ones(len(strain), dtype=bool)
        max_seen = strain[0]
        for i in range(1, len(strain)):
            if strain[i] > max_seen:
                max_seen = strain[i]
            else:
                mono_mask[i] = False

        strain = strain[mono_mask]
        stress = stress[mono_mask]

        # Tekrarlanan değerleri de kaldır
        _, unique_idx = np.unique(strain, return_index=True)
        unique_idx = np.sort(unique_idx)
        strain = strain[unique_idx]
        stress = stress[unique_idx]

        n_removed = ctx.n_points - len(strain)

        if len(strain) < 10:
            return self._failure("Monotonluk ve deduplikasyondan sonra yetersiz veri noktasi.")

        # Yeni eşit aralıklı grid
        new_strain = np.linspace(strain[0], strain[-1], self._n_points)

        # İnterpolasyon
        if self._method == "pchip":
            interp = PchipInterpolator(strain, stress)
        else:
            interp = CubicSpline(strain, stress)

        new_stress = interp(new_strain)

        original_n = ctx.n_points
        ctx.strain = new_strain
        ctx.stress = new_stress

        msg = f"Resampling: {original_n} -> {self._n_points} nokta ({self._method} interpolasyon)"
        if n_removed > 0:
            msg += f". {n_removed} non-monoton nokta cikarildi."
        return self._success(msg)


class SavitzkyGolayFilter(PipelineStep):
    """
    Savitzky-Golay gürültü azaltma filtresi.

    Neden: Peak değerlerini korur (moving average'dan üstün),
    türev hesabını doğrudan destekler (poly fit → analitik türev).

    Parametreler:
    - window_length=21: ~%1 eğri genişliği (2000 nokta için)
    - polyorder=3: küp polinom — kıvrımları korur
    """

    def __init__(self, window_length: int = 21, polyorder: int = 3):
        self._window = window_length
        self._polyorder = polyorder

    @property
    def name(self) -> str:
        return "SavitzkyGolayFilter"

    def process(self, ctx: AnalysisContext) -> StepResult:
        if not ctx.has_data:
            return self._failure("Veri yok.")

        # Window uzunluğu veri sayısından büyük olamaz ve tek olmalı
        window = min(self._window, len(ctx.stress))
        if window % 2 == 0:
            window -= 1
        if window < self._polyorder + 2:
            return self._warning("Veri çok kısa, SG filtresi atlandı.")

        original_max = np.max(ctx.stress)
        # Ham stress'i kaydet (UTS dual storage icin — ISO 6892-1 Cl. 3.10.1)
        ctx.extra["pre_sg_stress"] = ctx.stress.copy()
        ctx.stress = savgol_filter(ctx.stress, window, self._polyorder)
        filtered_max = np.max(ctx.stress)

        # UTS kaybı kontrolü (SG max'ı ne kadar düşürdü?)
        loss_pct = (original_max - filtered_max) / original_max * 100

        if loss_pct > 1.0:
            return self._warning(
                f"SG filtresi uygulandı (w={window}, p={self._polyorder}). "
                f"UTS peak {loss_pct:.2f}% düştü — window küçültmeyi düşünün."
            )

        return self._success(
            f"SG filtresi uygulandı (w={window}, p={self._polyorder}). "
            f"Peak kayıp: {loss_pct:.3f}%"
        )


class MonotonicityChecker(PipelineStep):
    """
    Strain serisinin monotonic artan olup olmadigini kontrol eder.

    Siklik yukleme (cyclic loading), ratcheting veya yukleme-bosaltma
    verilerini tespit eder. Bu veriler monotonic cekme testi degil,
    dolayisiyla E, Yield, UTS hesaplamalari anlamsiz sonuc uretir.

    Yontem:
    1. Strain diff serisinde negatif gecisleri (reversals) say
    2. Reversal > threshold ise → cyclic veri olarak isaretle
    3. ctx.extra["is_cyclic"] = True set ederek extraction step'lerini uyar
    """

    def __init__(self, reversal_threshold: int = 5, min_drop_ratio: float = 0.001):
        """
        Args:
            reversal_threshold: Kac reversal tespit edilirse siklik sayilir
            min_drop_ratio: Strain max'inin yuzde kaci kadar dusus reversal sayilir
        """
        self._threshold = reversal_threshold
        self._min_drop = min_drop_ratio

    @property
    def name(self) -> str:
        return "MonotonicityChecker"

    def process(self, ctx: AnalysisContext) -> StepResult:
        if not ctx.has_data:
            return self._failure("Veri yok.")

        strain = ctx.strain
        strain_range = np.max(strain) - np.min(strain)

        if strain_range <= 0:
            ctx.extra["is_cyclic"] = False
            return self._warning("Strain range sifir — veri bozuk olabilir.")

        # ── Anlamli reversal tespiti ──
        # Yontem: Running maximum'dan belirli bir oranda dusus → reversal
        # Bu, gurultu kaynakli kucuk dalgalanmalari filtreler.
        running_max = np.maximum.accumulate(strain)
        drops = running_max - strain  # Her noktada max'tan ne kadar dustuk

        # Anlamli dusus esigi: strain range'in %1'i (gurultuyu filtreler)
        significant_drop = strain_range * 0.01

        # Reversal = strain running max'tan anlamli dusup sonra tekrar yukselme
        in_reversal = drops > significant_drop
        # Reversal baslangiclarini say (False → True gecisleri)
        reversal_starts = np.diff(in_reversal.astype(int))
        n_reversals = int(np.sum(reversal_starts == 1))

        ctx.extra["is_cyclic"] = bool(n_reversals >= self._threshold)
        ctx.extra["strain_reversals"] = n_reversals

        if ctx.extra["is_cyclic"]:
            ctx.add_anomaly(
                anomaly_type=AnomalyType.NON_MONOTONIC,
                confidence=0.95,
                description=(
                    f"Siklik yukleme tespit edildi ({n_reversals} reversal). "
                    f"Monotonic cekme testi degil — property hesaplamalari atlanacak."
                ),
                severity="critical",
            )
            return self._warning(
                f"SIKLIK VERI: {n_reversals} strain reversal tespit edildi "
                f"(threshold={self._threshold}). Property extraction atlanacak."
            )

        return self._success(
            f"Monotonic veri dogrulandi ({n_reversals} minor reversal, "
            f"threshold={self._threshold})."
        )
