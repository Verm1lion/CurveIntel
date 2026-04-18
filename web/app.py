"""
CurveIntel Web — FastAPI Backend.

Endpoints:
  GET  /            → Dashboard (son analiz sonuclari)
  POST /api/analyze  → CSV upload + pipeline calistir
  GET  /api/results  → Tum batch sonuclari (JSON)
  GET  /api/curve/{id} → Stress-strain curve data (JSON)
"""
from __future__ import annotations

import json
import sys
import uuid
import time
from io import BytesIO
from pathlib import Path
from typing import Any

import numpy as np
from fastapi import FastAPI, File, UploadFile, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# Pipeline imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.pipeline.base import AnalysisContext, Pipeline
from src.pipeline.ingestion import DataLoader, SchemaDetector, UnitConverter
from src.pipeline.preprocessing import (
    Resampler, SavitzkyGolayFilter, SpikeFilter, ToeCompensation,
)
from src.pipeline.extraction import (
    ElasticModulusDetector, ElongationDetector, NeckingDetector,
    StrainHardeningFitter, StrainRateValidator, ToughnessCalculator,
    UTSDetector, YieldDetector,
)
from src.pipeline.anomaly import (
    GripSlippageDetector, SensorSaturationDetector,
    NoiseAnalyzer, CurveIntegrityChecker, PropertyValidator,
)
from src.pipeline.reporting import _quality_score, generate_pdf_report

# ── App setup ──
app = FastAPI(title="CurveIntel", version="1.0.0")

BASE_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

# ── In-memory results store ──
analysis_results: list[dict[str, Any]] = []
UPLOAD_DIR = BASE_DIR.parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)


@app.get("/api/health")
async def health_check():
    """Health check endpoint (Docker HEALTHCHECK)."""
    return {"status": "ok", "version": "1.0.0", "engine": "CurveIntel"}


def build_pipeline(csv_path: Path) -> Pipeline:
    return Pipeline([
        DataLoader(csv_path),
        SchemaDetector(),
        UnitConverter(),
        SpikeFilter(window_size=5, threshold_sigma=3.0),
        ToeCompensation(),
        Resampler(n_points=2000),
        SavitzkyGolayFilter(window_length=21, polyorder=3),
        ElasticModulusDetector(),
        YieldDetector(),
        UTSDetector(),
        ElongationDetector(),
        NeckingDetector(),
        StrainHardeningFitter(),
        ToughnessCalculator(),
        StrainRateValidator(),
        GripSlippageDetector(),
        SensorSaturationDetector(),
        NoiseAnalyzer(),
        CurveIntegrityChecker(),
        PropertyValidator(),
    ])


