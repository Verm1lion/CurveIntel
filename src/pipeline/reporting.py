"""
CurveIntel — Katman 5: Reporting & Export.

PDF rapor uretimi ve batch analiz modulleri.
Hesaplamalar ISO 6892-1:2019 metodolojisine gore yapilir.
Rapor sablonu, ISO/IEC 17025:2017 Madde 7.8.2 alanlarini icermek uzere tasarlanmistir.

PDF Rapor Icerigi:
  1. Baslik sayfasi (test bilgileri, tarih, yasal not)
  2. Mekanik ozellikler tablosu (ISO method_tags ile)
  3. Stress-strain egrisi grafigi
  4. Anomali ozeti
  5. Pipeline adim loglari
  6. Kalite skoru + sonuc

Batch Analiz:
  - Bir dizindeki tum CSV dosyalarini tarar
  - Her biri icin pipeline calistirir
  - Ozet tablo + bireysel raporlar uretir
"""
from __future__ import annotations

import json
import csv as csv_module
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any

import numpy as np

from src.pipeline.base import AnalysisContext, Pipeline

# ReportLab imports
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


# ── Renk paleti ──
COLOR_PRIMARY = colors.HexColor("#1a237e")      # Koyu lacivert
COLOR_SECONDARY = colors.HexColor("#283593")     # Lacivert
COLOR_ACCENT = colors.HexColor("#42a5f5")        # Acik mavi
COLOR_SUCCESS = colors.HexColor("#2e7d32")       # Yesil
COLOR_WARNING = colors.HexColor("#f57f17")       # Turuncu
COLOR_DANGER = colors.HexColor("#c62828")        # Kirmizi
COLOR_LIGHT_BG = colors.HexColor("#e8eaf6")      # Acik gri-mavi
COLOR_TABLE_HEADER = colors.HexColor("#1565c0")  # Tablo baslik
COLOR_TABLE_ALT = colors.HexColor("#e3f2fd")     # Tablo alternatif satir


# ── Turkce karakter donusumu (Helvetica desteklemiyor) ──
_TR_MAP = str.maketrans({
    '\u011f': 'g', '\u011e': 'G',  # ğ Ğ
    '\u00fc': 'u', '\u00dc': 'U',  # ü Ü
    '\u015f': 's', '\u015e': 'S',  # ş Ş
    '\u0131': 'i', '\u0130': 'I',  # ı İ
    '\u00f6': 'o', '\u00d6': 'O',  # ö Ö
    '\u00e7': 'c', '\u00c7': 'C',  # ç Ç
    '\u2014': '--', '\u2013': '-',  # em/en dash
    '\u2019': "'", '\u201c': '"', '\u201d': '"',
})

def _s(text: str) -> str:
    """Sanitize text for Helvetica: replace Turkish chars with ASCII."""
    if not isinstance(text, str):
        return str(text)
    return text.translate(_TR_MAP)


def _build_styles() -> dict[str, ParagraphStyle]:
    """Ozel PDF stilleri olustur."""
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "CITitle", parent=base["Title"],
            fontSize=22, textColor=COLOR_PRIMARY, spaceAfter=6 * mm,
            fontName="Helvetica-Bold",
        ),
        "subtitle": ParagraphStyle(
            "CISubtitle", parent=base["Normal"],
            fontSize=11, textColor=COLOR_SECONDARY, spaceAfter=3 * mm,
            fontName="Helvetica",
        ),
        "heading": ParagraphStyle(
            "CIHeading", parent=base["Heading2"],
            fontSize=14, textColor=COLOR_PRIMARY, spaceBefore=8 * mm,
            spaceAfter=4 * mm, fontName="Helvetica-Bold",
            borderWidth=1, borderColor=COLOR_ACCENT, borderPadding=3,
        ),
        "body": ParagraphStyle(
            "CIBody", parent=base["Normal"],
            fontSize=10, leading=14, fontName="Helvetica",
        ),
        "small": ParagraphStyle(
            "CISmall", parent=base["Normal"],
            fontSize=8, leading=10, textColor=colors.gray,
            fontName="Helvetica",
        ),
        "value": ParagraphStyle(
            "CIValue", parent=base["Normal"],
            fontSize=11, fontName="Helvetica-Bold", alignment=TA_RIGHT,
        ),
        "label": ParagraphStyle(
            "CILabel", parent=base["Normal"],
            fontSize=10, fontName="Helvetica", textColor=COLOR_SECONDARY,
        ),
        "pass": ParagraphStyle(
            "CIPass", parent=base["Normal"],
            fontSize=12, fontName="Helvetica-Bold", textColor=COLOR_SUCCESS,
            alignment=TA_CENTER,
        ),
        "fail": ParagraphStyle(
            "CIFail", parent=base["Normal"],
            fontSize=12, fontName="Helvetica-Bold", textColor=COLOR_DANGER,
            alignment=TA_CENTER,
        ),
    }


