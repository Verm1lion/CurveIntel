"""
CurveIntel — Katman 3: Feature Extraction (ISO 6892-1:2019 uyumlu).

Stress-strain egrisinden mekanik ozellikleri otomatik hesaplayan moduller.
Giris: AnalysisContext.stress / .strain (temiz, esit aralikli)
Cikis: AnalysisContext.properties (MechanicalProperties)

Hesaplanan ozellikler:
  - E (GPa): Elastik modul — OLS birincil, RANSAC on-filtre (Annex G)
  - Rp0.2 / ReH / ReL (MPa): Akma dayanimi — ISO A.3.2 iki-kosullu test
  - UTS / Rm (MPa): Cekme dayanimi — SG filtrelenmis max + dual storage
  - At (%): Toplam uzama (kirilmada) — Annex A.3.6.1 force-drop
  - Ag (%): Uniform elongation — Considere kriteri
  - n: Strain hardening eksponani (Hollomon, ISO 10275)
  - Ut (MJ/m3): Modulus of toughness (supplementary)
"""
from __future__ import annotations

import numpy as np
from scipy.signal import savgol_filter
from sklearn.linear_model import RANSACRegressor

from src.models.enums import AnomalyType, YieldBehavior
from src.pipeline.base import AnalysisContext, PipelineStep, StepResult