def ctx_to_dict(ctx: AnalysisContext, filename: str) -> dict[str, Any]:
    """AnalysisContext -> dashboard-friendly dict."""
    p = ctx.properties
    score, grade = _quality_score(ctx)

    # Curve data: downsample to max 500 points for chart
    strain_list = []
    stress_list = []
    if ctx.has_data and len(ctx.strain) > 0:
        step = max(1, len(ctx.strain) // 500)
        strain_list = ctx.strain[::step].tolist()
        stress_list = ctx.stress[::step].tolist()

    # Yield point
    yield_strain = ctx.extra.get("yield_strain")
    uts_idx = ctx.extra.get("uts_idx")
    neck_idx = ctx.extra.get("necking_idx")

    yield_point = None
    if yield_strain is not None and p.yield_strength_mpa is not None:
        yield_point = {"strain": float(yield_strain), "stress": float(p.yield_strength_mpa)}

    uts_point = None
    if uts_idx is not None and p.ultimate_tensile_mpa is not None and ctx.has_data:
        uts_point = {"strain": float(ctx.strain[uts_idx]), "stress": float(p.ultimate_tensile_mpa)}

    neck_point = None
    if neck_idx is not None and ctx.has_data:
        neck_point = {"strain": float(ctx.strain[neck_idx]), "stress": float(ctx.stress[neck_idx])}

    # Pipeline steps
    steps = []
    total_ms = 0
    for r in ctx.step_results:
        steps.append({
            "name": r.step_name,
            "status": r.status.value,
            "duration_ms": round(r.duration_ms, 2),
            "message": r.message,
        })
        total_ms += r.duration_ms

    # Pipeline layer summary (for stepper UI)
    layer_status = {
        "ingestion": "success",
        "preprocessing": "success",
        "extraction": "success",
        "anomaly": "success",
        "reporting": "success",
    }
    for r in ctx.step_results:
        name = r.step_name.lower()
        if name in ("dataloader", "schemadetector", "unitconverter"):
            layer = "ingestion"
        elif name in ("spikefilter", "toecompensation", "resampler", "savitzkygolayfilter"):
            layer = "preprocessing"
        elif name in ("elasticmodulusdetector", "yielddetector", "utsdetector",
                      "elongationdetector", "neckingdetector", "strainhardeningfitter",
                      "toughnesscalculator"):
            layer = "extraction"
        elif name in ("gripslippagedetector", "sensorsaturationdetector", "noiseanalyzer",
                      "curveintegritychecker", "propertyvalidator"):
            layer = "anomaly"
        else:
            layer = "reporting"

        if r.status.value == "failure":
            layer_status[layer] = "failure"
        elif r.status.value == "warning" and layer_status[layer] != "failure":
            layer_status[layer] = "warning"

    # Anomalies
    anomalies = []
    info_count = warn_count = crit_count = 0
    for a in ctx.anomalies:
        anomalies.append({
            "type": a.anomaly_type.value,
            "severity": a.severity,
            "description": a.description,
            "confidence": a.confidence,
            "strain_location": a.strain_location,
        })
        if a.severity == "info":
            info_count += 1
        elif a.severity == "warning":
            warn_count += 1
        else:
            crit_count += 1

    result_id = str(uuid.uuid4())[:8]

    # Vendor detection info
    vendor_name = ctx.extra.get("vendor_name", "Generic CSV")
    vendor_confidence = ctx.extra.get("vendor_confidence", 0)
    detected_encoding = ctx.extra.get("detected_encoding", "utf-8")
    detected_separator = ctx.extra.get("detected_separator", ",")

    # Strain rate info
    strain_rate_range = ctx.extra.get("strain_rate_range", None)
    strain_rate_code = ctx.extra.get("strain_rate_code", None)
    strain_rate_value = ctx.extra.get("strain_rate_median", None)
    strain_rate_compliant = ctx.extra.get("strain_rate_compliant", None)

    return {
        "id": result_id,
        "filename": filename,
        "timestamp": time.strftime("%Y-%m-%d %H:%M"),
        "material_type": ctx.metadata.material_type.value if ctx.metadata.material_type else "unknown",
        "stress_type": ctx.stress_type.value,
        "n_points": ctx.n_points,
        "properties": {
            "elastic_modulus_gpa": round(p.elastic_modulus_gpa, 1) if p.elastic_modulus_gpa else None,
            "yield_strength_mpa": round(p.yield_strength_mpa, 1) if p.yield_strength_mpa else None,
            "yield_lower_mpa": round(p.yield_lower_mpa, 1) if p.yield_lower_mpa else None,
            "ultimate_tensile_mpa": round(p.ultimate_tensile_mpa, 1) if p.ultimate_tensile_mpa else None,
            "elongation_at_break_pct": round(p.elongation_at_break_pct, 1) if p.elongation_at_break_pct else None,
            "uniform_elongation_pct": round(p.uniform_elongation_pct, 2) if p.uniform_elongation_pct else None,
            "strain_hardening_n": round(p.strain_hardening_n, 3) if p.strain_hardening_n else None,
            "strength_coefficient_k": round(p.strength_coefficient_k, 1) if p.strength_coefficient_k else None,
            "toughness_mj_m3": round(p.toughness_mj_m3, 2) if p.toughness_mj_m3 else None,
            "yield_behavior": p.yield_behavior.value,
            "method_tags": dict(p.method_tags),
        },
        "quality": {
            "score": round(score, 0),
            "grade": grade.split("(")[0].strip(),
            "grade_label": grade,
            "snr_db": round(ctx.extra.get("snr_db", 0), 1),
            "noise_pct": round(ctx.extra.get("noise_pct", 0), 2),
            "elastic_r2": round(ctx.extra.get("elastic_r2", 0), 6),
            "elastic_sm_rel": round(ctx.extra.get("elastic_sm_rel", 0), 2),
            "elastic_n_points": ctx.extra.get("elastic_n_points"),
            "elastic_iterations": ctx.extra.get("elastic_iterations"),
        },
        "vendor": {
            "name": vendor_name,
            "confidence": vendor_confidence,
            "encoding": detected_encoding,
            "separator": detected_separator,
        },
        "strain_rate": {
            "range": strain_rate_range,
            "code": strain_rate_code,
            "value": round(strain_rate_value, 6) if strain_rate_value else None,
            "compliant": strain_rate_compliant,
        },
        "curve": {
            "strain": strain_list,
            "stress": stress_list,
            "yield_point": yield_point,
            "uts_point": uts_point,
            "neck_point": neck_point,
        },
        "pipeline": {
            "steps": steps,
            "total_ms": round(total_ms, 1),
            "layer_status": layer_status,
        },
        "anomalies": {
            "entries": anomalies,
            "total": len(anomalies),
            "info": info_count,
            "warning": warn_count,
            "critical": crit_count,
        },
    }


# ── Routes ──

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Ana dashboard sayfasi."""
    # Son analiz sonucu (varsa)
    current = analysis_results[-1] if analysis_results else None
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "current": current,
        "batch_results": analysis_results[-10:],  # Son 10
        "has_data": current is not None,
    })


@app.post("/api/analyze")
async def analyze(file: UploadFile = File(...)):
    """CSV upload edip pipeline calistir."""
    # Dosyayi kaydet
    save_path = UPLOAD_DIR / file.filename
    content = await file.read()
    with open(save_path, "wb") as f:
        f.write(content)

    # Pipeline calistir
    try:
        pipeline = build_pipeline(save_path)
        ctx = AnalysisContext()
        ctx = pipeline.run(ctx)
        result = ctx_to_dict(ctx, file.filename)
        analysis_results.append(result)
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@app.get("/api/results")
async def get_results():
    """Tum batch sonuclari."""
    return JSONResponse({"results": analysis_results})


@app.get("/api/report/{result_id}/pdf")
async def download_pdf(result_id: str):
    """PDF rapor indir."""
    for r in analysis_results:
        if r["id"] == result_id:
            # Rebuild context minimally for PDF
            pdf_path = UPLOAD_DIR / f"report_{result_id}.pdf"
            from src.pipeline.base import AnalysisContext as AC, MechanicalProperties
            ctx = AC()
            # We need the original ctx — for now generate a summary PDF
            # from the stored result dict
            props_text = []
            p = r["properties"]
            if p.get("elastic_modulus_gpa"): props_text.append(f"E = {p['elastic_modulus_gpa']} GPa")
            if p.get("yield_strength_mpa"): props_text.append(f"Rp0.2 = {p['yield_strength_mpa']} MPa")
            if p.get("ultimate_tensile_mpa"): props_text.append(f"Rm = {p['ultimate_tensile_mpa']} MPa")
            if p.get("elongation_at_break_pct"): props_text.append(f"At = {p['elongation_at_break_pct']}%")

            # Simple PDF with reportlab
            from reportlab.lib.pagesizes import A4
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.lib import colors
            from reportlab.lib.units import cm

            doc = SimpleDocTemplate(str(pdf_path), pagesize=A4)
            styles = getSampleStyleSheet()
            elements = []
            elements.append(Paragraph("CurveIntel Analysis Report", styles["Title"]))
            elements.append(Spacer(1, 0.5 * cm))
            elements.append(Paragraph(f"File: {r['filename']}", styles["Normal"]))
            elements.append(Paragraph(f"Date: {r['timestamp']}", styles["Normal"]))
            elements.append(Paragraph(f"Material: {r['material_type']}", styles["Normal"]))
            elements.append(Paragraph(f"Vendor: {r.get('vendor', {}).get('name', 'Generic')}", styles["Normal"]))
            elements.append(Paragraph(f"Quality: {r['quality']['score']}/100 ({r['quality']['grade_label']})", styles["Normal"]))
            elements.append(Spacer(1, 0.5 * cm))
            elements.append(Paragraph("Mechanical Properties", styles["Heading2"]))
            rows = [["Property", "Value"]]
            for line in props_text:
                k, v = line.split(" = ")
                rows.append([k, v])
            if p.get("strain_hardening_n"): rows.append(["n", str(p["strain_hardening_n"])])
            if p.get("toughness_mj_m3"): rows.append(["Ut", f"{p['toughness_mj_m3']} MJ/m³"])
            t = Table(rows, colWidths=[6*cm, 8*cm])
            t.setStyle(TableStyle([
                ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#1565c0")),
                ("TEXTCOLOR", (0,0), (-1,0), colors.white),
                ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
                ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
            ]))
            elements.append(t)
            elements.append(Spacer(1, 1 * cm))
            elements.append(Paragraph(
                "<i>LEGAL NOTICE: Calculations performed per ISO 6892-1:2019. "
                "This software is NOT accredited by any accreditation body.</i>",
                styles["Normal"]
            ))
            doc.build(elements)

            def iterfile():
                with open(pdf_path, "rb") as f:
                    yield from f

            return StreamingResponse(
                iterfile(),
                media_type="application/pdf",
                headers={"Content-Disposition": f"attachment; filename=CurveIntel_{result_id}.pdf"}
            )
    return JSONResponse({"error": "Not found"}, status_code=404)


@app.get("/api/results/{result_id}")
async def get_result(result_id: str):
    """Tek sonuc detayi."""
    for r in analysis_results:
        if r["id"] == result_id:
            return JSONResponse(r)
    return JSONResponse({"error": "Not found"}, status_code=404)


def _analyze_path(csv_path: Path) -> dict[str, Any] | None:
    """Dosya yolundan pipeline calistir (senkron)."""
    try:
        pipeline = build_pipeline(csv_path)
        ctx = AnalysisContext()
        ctx = pipeline.run(ctx)
        if ctx.has_data:
            return ctx_to_dict(ctx, csv_path.name)
    except Exception:
        pass
    return None


@app.on_event("startup")
async def load_demo_data():
    """Sunucu basladiginda demo verilerini yukle."""
    demo_files = [
        Path(r"c:\Users\MSI\Desktop\Test_Cihazlari_Proje\veri_setleri\nist_numisheet\C00Al6xxxT4Numisheet2020R01T1.521W17.91-S-Stress-Strain.csv"),
        Path(r"c:\Users\MSI\Desktop\Test_Cihazlari_Proje\veri_setleri\nist_numisheet\C00FeDP1180Numisheet2020R01T1.046W17.93-S-Stress-Strain.csv"),
        Path(r"c:\Users\MSI\Desktop\Test_Cihazlari_Proje\veri_setleri\nist_numisheet\C00FeDP980Numisheet2020R01T1.424W17.93-S-Stress-Strain.csv"),
    ]
    print("[STARTUP] Demo verileri yukleniyor...")
    for f in demo_files:
        if f.exists():
            result = _analyze_path(f)
            if result:
                analysis_results.append(result)
                print(f"  [OK] {f.name}: UTS={result['properties']['ultimate_tensile_mpa']} MPa")
    print(f"[STARTUP] {len(analysis_results)} analiz hazir.")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)