def _quality_score(ctx: AnalysisContext) -> tuple[float, str]:
    """
    Toplam kalite skoru hesapla (0-100).

    Puanlama:
    - Pipeline basari orani: 40 puan
    - SNR kalitesi: 20 puan
    - Anomali sayisi: 20 puan
    - Ozellik tutarliligi: 20 puan
    """
    score = 0.0

    # Pipeline basari
    total = len(ctx.step_results)
    success = sum(1 for r in ctx.step_results if r.status.value == "success")
    if total > 0:
        score += (success / total) * 40

    # SNR
    snr = ctx.extra.get("snr_db", 0)
    if snr >= 40:
        score += 20
    elif snr >= 20:
        score += 10
    else:
        score += 0

    # Anomali
    warn_count = sum(1 for a in ctx.anomalies if a.severity == "warning")
    crit_count = sum(1 for a in ctx.anomalies if a.severity == "critical")
    anomaly_penalty = min(20, warn_count * 3 + crit_count * 10)
    score += 20 - anomaly_penalty

    # Ozellik tutarliligi
    p = ctx.properties
    consistency = 20
    if p.yield_strength_mpa and p.ultimate_tensile_mpa:
        if p.yield_strength_mpa > p.ultimate_tensile_mpa:
            consistency -= 10
    if p.elastic_modulus_gpa and not (1 <= p.elastic_modulus_gpa <= 600):
        consistency -= 10
    score += max(0, consistency)

    score = min(100, max(0, score))

    if score >= 85:
        grade = "A+ (Mukemmel)"
    elif score >= 70:
        grade = "A (Iyi)"
    elif score >= 55:
        grade = "B (Dikkatle Kullanilabilir)"
    elif score >= 40:
        grade = "C (Dusuk Guvenilirlik)"
    else:
        grade = "D (Guvenilmez)"

    return score, grade


