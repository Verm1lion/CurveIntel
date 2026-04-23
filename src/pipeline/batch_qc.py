"""
CurveIntel — Katman 6: Batch Quality Control (ISO 5725-2 uyumlu).

Bir batch'teki (parti) numunelerin mekanik ozellik sonuclarini
istatistiksel olarak analiz eden modul.

Ozellikler:
  - Temel istatistikler: mean, std, CoV, min, max
  - Outlier tespiti: Dixon Q (n<=7), Grubbs (n>5)
  - 95% Guven Araligi (CI): t-dagilimi
  - Batch ozet raporu
  - Overlay grafik + box-whisker plot

Referanslar:
  - ISO 5725-2:2019 (olcum metodu kesinligi, Grubbs + Cochran)
  - Dean & Dixon 1951 (Q10 testi)
  - Rorabacher 1991 (Q10 kritik degerler, Monte Carlo dogrulama)
  - ASTM E178 (outlier isleme rehberi)
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy import stats


# ══════════════════════════════════════════════
# Dixon Q10 Kritik Degerler Tablosu
# Kaynak: Rorabacher 1991, Dean & Dixon 1951
# ══════════════════════════════════════════════
_DIXON_Q10_CRITICAL: dict[int, dict[str, float]] = {
    # n: {alpha: Q_crit}
    3: {"0.10": 0.941, "0.05": 0.970, "0.01": 0.994},
    4: {"0.10": 0.765, "0.05": 0.829, "0.01": 0.926},
    5: {"0.10": 0.642, "0.05": 0.710, "0.01": 0.821},
    6: {"0.10": 0.560, "0.05": 0.625, "0.01": 0.740},
    7: {"0.10": 0.507, "0.05": 0.568, "0.01": 0.680},
}


@dataclass
class OutlierResult:
    """Tek bir outlier test sonucu."""

    test_name: str  # "Dixon Q10" veya "Grubbs"
    property_name: str  # "E", "Rp0.2", vb.
    outlier_value: float | None
    outlier_index: int | None  # Orijinal listedeki indeks
    test_statistic: float
    critical_value: float
    is_outlier: bool
    alpha: float
    note: str = ""


@dataclass
class PropertyStats:
    """Tek bir mekanik ozellik icin istatistik ozeti."""

    name: str
    unit: str
    values: list[float] = field(default_factory=list)
    clean_values: list[float] = field(default_factory=list)  # outlier'lar cikarilmis

    mean: float | None = None
    std: float | None = None
    cov_pct: float | None = None
    min_val: float | None = None
    max_val: float | None = None
    n: int = 0

    # Outlier
    outlier_results: list[OutlierResult] = field(default_factory=list)
    outliers_removed: list[float] = field(default_factory=list)

    # Guven araligi
    ci_lower: float | None = None
    ci_upper: float | None = None
    ci_level: float = 0.95

    # CoV kalite
    cov_quality: str = ""  # "iyi", "uyari", "red"


@dataclass
class BatchQCReport:
    """Tam batch QC rapor sonucu."""

    n_specimens: int = 0
    n_passed: int = 0
    n_failed: int = 0
    property_stats: dict[str, PropertyStats] = field(default_factory=dict)
    overall_quality: str = ""  # "PASS", "WARNING", "FAIL"
    notes: list[str] = field(default_factory=list)


# ══════════════════════════════════════════════
# Dixon Q10 Testi
# ══════════════════════════════════════════════
def dixon_q10_test(
    data: list[float],
    alpha: float = 0.05,
) -> OutlierResult:
    """
    Dixon Q10 outlier testi (n=3..7).

    Siralama tabanli, standart sapmaya bagimli degil.
    Kucuk orneklemlerde (n<=7) Grubbs'a gore daha guvenilir.

    Referans: Dean & Dixon 1951, Rorabacher 1991

    Args:
        data: Deger listesi (n=3..7)
        alpha: Anlamlilik duzeyi (0.05 veya 0.01)

    Returns:
        OutlierResult: Test sonucu
    """
    n = len(data)
    if n < 3 or n > 7:
        return OutlierResult(
            test_name="Dixon Q10",
            property_name="",
            outlier_value=None,
            outlier_index=None,
            test_statistic=0.0,
            critical_value=0.0,
            is_outlier=False,
            alpha=alpha,
            note=f"n={n}: Dixon Q10 sadece n=3..7 icin gecerli",
        )

    sorted_data = sorted(data)
    alpha_key = f"{alpha:.2f}"

    q_crit = _DIXON_Q10_CRITICAL[n].get(alpha_key, _DIXON_Q10_CRITICAL[n]["0.05"])

    # Ust uc: Q_upper = (x_n - x_{n-1}) / (x_n - x_1)
    range_total = sorted_data[-1] - sorted_data[0]
    if range_total == 0:
        return OutlierResult(
            test_name="Dixon Q10",
            property_name="",
            outlier_value=None,
            outlier_index=None,
            test_statistic=0.0,
            critical_value=q_crit,
            is_outlier=False,
            alpha=alpha,
            note="Tum degerler esit — outlier yok",
        )

    gap_upper = sorted_data[-1] - sorted_data[-2]
    gap_lower = sorted_data[1] - sorted_data[0]
    q_upper = gap_upper / range_total
    q_lower = gap_lower / range_total

    # Hangi uc daha supheliyse onu test et
    if q_upper >= q_lower:
        q_exp = q_upper
        suspect_val = sorted_data[-1]
        suspect_idx = data.index(suspect_val)
        side = "ust"
    else:
        q_exp = q_lower
        suspect_val = sorted_data[0]
        suspect_idx = data.index(suspect_val)
        side = "alt"

    is_outlier = q_exp > q_crit

    return OutlierResult(
        test_name="Dixon Q10",
        property_name="",
        outlier_value=suspect_val if is_outlier else None,
        outlier_index=suspect_idx if is_outlier else None,
        test_statistic=round(q_exp, 4),
        critical_value=q_crit,
        is_outlier=is_outlier,
        alpha=alpha,
        note=f"{side} uc: Q={q_exp:.4f} {'>' if is_outlier else '<='} Q_crit={q_crit}",
    )


# ══════════════════════════════════════════════
# Grubbs Testi
# ══════════════════════════════════════════════
def grubbs_test(
    data: list[float],
    alpha: float = 0.05,
) -> OutlierResult:
    """
    Grubbs outlier testi (n>=6 icin onerilen).

    G = |x_suspect - mean| / std
    Kritik deger t-dagilimi uzerinden hesaplanir.

    Referans: ISO 5725-2:2019, Grubbs 1969

    Args:
        data: Deger listesi (n>=3)
        alpha: Anlamlilik duzeyi

    Returns:
        OutlierResult: Test sonucu
    """
    n = len(data)
    if n < 3:
        return OutlierResult(
            test_name="Grubbs",
            property_name="",
            outlier_value=None,
            outlier_index=None,
            test_statistic=0.0,
            critical_value=0.0,
            is_outlier=False,
            alpha=alpha,
            note="n < 3: Grubbs testi uygulanamaz",
        )

    arr = np.array(data, dtype=float)
    mean = float(np.mean(arr))
    std = float(np.std(arr, ddof=1))

    if std < 1e-15:
        return OutlierResult(
            test_name="Grubbs",
            property_name="",
            outlier_value=None,
            outlier_index=None,
            test_statistic=0.0,
            critical_value=0.0,
            is_outlier=False,
            alpha=alpha,
            note="Standart sapma ~0 — outlier yok",
        )

    # En buyuk sapmayi bul
    deviations = np.abs(arr - mean)
    suspect_idx = int(np.argmax(deviations))
    suspect_val = data[suspect_idx]
    g_exp = float(deviations[suspect_idx] / std)

    # Kritik deger: t-dagilimi tabanli
    t_crit = stats.t.ppf(1 - alpha / (2 * n), n - 2)
    g_crit = float(((n - 1) / np.sqrt(n)) * np.sqrt(t_crit**2 / (n - 2 + t_crit**2)))

    is_outlier = g_exp > g_crit

    return OutlierResult(
        test_name="Grubbs",
        property_name="",
        outlier_value=suspect_val if is_outlier else None,
        outlier_index=suspect_idx if is_outlier else None,
        test_statistic=round(g_exp, 4),
        critical_value=round(g_crit, 4),
        is_outlier=is_outlier,
        alpha=alpha,
        note=f"G={g_exp:.4f} {'>' if is_outlier else '<='} G_crit={g_crit:.4f}",
    )


# ══════════════════════════════════════════════
# Otomatik Outlier Tespiti (Dixon/Grubbs secimi)
# ══════════════════════════════════════════════
def detect_outlier(
    data: list[float],
    alpha: float = 0.05,
    max_removed: int = 1,
) -> tuple[list[OutlierResult], list[float]]:
    """
    Otomatik outlier tespiti.

    Strateji (deep research mutabakati):
      - n <= 5: Dixon Q10 (birincil)
      - n >= 6: Grubbs (birincil)
      - max_removed = 1 (ASTM E178 onerisi: masking riski)

    Args:
        data: Deger listesi
        alpha: Anlamlilik duzeyi
        max_removed: En fazla cikarilacak outlier sayisi

    Returns:
        (outlier_results, clean_data): sonuclar ve temizlenmis veri
    """
    results: list[OutlierResult] = []
    clean = list(data)
    removed = 0

    while removed < max_removed and len(clean) >= 3:
        n = len(clean)

        # Test secimi
        if n <= 7:
            result = dixon_q10_test(clean, alpha)
        else:
            result = grubbs_test(clean, alpha)

        results.append(result)

        if result.is_outlier and result.outlier_value is not None:
            clean.remove(result.outlier_value)
            removed += 1
        else:
            break

    return results, clean


# ══════════════════════════════════════════════
# Mekanik Ozellik Istatistikleri
# ══════════════════════════════════════════════
def compute_property_stats(
    name: str,
    unit: str,
    values: list[float],
    alpha: float = 0.05,
    ci_level: float = 0.95,
    cov_warn_threshold: float = 10.0,
    cov_fail_threshold: float = 15.0,
) -> PropertyStats:
    """
    Tek bir mekanik ozellik icin tam istatistik raporu.

    Args:
        name: Ozellik adi (orn: "Rm")
        unit: Birim (orn: "MPa")
        values: Ham deger listesi
        alpha: Outlier test anlamlilik duzeyi
        ci_level: Guven araligi duzeyi (0.95)
        cov_warn_threshold: CoV uyari esigi (%)
        cov_fail_threshold: CoV red esigi (%)

    Returns:
        PropertyStats: Tam istatistik ozeti
    """
    ps = PropertyStats(name=name, unit=unit, values=list(values))
    ps.n = len(values)

    if ps.n < 2:
        if ps.n == 1:
            ps.mean = values[0]
            ps.clean_values = list(values)
        ps.cov_quality = "yetersiz_veri"
        return ps

    # Outlier tespiti
    outlier_results, clean = detect_outlier(values, alpha=alpha)
    ps.outlier_results = outlier_results
    ps.clean_values = clean
    ps.outliers_removed = [v for v in values if v not in clean]

    # Temel istatistikler (clean data uzerinden)
    arr = np.array(clean, dtype=float)
    ps.mean = float(np.mean(arr))
    ps.std = float(np.std(arr, ddof=1))
    ps.min_val = float(np.min(arr))
    ps.max_val = float(np.max(arr))

    # CoV
    if ps.mean != 0:
        ps.cov_pct = float((ps.std / abs(ps.mean)) * 100)
    else:
        ps.cov_pct = 0.0

    # CoV kalite degerlendirmesi
    if ps.cov_pct <= cov_warn_threshold:
        ps.cov_quality = "iyi"
    elif ps.cov_pct <= cov_fail_threshold:
        ps.cov_quality = "uyari"
    else:
        ps.cov_quality = "red"

    # 95% Guven Araligi (t-dagilimi)
    n_clean = len(clean)
    if n_clean >= 2:
        ps.ci_level = ci_level
        t_val = stats.t.ppf(1 - (1 - ci_level) / 2, n_clean - 1)
        margin = t_val * ps.std / np.sqrt(n_clean)
        ps.ci_lower = float(ps.mean - margin)
        ps.ci_upper = float(ps.mean + margin)

    return ps


# ══════════════════════════════════════════════
# Batch QC Ana Fonksiyonu
# ══════════════════════════════════════════════
_PROPERTY_MAP = {
    "elastic_modulus_gpa": ("E", "GPa"),
    "yield_strength_mpa": ("Rp0.2 / ReH", "MPa"),
    "ultimate_tensile_mpa": ("Rm", "MPa"),
    "elongation_at_break_pct": ("At", "%"),
    "strain_hardening_n": ("n", "-"),
    "toughness_mj_m3": ("Ut", "MJ/m3"),
}


def run_batch_qc(
    contexts: list,
    alpha: float = 0.05,
) -> BatchQCReport:
    """
    Batch QC analizi calistir.

    Args:
        contexts: Pipeline tamamlanmis AnalysisContext listesi
        alpha: Outlier test anlamlilik duzeyi

    Returns:
        BatchQCReport: Tam QC raporu
    """
    report = BatchQCReport()
    report.n_specimens = len(contexts)

    # Her ozellik icin degerleri topla
    property_values: dict[str, list[float]] = {k: [] for k in _PROPERTY_MAP}
    valid_contexts = []

    for ctx in contexts:
        if not ctx.has_data or ctx.properties is None:
            report.n_failed += 1
            continue

        report.n_passed += 1
        valid_contexts.append(ctx)
        p = ctx.properties

        for attr_name in _PROPERTY_MAP:
            val = getattr(p, attr_name, None)
            if val is not None:
                property_values[attr_name].append(float(val))

    # Her ozellik icin istatistik hesapla
    for attr_name, (display_name, unit) in _PROPERTY_MAP.items():
        vals = property_values[attr_name]
        if len(vals) >= 2:
            ps = compute_property_stats(display_name, unit, vals, alpha=alpha)
            report.property_stats[attr_name] = ps

    # Genel kalite degerlendirmesi
    cov_qualities = [ps.cov_quality for ps in report.property_stats.values()]
    if "red" in cov_qualities:
        report.overall_quality = "FAIL"
        report.notes.append("Bir veya daha fazla ozellikte CoV > %15 — parti reddedildi.")
    elif "uyari" in cov_qualities:
        report.overall_quality = "WARNING"
        report.notes.append("Bir veya daha fazla ozellikte CoV > %10 — inceleme gerekli.")
    elif not cov_qualities:
        report.overall_quality = "INSUFFICIENT_DATA"
        report.notes.append("Yeterli veri yok — istatistik hesaplanamadi.")
    else:
        report.overall_quality = "PASS"
        report.notes.append("Tum ozellikler CoV < %10 — parti kabul edildi.")

    # Outlier notlari
    for ps in report.property_stats.values():
        for r in ps.outlier_results:
            if r.is_outlier:
                report.notes.append(
                    f"OUTLIER: {ps.name} = {r.outlier_value:.2f} {ps.unit} "
                    f"({r.test_name}, {r.note})"
                )

    return report


# ══════════════════════════════════════════════
# Raporlama Yardimcilari
# ══════════════════════════════════════════════
def format_batch_summary(report: BatchQCReport) -> str:
    """Batch QC raporunu okunabilir metin olarak formatla."""
    lines = [
        "=" * 70,
        "  CurveIntel — Batch QC Raporu (ISO 5725-2 uyumlu)",
        "=" * 70,
        f"  Toplam numune: {report.n_specimens}",
        f"  Basarili: {report.n_passed} | Basarisiz: {report.n_failed}",
        f"  Genel sonuc: {report.overall_quality}",
        "-" * 70,
    ]

    if report.property_stats:
        lines.append("")
        lines.append(
            f"  {'Ozellik':<15} {'Ortalama':>12} {'Std':>10} {'CoV%':>8} "
            f"{'Min':>10} {'Max':>10} {'CI±':>10} {'n':>4} {'Durum':>8}"
        )
        lines.append("  " + "-" * 98)

        for ps in report.property_stats.values():
            if ps.mean is None:
                continue

            ci_margin = ""
            if ps.ci_lower is not None and ps.ci_upper is not None:
                ci_margin = f"±{(ps.ci_upper - ps.ci_lower) / 2:.2f}"

            cov_str = f"{ps.cov_pct:.1f}" if ps.cov_pct is not None else "---"
            quality_icon = {"iyi": "OK", "uyari": "!!", "red": "XX"}.get(ps.cov_quality, "?")

            lines.append(
                f"  {ps.name + ' (' + ps.unit + ')':<15} "
                f"{ps.mean:>12.2f} {ps.std:>10.3f} {cov_str:>8} "
                f"{ps.min_val:>10.2f} {ps.max_val:>10.2f} {ci_margin:>10} "
                f"{len(ps.clean_values):>4} {quality_icon:>8}"
            )

            # Cikarilan outlier'lari goster
            if ps.outliers_removed:
                for ov in ps.outliers_removed:
                    lines.append(f"    └─ OUTLIER cikarildi: {ov:.2f} {ps.unit}")

    if report.notes:
        lines.append("")
        lines.append("  [NOTLAR]")
        for note in report.notes:
            lines.append(f"    • {note}")

    lines.append("")
    lines.append("=" * 70)
    return "\n".join(lines)


def generate_batch_plots(
    contexts: list,
    report: BatchQCReport,
    output_dir,
) -> list:
    """
    Batch gorsellestirme: overlay + box-whisker.

    Returns:
        Olusturulan dosya yollarinin listesi
    """
    output_files = []

    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from pathlib import Path

        output_dir = Path(output_dir)
    except ImportError:
        return output_files

    # ─── 1. Overlay: Tum egriler ust uste ───
    fig, ax = plt.subplots(figsize=(14, 8))
    colors_cycle = plt.cm.tab10.colors

    valid_ctxs = [c for c in contexts if c.has_data]
    all_stresses = []

    for i, ctx in enumerate(valid_ctxs):
        color = colors_cycle[i % len(colors_cycle)]
        label = ctx.metadata.source_file or f"Numune {i + 1}"
        label = label[:30]

        # Outlier kontrolu — cikarilmis mi?
        is_outlier = False
        for ps in report.property_stats.values():
            if ps.outliers_removed and i < len(ps.values):
                if ps.values[i] in ps.outliers_removed:
                    is_outlier = True
                    break

        if is_outlier:
            ax.plot(
                ctx.strain,
                ctx.stress,
                "--",
                color=color,
                alpha=0.4,
                lw=0.8,
                label=f"{label} (OUTLIER)",
            )
        else:
            ax.plot(ctx.strain, ctx.stress, "-", color=color, alpha=0.8, lw=1.0, label=label)
            all_stresses.append(ctx.stress)

    # Ortalama egri (non-outlier)
    if len(all_stresses) >= 2:
        min_len = min(len(s) for s in all_stresses)
        stacked = np.column_stack([s[:min_len] for s in all_stresses])
        mean_stress = np.mean(stacked, axis=1)
        mean_strain = valid_ctxs[0].strain[:min_len]  # ilk gecerli numunenin strain'i
        ax.plot(mean_strain, mean_stress, "k-", lw=2.5, label="Ortalama", zorder=10)

    ax.set_xlabel("Strain (mm/mm)", fontsize=12)
    ax.set_ylabel("Stress (MPa)", fontsize=12)
    ax.set_title("CurveIntel — Batch Overlay (Tum Numuneler)", fontsize=14)
    ax.legend(fontsize=8, loc="lower right", ncol=2)
    ax.grid(True, alpha=0.3)

    overlay_path = output_dir / "batch_overlay.png"
    fig.savefig(overlay_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    output_files.append(overlay_path)

    # ─── 2. Box-Whisker Plot ───
    prop_names = []
    prop_values = []
    for ps in report.property_stats.values():
        if ps.n >= 2:
            prop_names.append(f"{ps.name}\n({ps.unit})")
            prop_values.append(ps.values)

    if prop_values:
        n_props = len(prop_names)
        fig, axes = plt.subplots(1, n_props, figsize=(3.5 * n_props, 6))
        if n_props == 1:
            axes = [axes]

        for ax_i, (name, vals) in enumerate(zip(prop_names, prop_values)):
            axes[ax_i].boxplot(
                vals,
                widths=0.5,
                patch_artist=True,
                boxprops=dict(facecolor="#42a5f5", alpha=0.7),
                medianprops=dict(color="#c62828", lw=2),
            )
            axes[ax_i].set_title(name, fontsize=11, fontweight="bold")
            axes[ax_i].set_xticks([])
            axes[ax_i].grid(True, axis="y", alpha=0.3)

            # Bireysel noktalar
            jitter = np.random.normal(1, 0.04, len(vals))
            axes[ax_i].scatter(jitter, vals, c="#1a237e", alpha=0.5, s=30, zorder=5)

        fig.suptitle(
            "CurveIntel — Batch Box-Whisker (Mekanik Ozellikler)", fontsize=13, fontweight="bold"
        )
        fig.tight_layout()

        box_path = output_dir / "batch_boxwhisker.png"
        fig.savefig(box_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        output_files.append(box_path)

    return output_files


# ══════════════════════════════════════════════
# SPC — Statistical Process Control
# X-bar / R Chart + Nelson Rules
# ══════════════════════════════════════════════

# X-bar / R chart sabitleri (subgroup size n -> A2, D3, D4)
# Kaynak: ASTM E2587, Montgomery "Introduction to SPC" Table VI
_SPC_CONSTANTS: dict[int, dict[str, float]] = {
    2: {"A2": 1.880, "D3": 0.000, "D4": 3.267},
    3: {"A2": 1.023, "D3": 0.000, "D4": 2.575},
    4: {"A2": 0.729, "D3": 0.000, "D4": 2.282},
    5: {"A2": 0.577, "D3": 0.000, "D4": 2.115},
    6: {"A2": 0.483, "D3": 0.000, "D4": 2.004},
    7: {"A2": 0.419, "D3": 0.076, "D4": 1.924},
    8: {"A2": 0.373, "D3": 0.136, "D4": 1.864},
    9: {"A2": 0.337, "D3": 0.184, "D4": 1.816},
    10: {"A2": 0.308, "D3": 0.223, "D4": 1.777},
}


@dataclass
class NelsonViolation:
    """Tek bir Nelson kural ihlali."""

    rule: int  # 1-8
    description: str
    indices: list[int]  # Ihlal eden noktalarin indeksleri


@dataclass
class SPCResult:
    """SPC analiz sonucu."""

    property_name: str
    grand_mean: float
    r_bar: float
    ucl_xbar: float
    lcl_xbar: float
    ucl_r: float
    lcl_r: float
    subgroup_means: list[float]
    subgroup_ranges: list[float]
    nelson_violations: list[NelsonViolation]
    is_in_control: bool


def _check_nelson_rules(
    values: list[float],
    center: float,
    sigma: float,
) -> list[NelsonViolation]:
    """
    Nelson 8 kurali kontrolu.

    Kurallar:
      1: Tek nokta 3-sigma disinda
      2: 9 ardisik nokta ortalama ayni tarafinda
      3: 6 ardisik nokta surekli artan/azalan
      4: 14 ardisik nokta alternating (yukari-asagi)
      5: 2/3 ardisik nokta 2-sigma disinda (ayni tarafta)
      6: 4/5 ardisik nokta 1-sigma disinda (ayni tarafta)
      7: 15 ardisik nokta 1-sigma icinde (stratification)
      8: 8 ardisik nokta 1-sigma disinda (mixture)
    """
    violations: list[NelsonViolation] = []
    n = len(values)
    if n < 2 or sigma < 1e-15:
        return violations

    # Bolgeler
    z = [(v - center) / sigma for v in values]

    # Rule 1: Tek nokta |z| > 3
    for i, zi in enumerate(z):
        if abs(zi) > 3:
            violations.append(
                NelsonViolation(
                    rule=1,
                    description=f"Nokta {i}: 3-sigma disinda (z={zi:.2f})",
                    indices=[i],
                )
            )

    # Rule 2: 9 ardisik nokta ayni tarafta
    if n >= 9:
        for i in range(n - 8):
            window = z[i : i + 9]
            if all(v > 0 for v in window) or all(v < 0 for v in window):
                violations.append(
                    NelsonViolation(
                        rule=2,
                        description=f"Noktalar {i}-{i + 8}: 9 ardisik ayni tarafta",
                        indices=list(range(i, i + 9)),
                    )
                )
                break  # Tek sefer raporla

    # Rule 3: 6 ardisik artan veya azalan
    if n >= 6:
        for i in range(n - 5):
            window = values[i : i + 6]
            diffs = [window[j + 1] - window[j] for j in range(5)]
            if all(d > 0 for d in diffs) or all(d < 0 for d in diffs):
                trend = "artan" if diffs[0] > 0 else "azalan"
                violations.append(
                    NelsonViolation(
                        rule=3,
                        description=f"Noktalar {i}-{i + 5}: 6 ardisik {trend}",
                        indices=list(range(i, i + 6)),
                    )
                )
                break

    # Rule 4: 14 ardisik alternating
    if n >= 14:
        for i in range(n - 13):
            window = values[i : i + 14]
            diffs = [window[j + 1] - window[j] for j in range(13)]
            signs = [1 if d > 0 else -1 for d in diffs]
            alternating = all(signs[j] != signs[j + 1] for j in range(12))
            if alternating:
                violations.append(
                    NelsonViolation(
                        rule=4,
                        description=f"Noktalar {i}-{i + 13}: 14 ardisik alternating",
                        indices=list(range(i, i + 14)),
                    )
                )
                break

    # Rule 5: 2/3 ardisik nokta 2-sigma disinda (ayni tarafta)
    if n >= 3:
        for i in range(n - 2):
            window = z[i : i + 3]
            above = sum(1 for v in window if v > 2)
            below = sum(1 for v in window if v < -2)
            if above >= 2 or below >= 2:
                violations.append(
                    NelsonViolation(
                        rule=5,
                        description=f"Noktalar {i}-{i + 2}: 2/3 nokta 2-sigma disinda",
                        indices=list(range(i, i + 3)),
                    )
                )
                break

    # Rule 6: 4/5 ardisik nokta 1-sigma disinda (ayni tarafta)
    if n >= 5:
        for i in range(n - 4):
            window = z[i : i + 5]
            above = sum(1 for v in window if v > 1)
            below = sum(1 for v in window if v < -1)
            if above >= 4 or below >= 4:
                violations.append(
                    NelsonViolation(
                        rule=6,
                        description=f"Noktalar {i}-{i + 4}: 4/5 nokta 1-sigma disinda",
                        indices=list(range(i, i + 5)),
                    )
                )
                break

    # Rule 7: 15 ardisik nokta 1-sigma icinde (stratification)
    if n >= 15:
        for i in range(n - 14):
            window = z[i : i + 15]
            if all(abs(v) < 1 for v in window):
                violations.append(
                    NelsonViolation(
                        rule=7,
                        description=f"Noktalar {i}-{i + 14}: 15 ardisik 1-sigma icinde",
                        indices=list(range(i, i + 15)),
                    )
                )
                break

    # Rule 8: 8 ardisik nokta 1-sigma disinda (mixture)
    if n >= 8:
        for i in range(n - 7):
            window = z[i : i + 8]
            if all(abs(v) > 1 for v in window):
                violations.append(
                    NelsonViolation(
                        rule=8,
                        description=f"Noktalar {i}-{i + 7}: 8 ardisik 1-sigma disinda",
                        indices=list(range(i, i + 8)),
                    )
                )
                break

    return violations


def run_spc_analysis(
    batch_means: list[float],
    property_name: str = "Rm",
    subgroup_size: int = 3,
) -> SPCResult:
    """
    SPC (X-bar / R chart) analizi.

    Batch ortalamalarindan kontrol limitleri ve Nelson kurallarini hesaplar.

    Args:
        batch_means: Batch bazinda ortalama degerler (zaman sirasinda)
        property_name: Ozellik adi
        subgroup_size: Alt-grup buyuklugu (default 3)

    Returns:
        SPCResult: SPC analiz sonucu
    """
    n = len(batch_means)

    if n < 2:
        return SPCResult(
            property_name=property_name,
            grand_mean=batch_means[0] if batch_means else 0,
            r_bar=0,
            ucl_xbar=0,
            lcl_xbar=0,
            ucl_r=0,
            lcl_r=0,
            subgroup_means=batch_means,
            subgroup_ranges=[],
            nelson_violations=[],
            is_in_control=True,
        )

    # SPC sabitleri
    sg = min(subgroup_size, 10)
    sg = max(sg, 2)
    consts = _SPC_CONSTANTS[sg]

    # Grand mean ve R-bar (individual chart icin moving range)
    grand_mean = float(np.mean(batch_means))

    # Moving range (ardisik farklar)
    moving_ranges = [abs(batch_means[i] - batch_means[i - 1]) for i in range(1, n)]
    r_bar = float(np.mean(moving_ranges)) if moving_ranges else 0

    # Kontrol limitleri (X-bar chart, individuals)
    # Individuals chart icin d2=1.128 (n=2 moving range)
    d2 = 1.128
    sigma_est = r_bar / d2 if d2 > 0 else 0

    ucl_xbar = grand_mean + 3 * sigma_est
    lcl_xbar = grand_mean - 3 * sigma_est

    # R chart limitleri
    ucl_r = consts["D4"] * r_bar
    lcl_r = consts["D3"] * r_bar

    # Nelson kurallari
    nelson = _check_nelson_rules(batch_means, grand_mean, sigma_est)

    # Kontrol durumu
    all_in_limits = all(lcl_xbar <= v <= ucl_xbar for v in batch_means)
    is_in_control = all_in_limits and len(nelson) == 0

    return SPCResult(
        property_name=property_name,
        grand_mean=round(grand_mean, 4),
        r_bar=round(r_bar, 4),
        ucl_xbar=round(ucl_xbar, 4),
        lcl_xbar=round(lcl_xbar, 4),
        ucl_r=round(ucl_r, 4),
        lcl_r=round(lcl_r, 4),
        subgroup_means=batch_means,
        subgroup_ranges=moving_ranges,
        nelson_violations=nelson,
        is_in_control=is_in_control,
    )


def generate_spc_chart(
    spc_result: SPCResult,
    output_dir,
) -> list:
    """
    SPC kontrol grafigi uret.

    Returns:
        Olusturulan dosya yollarinin listesi
    """
    output_files = []

    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from pathlib import Path

        output_dir = Path(output_dir)
    except ImportError:
        return output_files

    r = spc_result
    n = len(r.subgroup_means)
    x = list(range(1, n + 1))

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), height_ratios=[3, 2])

    # ─── X-bar Chart ───
    ax1.plot(x, r.subgroup_means, "bo-", lw=1.2, ms=6, label="Deger")

    # Kontrol limitleri
    ax1.axhline(r.grand_mean, color="#1b5e20", lw=2, ls="-", label=f"CL={r.grand_mean:.1f}")
    ax1.axhline(r.ucl_xbar, color="#c62828", lw=1.5, ls="--", label=f"UCL={r.ucl_xbar:.1f}")
    ax1.axhline(r.lcl_xbar, color="#c62828", lw=1.5, ls="--", label=f"LCL={r.lcl_xbar:.1f}")

    # Sigma bolgeleri (renkli band)
    sigma = (r.ucl_xbar - r.grand_mean) / 3
    for i, (alpha_val, color) in enumerate(
        [
            (0.08, "#a5d6a7"),  # 1-sigma (yesil)
            (0.06, "#fff9c4"),  # 2-sigma (sari)
            (0.04, "#ffcdd2"),  # 3-sigma (kirmizi)
        ]
    ):
        ax1.axhspan(
            r.grand_mean + i * sigma, r.grand_mean + (i + 1) * sigma, alpha=alpha_val, color=color
        )
        ax1.axhspan(
            r.grand_mean - (i + 1) * sigma, r.grand_mean - i * sigma, alpha=alpha_val, color=color
        )

    # Nelson ihlalleri
    for nv in r.nelson_violations:
        for idx in nv.indices:
            if idx < n:
                ax1.plot(idx + 1, r.subgroup_means[idx], "r*", ms=14, zorder=10)

    ax1.set_ylabel(f"{r.property_name}", fontsize=12)
    ax1.set_title(
        f"X-bar Chart: {r.property_name} "
        f"({'KONTROL ICINDE' if r.is_in_control else 'KONTROL DISI!'})",
        fontsize=13,
        fontweight="bold",
        color="#1b5e20" if r.is_in_control else "#c62828",
    )
    ax1.legend(fontsize=9, loc="upper right")
    ax1.grid(True, alpha=0.3)

    # ─── R Chart (Moving Range) ───
    if r.subgroup_ranges:
        x_r = list(range(2, n + 1))
        ax2.plot(x_r, r.subgroup_ranges, "rs-", lw=1.0, ms=5, label="MR")
        ax2.axhline(r.r_bar, color="#1b5e20", lw=2, ls="-", label=f"R-bar={r.r_bar:.2f}")
        ax2.axhline(r.ucl_r, color="#c62828", lw=1.5, ls="--", label=f"UCL={r.ucl_r:.2f}")
        if r.lcl_r > 0:
            ax2.axhline(r.lcl_r, color="#c62828", lw=1.5, ls="--", label=f"LCL={r.lcl_r:.2f}")
        ax2.set_ylabel("Moving Range", fontsize=12)
        ax2.set_xlabel("Batch #", fontsize=12)
        ax2.legend(fontsize=9, loc="upper right")
        ax2.grid(True, alpha=0.3)

    ax2.set_title("R Chart (Moving Range)", fontsize=12)

    fig.tight_layout()
    chart_path = output_dir / f"spc_{r.property_name.replace('/', '_')}.png"
    fig.savefig(chart_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    output_files.append(chart_path)

    return output_files