class ElasticModulusDetector(PipelineStep):
    """
    Elastik modul (E) hesaplama — ISO 6892-1:2019 Annex G uyumlu.

    Yontem (3/3 AI capraz dogrulama ile kesinlesmis):
    1. Yield referans tohum: 0.8 × Rm (dairesel bagimlilik cozumu, §G.5.1)
    2. Pencere: R1 = 10% × yield_ref, R2 = 40% × yield_ref
    3. RANSAC on-filtre: toe/slip noktalarini temizle → inlier maskesi
    4. OLS (scipy.stats.linregress) birincil fit, inlier'lar uzerinde
    5. ISO kalite kapilari: R² ≥ 0.9995, Sm(rel) < 1%, N ≥ 50
    6. Fail durumunda: Sliding window (stride=1, N≥50)
    7. Iteratif E ↔ Rp0.2 guncelleme (max 4 iterasyon)

    ONEMLI: R2 ust siniri %40 (Gemini'nin %50 iddiasi HATALI, Opus+ChatGPT dogruladi)

    Referanslar:
    - ISO 6892-1:2019 Annex G §G.3.1.3 (N ≥ 50)
    - ISO 6892-1:2019 Annex G §G.5.1 (R1/R2 tanimlari)
    - ISO 6892-1:2019 Annex G §G.6.2 (R², Sm(rel) kabul kriterleri)
    """

    def __init__(
        self,
        r1_fraction: float = 0.10,    # %10 yield_ref
        r2_fraction: float = 0.40,    # %40 yield_ref (Annex G)
        min_n_points: int = 50,        # §G.3.1.3
        min_r2: float = 0.9995,        # §G.6.2
        max_sm_rel: float = 1.0,       # §G.6.2 (%)
        max_iterations: int = 4,       # E ↔ Rp0.2 iterasyon limiti
        convergence_tol: float = 1e-4, # Yakinlasma toleransi
    ):
        self._r1_frac = r1_fraction
        self._r2_frac = r2_fraction
        self._min_n = min_n_points
        self._min_r2 = min_r2
        self._max_sm_rel = max_sm_rel
        self._max_iter = max_iterations
        self._tol = convergence_tol

    @property
    def name(self) -> str:
        return "ElasticModulusDetector"

    def process(self, ctx: AnalysisContext) -> StepResult:
        if not ctx.has_data:
            return self._failure("Veri yok.")

        stress = ctx.stress
        strain = ctx.strain
        max_stress = np.max(stress)

        # Yield referans tohum: 0.8 × Rm (dairesel bagimlilik cozumu)
        yield_ref = max_stress * 0.8

        best_result = None

        for iteration in range(self._max_iter):
            # R1/R2 penceresi
            r1_stress = yield_ref * self._r1_frac
            r2_stress = yield_ref * self._r2_frac

            # Pencere maskesi
            mask = (stress >= r1_stress) & (stress <= r2_stress)
            n_points = int(np.sum(mask))

            # N ≥ 50 kontrolu (§G.3.1.3)
            if n_points < self._min_n:
                if best_result is None:
                    # Dogrudan max_stress-tabanli fallback dene
                    mask = (stress >= max_stress * 0.05) & (stress <= max_stress * 0.40)
                    n_points = int(np.sum(mask))
                    if n_points < 10:
                        return self._failure(
                            f"ISO 6892-1 G.3.1.3 Ihlali: N={n_points} < 50. "
                            "Degerlendirme araliginda yeterli veri noktasi yok."
                        )
                else:
                    break

            X_window = strain[mask]
            y_window = stress[mask]

            # RANSAC on-filtre: toe/slip noktalarini temizle
            try:
                ransac = RANSACRegressor(random_state=42)
                ransac.fit(X_window.reshape(-1, 1), y_window)
                inlier_mask = ransac.inlier_mask_
                ransac_slope = float(ransac.estimator_.coef_[0])
            except Exception:
                inlier_mask = np.ones(len(X_window), dtype=bool)
                ransac_slope = None

            # OLS birincil fit — inlier'lar uzerinde
            X_ols = X_window[inlier_mask]
            y_ols = y_window[inlier_mask]
            n_ols = len(X_ols)

            if n_ols < 10:
                # Inlier'lar cok az, tum pencereyi kullan
                X_ols = X_window
                y_ols = y_window
                n_ols = len(X_ols)

            from scipy.stats import linregress
            result = linregress(X_ols, y_ols)
            slope = result.slope
            intercept = result.intercept
            r2 = result.rvalue ** 2
            sm_rel = (result.stderr / abs(slope) * 100) if slope != 0 else float("inf")

            current_result = {
                "slope": slope,
                "intercept": intercept,
                "r2": r2,
                "sm_rel": sm_rel,
                "n_points": n_ols,
                "r1_mpa": r1_stress,
                "r2_mpa": r2_stress,
                "ransac_slope": ransac_slope,
                "iteration": iteration,
            }

            # En iyi sonucu guncelle
            if best_result is None or r2 > best_result["r2"]:
                best_result = current_result

            # Yakinlasma kontrolu: E → Rp0.2 → R1/R2 → E
            if slope > 0:
                # Geçici Rp0.2: offset cizgisi kesisimi
                offset_line = slope * (strain - 0.002)
                diff = stress - offset_line
                sign_changes = np.where(np.diff(np.sign(diff)) < 0)[0]

                if len(sign_changes) > 0:
                    idx = sign_changes[0]
                    d0, d1 = diff[idx], diff[idx + 1]
                    frac = d0 / (d0 - d1) if (d0 - d1) != 0 else 0.5
                    new_yield_ref = float(
                        stress[idx] + frac * (stress[idx + 1] - stress[idx])
                    )

                    # Yakinlasma testi
                    if abs(new_yield_ref - yield_ref) / max(yield_ref, 1e-6) < self._tol:
                        break
                    yield_ref = new_yield_ref
                else:
                    break
            else:
                break

        if best_result is None:
            return self._failure("E modulu hesaplanamadi.")

        slope = best_result["slope"]
        r2 = best_result["r2"]
        sm_rel = best_result["sm_rel"]
        n_ols = best_result["n_points"]

        # ISO kalite kapilari: sliding window fallback
        if r2 < self._min_r2 or sm_rel > self._max_sm_rel:
            sw_result = self._sliding_window_fit(stress, strain, yield_ref)
            if sw_result is not None and sw_result["r2"] > r2:
                best_result = sw_result
                slope = sw_result["slope"]
                r2 = sw_result["r2"]
                sm_rel = sw_result["sm_rel"]
                n_ols = sw_result["n_points"]

        e_gpa = slope / 1000  # MPa -> GPa

        # Sonuclari kaydet
        ctx.properties.elastic_modulus_gpa = e_gpa
        ctx.extra["elastic_slope_mpa"] = slope
        ctx.extra["elastic_intercept_mpa"] = best_result["intercept"]
        ctx.extra["elastic_r2"] = r2
        ctx.extra["elastic_sm_rel"] = sm_rel
        ctx.extra["elastic_n_points"] = n_ols
        ctx.extra["elastic_r1_mpa"] = best_result["r1_mpa"]
        ctx.extra["elastic_r2_mpa"] = best_result["r2_mpa"]
        ctx.extra["elastic_ols_slope"] = slope
        ctx.extra["elastic_ransac_slope"] = best_result["ransac_slope"]
        ctx.extra["elastic_iterations"] = best_result["iteration"] + 1

        # Method tag
        ctx.properties.method_tags["elastic_modulus"] = (
            "per ISO 6892-1:2019 Annex G, OLS primary"
        )

        # Kalite degerlendirmesi
        if r2 >= self._min_r2 and sm_rel <= self._max_sm_rel:
            quality = "ISO uyumlu"
        elif r2 >= 0.999:
            quality = "kabul edilebilir"
        else:
            quality = "dusuk — kontrol edin"

        return self._success(
            f"E = {e_gpa:.1f} GPa (R2={r2:.6f}, Sm(rel)={sm_rel:.2f}%, "
            f"N={n_ols}, iter={best_result['iteration']+1}, kalite: {quality})"
        )

    def _sliding_window_fit(
        self,
        stress: np.ndarray,
        strain: np.ndarray,
        yield_ref: float,
    ) -> dict | None:
        """
        Sliding window fallback — ISO Annex G "recalculation with other limits".

        %5 - %60 yield_ref aralığında N=50 genisliginde pencere kaydirarak
        en iyi Sm(rel)'i minimize eden bolgeyi bul.
        """
        from scipy.stats import linregress

        sw_start = yield_ref * 0.05
        sw_end = yield_ref * 0.60

        window_mask = (stress >= sw_start) & (stress <= sw_end)
        indices = np.where(window_mask)[0]

        if len(indices) < self._min_n:
            return None

        best = None
        window_size = self._min_n

        for start in range(0, len(indices) - window_size + 1, 1):
            end = start + window_size
            idx_slice = indices[start:end]

            X_w = strain[idx_slice]
            y_w = stress[idx_slice]

            try:
                res = linregress(X_w, y_w)
                r2 = res.rvalue ** 2
                sm_rel = (res.stderr / abs(res.slope) * 100) if res.slope != 0 else float("inf")

                if best is None or sm_rel < best["sm_rel"]:
                    best = {
                        "slope": res.slope,
                        "intercept": res.intercept,
                        "r2": r2,
                        "sm_rel": sm_rel,
                        "n_points": window_size,
                        "r1_mpa": float(y_w[0]),
                        "r2_mpa": float(y_w[-1]),
                        "ransac_slope": None,
                        "iteration": 0,
                    }
            except Exception:
                continue

        return best