def generate_plot_image(ctx: AnalysisContext, title: str = "") -> BytesIO | None:
    """Stress-strain egrisi grafigini BytesIO olarak uret."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(ctx.strain, ctx.stress, "#1565c0", lw=1.2, label="Stress-Strain")

        p = ctx.properties

        # Yield noktasi
        ys = ctx.extra.get("yield_strain")
        if ys and p.yield_strength_mpa:
            ax.plot(ys, p.yield_strength_mpa, "go", ms=9,
                    label=f"Yield = {p.yield_strength_mpa:.1f} MPa", zorder=5)

        # UTS noktasi
        uts_idx = ctx.extra.get("uts_idx")
        if uts_idx is not None and p.ultimate_tensile_mpa:
            ax.plot(ctx.strain[uts_idx], p.ultimate_tensile_mpa, "r^", ms=9,
                    label=f"UTS = {p.ultimate_tensile_mpa:.1f} MPa", zorder=5)

        # Necking
        neck_idx = ctx.extra.get("necking_idx")
        if neck_idx:
            ax.axvline(ctx.strain[neck_idx], color="orange", ls="--", alpha=0.7,
                       label="Necking baslangici")

        ax.set_xlabel("Strain (mm/mm)", fontsize=11)
        ax.set_ylabel("Stress (MPa)", fontsize=11)
        ax.set_title(title or "Stress-Strain Egrisi", fontsize=13)
        ax.legend(fontsize=9, loc="lower right")
        ax.grid(True, alpha=0.3)

        buf = BytesIO()
        fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
        plt.close(fig)
        buf.seek(0)
        return buf
    except Exception:
        return None


def generate_pdf_report(
    ctx: AnalysisContext,
    output_path: str | Path,
    company_name: str = "CurveIntel Analysis Engine",
    operator: str = "",
    test_standard: str = "ISO 6892-1:2019",
    lab_name: str = "",
    lab_address: str = "",
    customer_name: str = "",
) -> Path:
    """
    PDF rapor uret.

    Hesaplamalar ISO 6892-1:2019 metodolojisine gore yapilir.
    Rapor sablonu ISO/IEC 17025:2017 Cl. 7.8.2 alanlarini icerir.

    Args:
        ctx: Tamamlanmis pipeline context
        output_path: PDF cikti yolu
        company_name: Firma adi
        operator: Operator adi
        test_standard: Uygulanan standart
        lab_name: Laboratuvar adi (17025 Cl. 7.8.2.1)
        lab_address: Laboratuvar adresi (17025 Cl. 7.8.2.1)
        customer_name: Musteri adi (17025 Cl. 7.8.2.1)

    Returns:
        Olusturulan PDF dosyasinin yolu
    """
    output_path = Path(output_path)
    styles = _build_styles()

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    elements: list[Any] = []

    # ─────────────────────────────────────────────
    # 1. BASLIK SAYFASI
    # ─────────────────────────────────────────────
    elements.append(Spacer(1, 3 * cm))
    elements.append(Paragraph(company_name, styles["title"]))
    elements.append(Paragraph("Mekanik Test Analiz Raporu", styles["subtitle"]))
    elements.append(Spacer(1, 1 * cm))

    # Test bilgileri tablosu
    import uuid as _uuid
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    report_uuid = str(_uuid.uuid4())[:12].upper()
    specimen_id = ctx.metadata.specimen_id or ctx.metadata.source_file or "---"
    _MATERIAL_LABELS = {
        "structural_steel": "Yapisal Celik (Structural Steel)",
        "dual_phase_steel": "Cift-Fazli Celik (DP Steel)",
        "low_carbon_steel": "Dusuk Karbonlu Celik",
        "stainless_steel": "Paslanmaz Celik (Stainless)",
        "aluminum": "Aluminyum",
        "polymer": "Polimer",
        "composite": "Kompozit",
        "unknown": "---",
    }
    material_raw = ctx.metadata.material_type.value if ctx.metadata.material_type else "unknown"
    material = _MATERIAL_LABELS.get(material_raw, material_raw)

    info_data = [
        ["Rapor ID", f"CI-{report_uuid}"],
        ["Rapor Tarihi", now],
        ["Laboratuvar", lab_name or "---"],
        ["Laboratuvar Adresi", lab_address or "---"],
        ["Musteri", customer_name or "---"],
        ["Numune ID", specimen_id],
        ["Malzeme", material],
        ["Kaynak Dosya", ctx.metadata.source_file or "---"],
        ["Test Standardi", test_standard],
        ["Operator", operator or "---"],
        ["Veri Turu", ctx.stress_type.value],
        ["Veri Noktasi", str(ctx.n_points)],
    ]

    info_table = Table(info_data, colWidths=[5.5 * cm, 10 * cm])
    info_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("TEXTCOLOR", (0, 0), (0, -1), COLOR_SECONDARY),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("LINEBELOW", (0, 0), (-1, -2), 0.5, colors.lightgrey),
        ("LINEBELOW", (0, -1), (-1, -1), 1, COLOR_ACCENT),
    ]))
    elements.append(info_table)

    # Kalite skoru
    score, grade = _quality_score(ctx)
    elements.append(Spacer(1, 1 * cm))

    score_color = COLOR_SUCCESS if score >= 60 else (COLOR_WARNING if score >= 40 else COLOR_DANGER)
    score_style = ParagraphStyle(
        "ScoreStyle", fontSize=16, fontName="Helvetica-Bold",
        textColor=score_color, alignment=TA_CENTER,
    )
    elements.append(Paragraph(f"Kalite Skoru: {score:.0f}/100 — {grade}", score_style))

    # ── ISO 17025 Yasal Not / Disclaimer (TR + EN) ──
    elements.append(Spacer(1, 1 * cm))
    disclaimer_style = ParagraphStyle(
        "Disclaimer", fontSize=7.5, leading=10,
        fontName="Helvetica", textColor=colors.HexColor("#616161"),
        spaceBefore=2 * mm, spaceAfter=2 * mm,
        borderWidth=0.5, borderColor=colors.HexColor("#bdbdbd"),
        borderPadding=6,
    )
    disclaimer_tr = (
        "<b>YASAL NOT:</b> Bu rapordaki hesaplamalar ISO 6892-1:2019 metodolojisine gore yapilmistir. "
        "Rapor sablonu, ISO/IEC 17025:2017 Madde 7.8.2'de listelenen alanlari icerecek sekilde "
        "tasarlanmistir. Bu yazilim veya bu rapor herhangi bir akreditasyon kurulusu "
        "(TURKAK, EA, ILAC vb.) tarafindan akredite edilmemis veya sertifikalandirilmamistir. "
        "Akredite test raporu ancak ISO/IEC 17025 kapsaminda akredite edilmis bir laboratuvar "
        "tarafindan, kendi kapsami dahilinde duzenlenebilir."
    )
    disclaimer_en = (
        "<b>LEGAL NOTICE:</b> Calculations in this report are performed according to ISO 6892-1:2019. "
        "Report template is designed to include data fields listed in ISO/IEC 17025:2017 "
        "Clause 7.8.2. This software and this report are NOT accredited or certified by "
        "any accreditation body. An accredited test report can only be issued by a "
        "laboratory accredited to ISO/IEC 17025 within its accredited scope."
    )
    elements.append(Paragraph(disclaimer_tr, disclaimer_style))
    elements.append(Paragraph(disclaimer_en, disclaimer_style))

    # Cl. 7.8.2.1: "Sonuclar yalnizca deney edilen numuneye aittir" beyani
    specimen_stmt = ParagraphStyle(
        "SpecimenStmt", fontSize=8, fontName="Helvetica-BoldOblique",
        textColor=COLOR_SECONDARY, alignment=TA_CENTER,
        spaceBefore=4 * mm, spaceAfter=2 * mm,
    )
    elements.append(Paragraph(
        "Bu rapordaki sonuclar yalnizca deney edilen numuneye aittir. / "
        "The results in this report relate only to the items tested.",
        specimen_stmt,
    ))

    elements.append(PageBreak())

    # ─────────────────────────────────────────────
    # 2. MEKANIK OZELLIKLER
    # ─────────────────────────────────────────────
    elements.append(Paragraph("Mekanik Ozellikler", styles["heading"]))

    p = ctx.properties
    tags = p.method_tags
    props_data = [
        ["Ozellik / Property", "Deger / Value", "Birim / Unit", "ISO Yontem / Method"],
    ]

    wrap_style = ParagraphStyle("Wrap", fontSize=8, leading=10, fontName="Helvetica", textColor=colors.black)

    def _add_prop(name, value, unit, method):
        props_data.append([name, value, unit, Paragraph(method, wrap_style)])

    if p.elastic_modulus_gpa is not None:
        _add_prop("Elastik Modul (E)", f"{p.elastic_modulus_gpa:.1f}", "GPa",
                  tags.get("elastic_modulus", "OLS"))

    if p.yield_strength_mpa is not None:
        _add_prop("Akma Dayanimi", f"{p.yield_strength_mpa:.1f}", "MPa",
                  tags.get("yield", "---"))

    if p.yield_lower_mpa is not None:
        _add_prop("Alt Akma (ReL)", f"{p.yield_lower_mpa:.1f}", "MPa", tags.get("yield", "---"))

    if p.ultimate_tensile_mpa is not None:
        _add_prop("Cekme Dayanimi (Rm)", f"{p.ultimate_tensile_mpa:.1f}", "MPa", tags.get("uts", "---"))

    if p.elongation_at_break_pct is not None:
        _add_prop("Toplam Uzama (At)", f"{p.elongation_at_break_pct:.1f}", "%", tags.get("elongation", "---"))

    if p.uniform_elongation_pct is not None:
        _add_prop("Uniform Uzama (Ag)", f"{p.uniform_elongation_pct:.2f}", "%", tags.get("uniform_elongation", "---"))

    if p.strain_hardening_n is not None:
        _add_prop("Strain Hardening (n)", f"{p.strain_hardening_n:.3f}", "—",
                  tags.get("strain_hardening", "Hollomon"))

    if p.strength_coefficient_k is not None:
        _add_prop("Guc Katsayisi (K)", f"{p.strength_coefficient_k:.1f}", "MPa", tags.get("strain_hardening", "Hollomon"))

    if p.toughness_mj_m3 is not None:
        _add_prop("Modulus of Toughness (Ut)", f"{p.toughness_mj_m3:.2f}", "MJ/m3", tags.get("toughness", "---"))

    props_table = Table(props_data, colWidths=[4.5 * cm, 2.5 * cm, 2 * cm, 7.5 * cm])
    props_table.setStyle(TableStyle([
        # Header
        ("BACKGROUND", (0, 0), (-1, 0), COLOR_TABLE_HEADER),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
        # Body
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 4),
        ("TOPPADDING", (0, 1), (-1, -1), 4),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        # Deger kolonu bold
        ("FONTNAME", (1, 1), (1, -1), "Helvetica-Bold"),
        # Alternatif satir renkleri
        *[("BACKGROUND", (0, i), (-1, i), COLOR_TABLE_ALT)
          for i in range(2, len(props_data), 2)],
        # Grid
        ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ("LINEBELOW", (0, 0), (-1, 0), 1.5, COLOR_PRIMARY),
    ]))
    elements.append(props_table)

    # ─────────────────────────────────────────────
    # 3. STRESS-STRAIN GRAFIGI
    # ─────────────────────────────────────────────
    elements.append(Spacer(1, 8 * mm))
    elements.append(Paragraph("Stress-Strain Egrisi", styles["heading"]))

    plot_buf = generate_plot_image(ctx, title=f"Numune: {specimen_id}")
    if plot_buf:
        img = Image(plot_buf, width=15.5 * cm, height=9.3 * cm)
        elements.append(img)
    else:
        elements.append(Paragraph(
            "<i>Grafik uretilemedi (matplotlib yok)</i>", styles["body"]
        ))

    elements.append(PageBreak())

    # ─────────────────────────────────────────────
    # 4. ANOMALI OZETI
    # ─────────────────────────────────────────────
    elements.append(Paragraph("Anomali ve Kalite Raporu", styles["heading"]))

    # SNR bilgisi
    snr = ctx.extra.get("snr_db")
    noise_pct = ctx.extra.get("noise_pct")
    if snr:
        snr_text = f"Sinyal/Gurultu Orani (SNR): {snr:.1f} dB  |  Gurultu: {noise_pct:.2f}%"
        snr_color = COLOR_SUCCESS if snr >= 30 else (COLOR_WARNING if snr >= 20 else COLOR_DANGER)
        elements.append(Paragraph(snr_text, ParagraphStyle(
            "SNR", fontSize=10, fontName="Helvetica-Bold", textColor=snr_color,
            spaceBefore=2 * mm, spaceAfter=4 * mm,
        )))

    if ctx.anomalies:
        anomaly_data = [["Seviye", "Tip", "Aciklama", "Konum (strain)"]]
        wrap_style = ParagraphStyle("Wrap", fontSize=8, leading=10, fontName="Helvetica", textColor=colors.black)
        for a in ctx.anomalies:
            loc = f"{a.strain_location:.4f}" if a.strain_location else "--"
            desc = _s(a.description[:150] + ("..." if len(a.description) > 150 else ""))
            anomaly_data.append([
                a.severity.upper(),
                _s(a.anomaly_type.value),
                Paragraph(desc, wrap_style),
                loc,
            ])

        a_table = Table(anomaly_data, colWidths=[2 * cm, 3 * cm, 7.5 * cm, 3 * cm])
        a_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), COLOR_TABLE_HEADER),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ("LINEBELOW", (0, 0), (-1, 0), 1.5, COLOR_PRIMARY),
            # Seviye renklendirme
            *[("TEXTCOLOR", (0, i), (0, i),
               COLOR_DANGER if ctx.anomalies[i - 1].severity == "critical"
               else COLOR_WARNING if ctx.anomalies[i - 1].severity == "warning"
               else COLOR_SUCCESS)
              for i in range(1, len(anomaly_data))],
            *[("FONTNAME", (0, i), (0, i), "Helvetica-Bold")
              for i in range(1, len(anomaly_data))],
        ]))
        elements.append(a_table)
    else:
        elements.append(Paragraph(
            "Anomali tespit edilmedi.", styles["body"]
        ))

    # ─────────────────────────────────────────────
    # 5. PIPELINE LOG
    # ─────────────────────────────────────────────
    elements.append(Spacer(1, 8 * mm))
    elements.append(Paragraph("Pipeline Islem Loglari", styles["heading"]))

    log_data = [["Adim", "Durum", "Sure (ms)", "Mesaj"]]
    wrap_style_small = ParagraphStyle("WrapSmall", fontSize=7, leading=9, fontName="Helvetica", textColor=colors.black)
    for r in ctx.step_results:
        status_text = {"success": "OK", "warning": "UYARI", "failure": "HATA"}[r.status.value]
        msg = _s(r.message[:150] + ("..." if len(r.message) > 150 else ""))
        log_data.append([
            _s(r.step_name),
            status_text,
            f"{r.duration_ms:.1f}",
            Paragraph(msg, wrap_style_small),
        ])

    total_ms = sum(r.duration_ms for r in ctx.step_results)
    log_data.append(["TOPLAM", "", f"{total_ms:.1f}", f"{len(ctx.step_results)} adim"])

    log_table = Table(log_data, colWidths=[3.8 * cm, 1.5 * cm, 1.8 * cm, 8.4 * cm])
    log_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), COLOR_SECONDARY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.lightgrey),
        # Toplam satiri
        ("BACKGROUND", (0, -1), (-1, -1), COLOR_LIGHT_BG),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        # Durum renklendirme
        *[("TEXTCOLOR", (1, i), (1, i),
           COLOR_SUCCESS if ctx.step_results[i - 1].status.value == "success"
           else COLOR_WARNING if ctx.step_results[i - 1].status.value == "warning"
           else COLOR_DANGER)
          for i in range(1, len(log_data) - 1)],
    ]))
    elements.append(log_table)

    # ─────────────────────────────────────────────
    # 6. FOOTER — ISO/IEC 17025 Cl. 7.8.2.1 Alanlari
    # ─────────────────────────────────────────────
    elements.append(Spacer(1, 1 * cm))

    # 6a. Yetkilendirme / Imza Alani (Cl. 7.8.2.1(p))
    sig_data = [
        ["Hazirlayan", "Onaylayan"],
        ["Ad Soyad: ____________________", "Ad Soyad: ____________________"],
        ["Imza: ____________________", "Imza: ____________________"],
        ["Tarih: ____________________", "Tarih: ____________________"],
    ]
    sig_table = Table(sig_data, colWidths=[7.5 * cm, 7.5 * cm])
    sig_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW", (0, 0), (-1, 0), 1, COLOR_ACCENT),
        ("TEXTCOLOR", (0, 0), (-1, 0), COLOR_PRIMARY),
    ]))
    elements.append(sig_table)

    # 6b. Rapor uretim notu
    elements.append(Spacer(1, 8 * mm))
    elements.append(Paragraph(
        f"Bu rapor CurveIntel v0.1 tarafindan {now} tarihinde otomatik olarak uretilmistir. "
        f"Hesaplamalar {test_standard} standardina gore yapilmistir.",
        styles["small"],
    ))

    # 6c. Yasal uyari (footer tekrari — kisa versiyon)
    elements.append(Paragraph(
        "Bu yazilim herhangi bir akreditasyon kurulusu tarafindan akredite edilmemistir. "
        "Akredite test raporu ancak ISO/IEC 17025 kapsaminda akredite bir laboratuvar tarafindan duzenlenebilir.",
        ParagraphStyle("FooterDisclaimer", fontSize=7, textColor=COLOR_DANGER,
                       fontName="Helvetica-Bold", spaceBefore=3 * mm),
    ))


    # PDF olustur
    doc.build(elements)
    return output_path


def export_results_json(ctx: AnalysisContext, output_path: str | Path) -> Path:
    """Analiz sonuclarini JSON olarak export et."""
    output_path = Path(output_path)
    p = ctx.properties

    data = {
        "metadata": {
            "source_file": ctx.metadata.source_file,
            "specimen_id": ctx.metadata.specimen_id,
            "material_type": ctx.metadata.material_type.value,
            "stress_type": ctx.stress_type.value,
            "n_points": ctx.n_points,
            "generated_at": datetime.now().isoformat(),
        },
        "properties": {
            "elastic_modulus_gpa": p.elastic_modulus_gpa,
            "yield_strength_mpa": p.yield_strength_mpa,
            "yield_lower_mpa": p.yield_lower_mpa,
            "ultimate_tensile_mpa": p.ultimate_tensile_mpa,
            "elongation_at_break_pct": p.elongation_at_break_pct,
            "uniform_elongation_pct": p.uniform_elongation_pct,
            "strain_hardening_n": p.strain_hardening_n,
            "strength_coefficient_k": p.strength_coefficient_k,
            "toughness_mj_m3": p.toughness_mj_m3,
            "yield_behavior": p.yield_behavior.value,
        },
        "quality": {
            "snr_db": ctx.extra.get("snr_db"),
            "noise_pct": ctx.extra.get("noise_pct"),
            "elastic_r2": ctx.extra.get("elastic_r2"),
            "hollomon_r2": ctx.extra.get("hollomon_r2"),
            "quality_score": _quality_score(ctx)[0],
            "quality_grade": _quality_score(ctx)[1],
        },
        "anomalies": [
            {
                "type": a.anomaly_type.value,
                "severity": a.severity,
                "confidence": a.confidence,
                "description": a.description,
                "strain_location": a.strain_location,
            }
            for a in ctx.anomalies
        ],
        "pipeline": [
            {
                "step": r.step_name,
                "status": r.status.value,
                "duration_ms": round(r.duration_ms, 2),
                "message": r.message,
            }
            for r in ctx.step_results
        ],
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    return output_path


def export_results_csv(ctx: AnalysisContext, output_path: str | Path) -> Path:
    """Analiz sonuclarini tek satirlik CSV olarak export et (batch ozeti icin)."""
    output_path = Path(output_path)
    p = ctx.properties
    score, grade = _quality_score(ctx)

    row = {
        "source_file": ctx.metadata.source_file,
        "specimen_id": ctx.metadata.specimen_id,
        "material_type": ctx.metadata.material_type.value,
        "E_GPa": p.elastic_modulus_gpa,
        "Yield_MPa": p.yield_strength_mpa,
        "Yield_Lower_MPa": p.yield_lower_mpa,
        "UTS_MPa": p.ultimate_tensile_mpa,
        "Elongation_pct": p.elongation_at_break_pct,
        "Uniform_Elongation_pct": p.uniform_elongation_pct,
        "n_hardening": p.strain_hardening_n,
        "K_MPa": p.strength_coefficient_k,
        "Toughness_MJ_m3": p.toughness_mj_m3,
        "yield_behavior": p.yield_behavior.value,
        "SNR_dB": ctx.extra.get("snr_db"),
        "quality_score": score,
        "quality_grade": grade,
        "anomaly_count": len(ctx.anomalies),
        "warning_count": sum(1 for a in ctx.anomalies if a.severity == "warning"),
    }

    file_exists = output_path.exists()
    with open(output_path, "a", newline="", encoding="utf-8") as f:
        writer = csv_module.DictWriter(f, fieldnames=row.keys())
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)

    return output_path