class YieldDetector(PipelineStep):
    """
    Akma dayanimi (Yield) hesaplama — ISO 6892-1:2019 Annex A.3.2 uyumlu.

    Strateji (3/3 AI capraz dogrulama ile kesinlesmis):
    1. ISO A.3.2 iki-kosullu state machine ile sureksiz akma (ReH/ReL) testi:
       - Kosul 1: Kuvvette >= %0.5 dusus
       - Kosul 2: Dusus sonrasi >= %0.05 strain penceresinde onceki maks asilmamali
    2. Iki kosul birlikte saglanirsa -> discontinuous yielding (ReH, ReL, Ae)
    3. Test boyunca hic saglanmazsa -> continuous yielding -> Rp0.2 (0.2% offset)

    ReL tespiti:
    - Transient maskeleme: ReH sonrasi ilk transient_mask_strain kadar bolge atlanir
    - Standart sayisal esik VERMIYOR — vendor rule olarak saklanir
    - Maskeleme sonrasi Luders platosu boyunca minimum = ReL

    Referanslar:
    - ISO 6892-1:2019 Annex A.3.2 (ReH iki-kosullu test)
    - ISO 6892-1:2019 Cl. 13.1 (Rp0.2 parallel-line offset)
    - ISO 6892-1:2019 Cl. 12 (ReL kisayolu, opsiyonel)
    """

    def __init__(
        self,
        offset: float = 0.002,
        drop_threshold: float = 0.005,       # >= %0.5 kuvvet dususu
        window_strain: float = 0.0005,        # >= %0.05 strain penceresi
        transient_mask_strain: float = 0.0005, # %0.05 transient maskeleme
        use_clause12_shortcut: bool = False,   # Cl.12 ReL kisayolu
        clause12_window: float = 0.0025,       # %0.25 strain (Cl.12)
    ):
        self._offset = offset
        self._drop_threshold = drop_threshold
        self._window_strain = window_strain
        self._transient_mask = transient_mask_strain
        self._use_clause12 = use_clause12_shortcut
        self._clause12_window = clause12_window

    @property
    def name(self) -> str:
        return "YieldDetector"

    def process(self, ctx: AnalysisContext) -> StepResult:
        if not ctx.has_data:
            return self._failure("Veri yok.")

        stress = ctx.stress
        strain = ctx.strain

        # ── Adim 1: ISO A.3.2 Iki-Kosullu State Machine ──
        reh_result = self._find_reh(stress, strain)

        if reh_result is not None:
            reh_value, reh_idx = reh_result

            # ── Adim 2: ReL Tespiti ──
            rel_value, rel_idx, rel_method = self._find_rel(
                stress, strain, reh_idx
            )

            # ── Adim 3: Ae (Luders uzamasi) tahmini ──
            ae_pct = self._estimate_ae(stress, strain, reh_idx, rel_value, ctx)

            # Sonuclari kaydet
            ctx.properties.yield_strength_mpa = reh_value
            ctx.properties.yield_lower_mpa = rel_value
            ctx.properties.yield_behavior = YieldBehavior.DISCONTINUOUS

            ctx.extra["yield_strain"] = float(strain[reh_idx])
            ctx.extra["yield_reh_strain"] = float(strain[reh_idx])
            ctx.extra["yield_lower_strain"] = float(strain[rel_idx])
            ctx.extra["yield_transient_mask_pct"] = self._transient_mask * 100
            ctx.extra["yield_ae_pct"] = ae_pct

            # Method tag
            tag = "per ISO 6892-1:2019 Annex A.3.2, two-condition test"
            if rel_method == "clause12":
                tag += " + Cl.12 shortcut for ReL"
            ctx.properties.method_tags["yield"] = tag

            ctx.add_anomaly(
                anomaly_type=AnomalyType.DOUBLE_YIELD,
                confidence=0.95,
                description=(
                    f"Sureksiz akma (ISO A.3.2): ReH={reh_value:.1f} MPa, "
                    f"ReL={rel_value:.1f} MPa, Ae={ae_pct:.2f}%"
                ),
                strain_location=float(strain[reh_idx]),
                severity="info",
            )

            return self._success(
                f"Discontinuous yield: ReH={reh_value:.1f} MPa, "
                f"ReL={rel_value:.1f} MPa, Ae={ae_pct:.2f}%"
            )

        # ── Adim 4: Surekli akma -> Rp0.2 (0.2% offset) ──
        return self._find_rp02(ctx, stress, strain)

    def _find_reh(
        self, stress: np.ndarray, strain: np.ndarray
    ) -> tuple[float, int] | None:
        """
        ISO 6892-1:2019 Annex A.3.2 iki-kosullu ReH tespiti.

        Kosul 1: stress[i] < max_stress_so_far * (1 - drop_threshold)
        Kosul 2: Sonraki window_strain kadar strain'de max asilmamali
        """
        max_stress_so_far = 0.0
        max_stress_idx = 0

        for i in range(len(stress)):
            if stress[i] > max_stress_so_far:
                max_stress_so_far = stress[i]
                max_stress_idx = i
                continue

            # Kosul 1: >= %0.5 dusus
            if max_stress_so_far <= 0:
                continue
            drop_ratio = (max_stress_so_far - stress[i]) / max_stress_so_far

            if drop_ratio >= self._drop_threshold:
                # Kosul 2: Strain penceresi dogrulama
                start_strain = strain[i]
                target_strain = start_strain + self._window_strain

                # Pencere icindeki verileri kontrol et
                window_ok = True
                window_complete = False

                for j in range(i, len(stress)):
                    if strain[j] > target_strain:
                        window_complete = True
                        break
                    if stress[j] > max_stress_so_far:
                        window_ok = False
                        break

                if window_complete and window_ok:
                    # Her iki kosul saglandi — ReH kesinlesti
                    return (float(max_stress_so_far), max_stress_idx)

                if not window_ok:
                    # Gurultu — max'i guncelle ve devam et
                    # (stress tekrar yukseldi, yeni max aranacak)
                    continue

        return None  # Sureksiz akma tespit edilemedi

    def _find_rel(
        self,
        stress: np.ndarray,
        strain: np.ndarray,
        reh_idx: int,
    ) -> tuple[float, int, str]:
        """
        ReL tespiti — transient maskeleme + plato minimum.

        ISO 6892-1:2019: "ignoring any initial transient effects"
        Standart sayisal esik vermiyor; vendor rule olarak transient_mask_strain kullanilir.
        """
        post_reh_stress = stress[reh_idx:]
        post_reh_strain = strain[reh_idx:]

        if len(post_reh_stress) < 5:
            return (float(stress[reh_idx]), reh_idx, "fallback")

        # Clause 12 kisayolu
        if self._use_clause12:
            cl12_end_strain = strain[reh_idx] + self._clause12_window
            cl12_mask = (
                (post_reh_strain >= strain[reh_idx]) &
                (post_reh_strain <= cl12_end_strain)
            )
            if np.any(cl12_mask):
                cl12_stress = post_reh_stress[cl12_mask]
                # Transient'i atlayarak minimum bul
                if len(cl12_stress) > 3:
                    # Ilk birkaç noktayı atla (transient)
                    skip = max(1, len(cl12_stress) // 5)
                    rel_local_idx = skip + np.argmin(cl12_stress[skip:])
                else:
                    rel_local_idx = np.argmin(cl12_stress)
                cl12_global_indices = np.where(cl12_mask)[0]
                rel_global_idx = reh_idx + cl12_global_indices[rel_local_idx]
                return (
                    float(stress[rel_global_idx]),
                    int(rel_global_idx),
                    "clause12",
                )

        # Standart yontem: transient maskeleme + plato minimum
        mask_end_strain = strain[reh_idx] + self._transient_mask
        plato_mask = post_reh_strain > mask_end_strain

        if not np.any(plato_mask):
            # Maskeleme cok genis — tum post-ReH'de minimum al
            rel_local_idx = np.argmin(post_reh_stress[1:]) + 1
            rel_value = float(post_reh_stress[rel_local_idx])
            return (rel_value, reh_idx + rel_local_idx, "no_mask_fallback")

        plato_stress = post_reh_stress[plato_mask]
        plato_global_indices = np.where(plato_mask)[0]

        # Plato boyunca minimum = ReL
        rel_local_idx = np.argmin(plato_stress)
        rel_global_idx = reh_idx + plato_global_indices[rel_local_idx]

        return (
            float(stress[rel_global_idx]),
            int(rel_global_idx),
            "transient_masked",
        )

    def _estimate_ae(
        self,
        stress: np.ndarray,
        strain: np.ndarray,
        reh_idx: int,
        rel_value: float,
        ctx: AnalysisContext,
    ) -> float:
        """
        Luders uzamasi (Ae) tahmini — yatay-cizgi yontemi.

        ReL seviyesinden yatay cizgi cizerek, is-sertlesmesi egimi ile
        kesisim noktasini bul. Bu noktanin gerinim degeri = Ae sonu.
        """
        # Basit tahmin: ReL seviyesini tekrar asan ilk noktanin
        # strain'i - ReH strain'i
        post_reh_stress = stress[reh_idx:]
        post_reh_strain = strain[reh_idx:]

        # ReL'den sonra stress'in ReL uzerinde stabil arttigi ilk bolgeyi bul
        re_rise_indices = np.where(post_reh_stress > rel_value * 1.02)[0]

        if len(re_rise_indices) > 5:
            # Ardisik yukselis basladigi ilk bolge
            ae_end_idx = re_rise_indices[0]
            ae_pct = (post_reh_strain[ae_end_idx] - strain[reh_idx]) * 100
        else:
            ae_pct = 0.0

        return float(max(0.0, ae_pct))

    def _find_rp02(
        self,
        ctx: AnalysisContext,
        stress: np.ndarray,
        strain: np.ndarray,
    ) -> StepResult:
        """
        0.2% offset yontemi — ISO 6892-1:2019 Cl. 13.1.

        Parallel-line offset method: Elastik dogruyu 0.002 strain kaydirarak
        ciz, kesisim noktasi = Rp0.2.
        """
        slope = ctx.extra.get("elastic_slope_mpa")
        if slope is None or slope <= 0:
            return self._failure(
                "Elastik modul hesaplanmamis - ElasticModulusDetector once calistirilmali."
            )

        # Offset cizgisi: sigma = slope * (epsilon - offset)
        offset_line = slope * (strain - self._offset)

        # Farki hesapla
        diff = stress - offset_line

        # Sign-change noktasini bul (pozitiften negatife gecis)
        sign_changes = np.where(np.diff(np.sign(diff)) < 0)[0]

        if len(sign_changes) == 0:
            # Fallback: en yakin noktayi al
            valid_range = diff[strain > self._offset * 2]
            if len(valid_range) == 0:
                return self._failure("Yield noktasi bulunamadi.")
            idx = np.argmin(np.abs(valid_range))
            rp02 = float(stress[idx])
        else:
            # Ilk sign-change noktasinda lineer interpolasyon
            idx = sign_changes[0]
            # Sub-point interpolasyon
            d0, d1 = diff[idx], diff[idx + 1]
            frac = d0 / (d0 - d1) if (d0 - d1) != 0 else 0.5
            rp02 = float(stress[idx] + frac * (stress[idx + 1] - stress[idx]))
            yield_strain = float(strain[idx] + frac * (strain[idx + 1] - strain[idx]))
            ctx.extra["yield_strain"] = yield_strain

        ctx.properties.yield_strength_mpa = rp02
        ctx.properties.yield_behavior = YieldBehavior.CONTINUOUS
        ctx.properties.method_tags["yield"] = (
            "per ISO 6892-1:2019 Cl. 13.1, parallel-line offset method"
        )

        return self._success(f"Rp0.2 = {rp02:.1f} MPa (parallel-line offset)")



class UTSDetector(PipelineStep):
    """
    Cekme dayanimi (UTS / Rm) hesaplama — ISO 6892-1:2019 Cl. 3.10.1.

    Yontem: SG-filtrelenmis sinyalin maksimum degeri.
    Ek: Ham vs filtreli dual storage + komsuluk tutarlilik kontrolu.

    Referans: ISO 6892-1:2019 Cl. 3.10.1 (Rm tanimi)
    """

    def __init__(self, neighborhood: int = 20, filter_warn_pct: float = 0.3):
        self._neighborhood = neighborhood
        self._filter_warn_pct = filter_warn_pct

    @property
    def name(self) -> str:
        return "UTSDetector"

    def process(self, ctx: AnalysisContext) -> StepResult:
        if not ctx.has_data:
            return self._failure("Veri yok.")

        stress = ctx.stress
        strain = ctx.strain

        uts_idx = int(np.argmax(stress))
        uts_value = float(stress[uts_idx])
        uts_strain = float(strain[uts_idx])

        # Ham vs filtreli dual storage
        pre_sg_stress = ctx.extra.get("pre_sg_stress")
        if pre_sg_stress is not None and len(pre_sg_stress) > 0:
            raw_uts = float(np.max(pre_sg_stress))
            ctx.extra["uts_raw_mpa"] = raw_uts
            ctx.extra["uts_filtered_mpa"] = uts_value
            diff_pct = abs(raw_uts - uts_value) / max(uts_value, 1e-6) * 100
            ctx.extra["uts_filter_warning"] = diff_pct > self._filter_warn_pct
        else:
            ctx.extra["uts_raw_mpa"] = uts_value
            ctx.extra["uts_filtered_mpa"] = uts_value
            ctx.extra["uts_filter_warning"] = False

        # Komsuluk kontrolu: max degerinin civarindaki ortalama
        start = max(0, uts_idx - self._neighborhood)
        end = min(len(stress), uts_idx + self._neighborhood + 1)
        neighborhood_mean = np.mean(stress[start:end])

        # Max deger komsuluk ortalamasindan %5'ten fazla farkli mi?
        deviation_pct = abs(uts_value - neighborhood_mean) / neighborhood_mean * 100

        ctx.properties.ultimate_tensile_mpa = uts_value
        ctx.extra["uts_idx"] = uts_idx
        ctx.extra["uts_strain"] = uts_strain

        # Method tag
        ctx.properties.method_tags["uts"] = "per ISO 6892-1:2019 Cl. 3.10.1"

        if deviation_pct > 5.0:
            return self._warning(
                f"UTS = {uts_value:.1f} MPa (strain={uts_strain:.4f}). "
                f"Komsuluk sapmasi %{deviation_pct:.1f} - olasi spike/artefakt."
            )

        return self._success(
            f"UTS = {uts_value:.1f} MPa (strain={uts_strain:.4f})"
        )


class ElongationDetector(PipelineStep):
    """
    Kirilma uzamasi (At) hesaplama — ISO 6892-1:2019 Annex A.3.6.1.

    At = total elongation at fracture (elastik dahil, force-drop yontemi).
    A = post-fracture fiziksel olcum gerektirir — bu sinif ile hesaplanamaz.

    Force-drop kriterleri (3/3 AI mutabakat, ISO OR-logic):
    - compound-a (brittle): |dF(n+1,n)| > 5 × |dF(n,n-1)| AND F(n+1) < 0.02 × Fm
    - standalone-b (ductile): F(n+1) < 0.02 × Fm

    Referans: ISO 6892-1:2019 Annex A.3.6.1
    """

    def __init__(
        self,
        fm_threshold: float = 0.02,    # %2 Fm esigi
        accel_factor: float = 5.0,     # 5x ivme kriteri
        min_persistence: int = 1,      # en az 1 ardisik noktada saglanmali
    ):
        self._fm_threshold = fm_threshold
        self._accel_factor = accel_factor
        self._persistence = min_persistence

    @property
    def name(self) -> str:
        return "ElongationDetector"

    def process(self, ctx: AnalysisContext) -> StepResult:
        if not ctx.has_data:
            return self._failure("Veri yok.")

        uts = ctx.properties.ultimate_tensile_mpa
        if uts is None:
            return self._failure("UTS hesaplanmamis.")

        stress = ctx.stress
        strain = ctx.strain
        uts_idx = ctx.extra.get("uts_idx", int(np.argmax(stress)))
        fm = uts  # Fm = max stress
        threshold_2pct = fm * self._fm_threshold

        fracture_idx = None
        criterion_triggered = "end_of_data"

        # UTS sonrasini tara — force-drop kriterleri
        for i in range(uts_idx + 2, len(stress)):
            f_curr = stress[i]
            f_prev = stress[i - 1]
            f_prev2 = stress[i - 2]

            df_curr = abs(f_curr - f_prev)
            df_prev = abs(f_prev - f_prev2)

            # compound-a: 5x ivme AND %2 esik
            is_compound_a = (
                df_prev > 0 and
                df_curr > self._accel_factor * df_prev and
                f_curr < threshold_2pct
            )

            # standalone-b: sadece %2 esik
            is_standalone_b = f_curr < threshold_2pct

            if is_compound_a or is_standalone_b:
                fracture_idx = i
                criterion_triggered = "5x_drop" if is_compound_a else "2pct_threshold"
                break

        if fracture_idx is not None:
            at_pct = float(strain[fracture_idx]) * 100
        else:
            # Veri kopma noktasina kadar gitmemis olabilir
            at_pct = float(strain[-1]) * 100

        ctx.properties.elongation_at_break_pct = at_pct

        # Tahmini A (kalici uzama): At - elastik geri donum
        e_gpa = ctx.properties.elastic_modulus_gpa
        if e_gpa and e_gpa > 0:
            elastic_recovery = (uts / (e_gpa * 1000)) * 100
            a_estimated = at_pct - elastic_recovery
            ctx.extra["elongation_A_estimated_pct"] = max(0.0, a_estimated)
        else:
            ctx.extra["elongation_A_estimated_pct"] = None

        ctx.extra["elongation_criterion"] = criterion_triggered
        ctx.extra["elongation_is_At"] = True

        # Method tag
        ctx.properties.method_tags["elongation"] = (
            "per ISO 6892-1:2019 Annex A.3.6.1, force-drop method"
        )

        return self._success(
            f"At = {at_pct:.1f}% (criterion: {criterion_triggered})"
        )


class NeckingDetector(PipelineStep):
    """
    Necking baslangici (uniform elongation, Ag) tespiti — Considere kriteri.

    Yontem:
    1. Engineering -> True stress-strain donusumu
    2. True stress-strain turevini hesapla (dsigma/depsilon)
    3. dsigma_true/depsilon_true = sigma_true kesisim noktasini bul
    4. Bu nokta = necking baslangici = uniform elongation (Ag)

    Not: Supplementary hesaplama — ISO 6892-1:2019 zorunlu ciktisi degil.
    """

    @property
    def name(self) -> str:
        return "NeckingDetector"

    def process(self, ctx: AnalysisContext) -> StepResult:
        if not ctx.has_data:
            return self._failure("Veri yok.")

        stress = ctx.stress
        strain = ctx.strain

        # True stress-strain hesapla (engineering'den)
        from src.models.enums import StressStrainType

        if ctx.stress_type == StressStrainType.ENGINEERING:
            true_stress = stress * (1 + strain)
            true_strain = np.log(1 + strain)
        else:
            true_stress = stress
            true_strain = strain

        # UTS indeksine kadar olan bolgeyi al (necking oncesi)
        uts_idx = ctx.extra.get("uts_idx", np.argmax(stress))

        # Yield sonrasina odaklan
        yield_strain = ctx.extra.get("yield_strain", strain[0])
        start_idx = int(np.searchsorted(strain, yield_strain))
        if start_idx >= uts_idx - 10:
            start_idx = max(0, uts_idx // 2)

        region_stress = true_stress[start_idx:uts_idx]
        region_strain = true_strain[start_idx:uts_idx]

        if len(region_stress) < 20:
            return self._warning("Necking analizi icin yetersiz veri.")

        # Turev hesapla (SG turev)
        window = min(21, len(region_stress))
        if window % 2 == 0:
            window -= 1
        if window < 5:
            return self._warning("Turev hesabi icin yetersiz veri noktasi.")

        d_strain = np.gradient(region_strain)
        # Sifir bolunmesini onle
        d_strain[d_strain == 0] = 1e-12
        dstress_dstrain = np.gradient(region_stress) / d_strain

        # Considere kriteri: dsigma/depsilon = sigma
        diff = dstress_dstrain - region_stress

        # Sign-change noktasini bul
        sign_changes = np.where(np.diff(np.sign(diff)) < 0)[0]

        if len(sign_changes) == 0:
            # Necking algilanamadi
            ctx.properties.uniform_elongation_pct = float(strain[uts_idx]) * 100
            ctx.properties.method_tags["uniform_elongation"] = (
                "Considere criterion, supplementary (fallback: UTS point)"
            )
            return self._warning(
                f"Considere kriteri saglanmadi. "
                f"UTS noktasi uniform elongation olarak kullanildi: "
                f"{ctx.properties.uniform_elongation_pct:.1f}%"
            )

        necking_local_idx = sign_changes[0]
        necking_global_idx = start_idx + necking_local_idx
        uniform_elong = float(strain[necking_global_idx]) * 100

        ctx.properties.uniform_elongation_pct = uniform_elong
        ctx.extra["necking_idx"] = necking_global_idx

        # Method tag
        ctx.properties.method_tags["uniform_elongation"] = (
            "Considere criterion, supplementary"
        )

        return self._success(
            f"Ag = {uniform_elong:.2f}% "
            f"(Considere kriteri, strain={strain[necking_global_idx]:.4f})"
        )


class StrainHardeningFitter(PipelineStep):
    """
    Strain hardening eksponani (n) hesaplama — Hollomon yontemi.

    Hollomon denklemi: sigma_true = K * epsilon_p^n
    Log-log uzayda: log(sigma_true) = log(K) + n * log(epsilon_p)

    Fit araligi: yield -> necking (Ag) arasi (plastik bolge)
    epsilon_p = epsilon_true - sigma_true / E

    Referans: ISO 10275:2020 (supplementary, yalnizca sac/serit numuneler)
    """

    @property
    def name(self) -> str:
        return "StrainHardeningFitter"

    def process(self, ctx: AnalysisContext) -> StepResult:
        if not ctx.has_data:
            return self._failure("Veri yok.")

        stress = ctx.stress
        strain = ctx.strain
        e_gpa = ctx.properties.elastic_modulus_gpa

        if e_gpa is None or e_gpa <= 0:
            return self._failure("Elastik modul hesaplanmamis.")

        e_mpa = e_gpa * 1000

        # True degerler
        from src.models.enums import StressStrainType

        if ctx.stress_type == StressStrainType.ENGINEERING:
            true_stress = stress * (1 + strain)
            true_strain = np.log(1 + strain)
        else:
            true_stress = stress
            true_strain = strain

        # Fit araligi: yield -> necking (Ag) veya UTS
        yield_strain = ctx.extra.get("yield_strain", strain[0])
        # Ag (necking) ust siniri — Ag disina tasmayi engelle
        necking_idx = ctx.extra.get("necking_idx")
        uts_idx = ctx.extra.get("uts_idx", np.argmax(stress))
        end_idx = necking_idx if necking_idx is not None else uts_idx

        start_idx = int(np.searchsorted(strain, yield_strain))
        # Yield'den biraz sonra basla (transition bolgesini atla)
        start_idx = min(start_idx + 10, end_idx - 20)
        if start_idx < 0:
            start_idx = 0

        ts = true_stress[start_idx:end_idx]
        te = true_strain[start_idx:end_idx]

        # Plastik strain: epsilon_p = epsilon_true - sigma_true / E
        plastic_strain = te - ts / e_mpa

        # Sadece pozitif degerler (log icin)
        valid = (plastic_strain > 1e-6) & (ts > 0)
        n_fit_points = int(np.sum(valid))
        if n_fit_points < 10:
            return self._warning("Hollomon fit icin yetersiz plastik veri noktasi.")

        log_strain = np.log(plastic_strain[valid])
        log_stress = np.log(ts[valid])

        # Lineer fit: log(sigma) = log(K) + n * log(epsilon_p)
        coeffs = np.polyfit(log_strain, log_stress, 1)
        n_value = float(coeffs[0])
        k_value = float(np.exp(coeffs[1]))

        # R2 hesapla
        y_pred = np.polyval(coeffs, log_strain)
        ss_res = np.sum((log_stress - y_pred) ** 2)
        ss_tot = np.sum((log_stress - np.mean(log_stress)) ** 2)
        r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0

        ctx.properties.strain_hardening_n = n_value
        ctx.properties.strength_coefficient_k = k_value
        ctx.extra["hollomon_r2"] = r2
        ctx.extra["hollomon_n_points"] = n_fit_points

        # Method tag
        ctx.properties.method_tags["strain_hardening"] = (
            "per ISO 10275:2020, supplementary (sheet/strip only)"
        )

        return self._success(
            f"Hollomon: n={n_value:.3f}, K={k_value:.1f} MPa "
            f"(R2={r2:.4f}, N={n_fit_points})"
        )


class ToughnessCalculator(PipelineStep):
    """
    Modulus of toughness (Ut) hesaplama — egri alti alan.

    Yontem: Trapezoidal integrasyon (np.trapezoid).
    Birim: Stress (MPa) * Strain (boyutsuz) = MJ/m3

    NOT: Supplementary hesaplama — ISO 6892-1:2019 zorunlu ciktisi DEGİL.
    Charpy impact toughness icin ISO 148 bakiniz.
    """

    @property
    def name(self) -> str:
        return "ToughnessCalculator"

    def process(self, ctx: AnalysisContext) -> StepResult:
        if not ctx.has_data:
            return self._failure("Veri yok.")

        # Sadece pozitif stress bolgesi (cekme)
        positive_mask = ctx.stress > 0
        if np.sum(positive_mask) < 2:
            return self._failure("Pozitif stress bolgesi bulunamadi.")

        # Surekli pozitif bolgeyi bul (ilk pozitiften son pozitife)
        positive_indices = np.where(positive_mask)[0]
        start = positive_indices[0]
        end = positive_indices[-1] + 1

        toughness = float(np.trapz(
            ctx.stress[start:end],
            ctx.strain[start:end],
        ))

        ctx.properties.toughness_mj_m3 = toughness

        # Method tag
        ctx.properties.method_tags["toughness"] = (
            "Supplementary: modulus of toughness (Ut). Not ISO 6892-1. "
            "See ISO 148 for Charpy impact toughness."
        )

        return self._success(f"Ut = {toughness:.2f} MJ/m3")


class StrainRateValidator(PipelineStep):
    """
    Test hizi dogrulama — ISO 6892-1:2019 Table B.1.

    CSV'deki zaman damgasindan strain-rate hesaplar ve ISO hiz araliklarini
    dogrular. Rapor kodu uretir (orn: "A224").

    ISO 6892-1 Hiz Araliklari (strain-rate, s^-1):
      Range 1: 7e-5  (±20%)
      Range 2: 2.5e-4 (±20%) — default
      Range 3: 2e-3  (±20%)
      Range 4: 6.7e-3 (±20%)

    Rapor kodu formati: [A/B][elastik][akma][akma_sonrasi]
      Hane 1: A = strain-rate kontrol, B = stress-rate kontrol
      Hane 2-4: hiz araligi numarasi (1-4)

    Referans: ISO 6892-1:2019 Table B.1, Annex B
    """

    # ISO Table B.1 strain-rate ranges (s^-1)
    ISO_RANGES = {
        1: 7e-5,
        2: 2.5e-4,
        3: 2e-3,
        4: 6.7e-3,
    }
    TOLERANCE = 0.20  # ±20%

    @property
    def name(self) -> str:
        return "StrainRateValidator"

    def process(self, ctx: AnalysisContext) -> StepResult:
        if not ctx.has_data:
            return self._failure("Veri yok.")

        # Zaman damgasi kontrol
        time_data = ctx.extra.get("time_array")
        if time_data is None or len(time_data) < 10:
            ctx.extra["strain_rate_available"] = False
            return self._warning(
                "Zaman damgasi verisi bulunamadi — strain-rate dogrulamasi atlanildi."
            )

        strain = ctx.strain
        time_arr = np.asarray(time_data, dtype=float)

        # Boyut uyumsuzlugu: time_array ham veri uzunlugunda, strain resampled
        # Interpolasyon ile esitle
        if len(time_arr) != len(strain):
            from scipy.interpolate import interp1d
            # Ham strain verisinden resampled strain'e time interpolasyonu
            raw_n = len(time_arr)
            raw_indices = np.linspace(0, 1, raw_n)
            new_indices = np.linspace(0, 1, len(strain))
            try:
                interp_fn = interp1d(raw_indices, time_arr, kind="linear", fill_value="extrapolate")
                time_arr = interp_fn(new_indices)
            except Exception:
                ctx.extra["strain_rate_available"] = False
                return self._warning("Zaman verisi interpolasyonu basarisiz.")

        # Genel strain-rate (ortalama)
        dt = np.diff(time_arr)
        ds = np.diff(strain)
        # Sifir dt'yi filtrele
        valid = dt > 0
        if np.sum(valid) < 5:
            return self._warning("Zaman verisi yetersiz veya sabit.")

        strain_rates = ds[valid] / dt[valid]
        mean_rate = float(np.median(strain_rates))

        # Bolgesel strain-rate (elastik / akma / akma_sonrasi)
        yield_strain = ctx.extra.get("yield_strain", strain[len(strain) // 4])
        uts_idx = ctx.extra.get("uts_idx", len(strain) // 2)

        # Bolge indekslerini bul
        elastic_end = int(np.searchsorted(strain, yield_strain))
        plastic_start = elastic_end
        post_yield_end = uts_idx

        def _region_rate(start, end):
            """Bolgesel strain-rate hesapla."""
            if end <= start + 5 or end >= len(time_arr):
                return mean_rate
            seg_dt = np.diff(time_arr[start:end])
            seg_ds = np.diff(strain[start:end])
            v = seg_dt > 0
            if np.sum(v) < 3:
                return mean_rate
            return float(np.median(seg_ds[v] / seg_dt[v]))

        elastic_rate = _region_rate(0, elastic_end)
        yield_rate = _region_rate(plastic_start, min(plastic_start + 200, post_yield_end))
        post_yield_rate = _region_rate(post_yield_end // 2, post_yield_end)

        # Her bolge icin en yakin ISO araligini bul
        def _classify(rate):
            best_range = 2  # default
            best_diff = float("inf")
            for rng, target in self.ISO_RANGES.items():
                diff = abs(rate - target) / target
                if diff < best_diff:
                    best_diff = diff
                    best_range = rng
            within_tol = best_diff <= self.TOLERANCE
            return best_range, within_tol, best_diff

        e_rng, e_ok, e_dev = _classify(elastic_rate)
        y_rng, y_ok, y_dev = _classify(yield_rate)
        p_rng, p_ok, p_dev = _classify(post_yield_rate)

        # Rapor kodu
        report_code = f"A{e_rng}{y_rng}{p_rng}"

        ctx.extra["strain_rate_available"] = True
        ctx.extra["strain_rate_mean"] = mean_rate
        ctx.extra["strain_rate_elastic"] = elastic_rate
        ctx.extra["strain_rate_yield"] = yield_rate
        ctx.extra["strain_rate_post_yield"] = post_yield_rate
        ctx.extra["strain_rate_report_code"] = report_code
        ctx.extra["strain_rate_all_ok"] = e_ok and y_ok and p_ok

        # Method tag
        ctx.properties.method_tags["test_method"] = (
            f"ISO 6892-1:2019 {report_code}"
        )

        violations = []
        if not e_ok:
            violations.append(f"elastik: Range {e_rng} sapma={e_dev*100:.1f}%")
        if not y_ok:
            violations.append(f"akma: Range {y_rng} sapma={y_dev*100:.1f}%")
        if not p_ok:
            violations.append(f"akma_sonrasi: Range {p_rng} sapma={p_dev*100:.1f}%")

        if violations:
            return self._warning(
                f"Rapor kodu: {report_code}. "
                f"Tolerans asimi: {'; '.join(violations)}"
            )

        return self._success(
            f"Rapor kodu: {report_code} (tum bolgeler ±20% tolerans icinde)"
        )
