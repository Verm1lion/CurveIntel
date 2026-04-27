"""
CurveIntel Web - FastAPI backend with auth, RBAC, and audit logging.

Endpoints:
  GET  /                 -> Authenticated dashboard
  GET  /login            -> Browser login page
  POST /api/analyze      -> CSV upload + pipeline execution
  GET  /api/results      -> Persisted analysis results as JSON
  GET  /api/report/{id}  -> PDF report download
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from http import HTTPStatus
import os
import sys
from pathlib import Path
from typing import Any
from uuid import UUID

from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.exception_handlers import (
    http_exception_handler as fastapi_http_exception_handler,
    request_validation_exception_handler,
)
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException as StarletteHTTPException

# Pipeline imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from src import __version__ as CURVEINTEL_VERSION
from src.curveintel.auth.dependencies import get_optional_current_user, require_roles
from src.curveintel.auth.router import router as auth_router
from src.curveintel.auth.security import ensure_default_admin
from src.curveintel.db.database import SessionLocal, get_db_session, get_engine
from src.curveintel.db.enums import AuditAction, AuditEntityType, AuditStatus, UserRole
from src.curveintel.db.repository import (
    AnalysisResultRepository,
    AuditLogRepository,
    UserRepository,
)
from src.curveintel.db.schemas import UserRead, UserUpdate
from src.curveintel.db.service import (
    append_audit_event,
    ensure_database_schema_ready,
    persist_analysis_result,
)
from src.curveintel.db.serializers import (
    build_analysis_context_from_snapshot,
    build_analysis_payload,
)
from src.curveintel.web.settings import get_web_settings
from src.pipeline.anomaly import (
    CurveIntegrityChecker,
    GripSlippageDetector,
    NoiseAnalyzer,
    PropertyValidator,
    SensorSaturationDetector,
)
from src.pipeline.base import AnalysisContext, Pipeline
from src.pipeline.extraction import (
    ElasticModulusDetector,
    ElongationDetector,
    NeckingDetector,
    StrainHardeningFitter,
    StrainRateValidator,
    ToughnessCalculator,
    UTSDetector,
    YieldDetector,
)
from src.pipeline.ingestion import DataLoader, SchemaDetector, UnitConverter
from src.pipeline.preprocessing import (
    MonotonicityChecker,
    Resampler,
    SavitzkyGolayFilter,
    SpikeFilter,
    ToeCompensation,
)
from src.pipeline.reporting import generate_pdf_report


BASE_DIR = Path(__file__).parent
UPLOAD_DIR = BASE_DIR.parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)


def _open_db_session() -> Session:
    """Open a plain SQLAlchemy session for lifespan hooks."""

    get_engine()
    return SessionLocal()


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Application lifespan hooks."""

    ensure_database_schema_ready()
    db = _open_db_session()
    try:
        seeded_user = ensure_default_admin(db)
        if seeded_user is not None:
            append_audit_event(
                db,
                None,
                action=AuditAction.SEED,
                entity_type=AuditEntityType.USER,
                entity_id=str(seeded_user.id),
                actor_user_id=seeded_user.id,
                after_snapshot=seeded_user.model_dump(mode="json"),
                event_meta={"seed_kind": "default_admin"},
            )
    finally:
        db.close()

    await load_demo_data()
    yield


app = FastAPI(title="CurveIntel", version=CURVEINTEL_VERSION, lifespan=lifespan)
app.include_router(auth_router)
web_settings = get_web_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=web_settings.cors_allow_origins,
    allow_credentials=web_settings.cors_allow_credentials,
    allow_methods=web_settings.cors_allow_methods,
    allow_headers=web_settings.cors_allow_headers,
)

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


def render_template(
    request: Request,
    name: str,
    context: dict[str, Any],
    status_code: int = 200,
) -> HTMLResponse:
    """Render templates across old and new Starlette TemplateResponse signatures."""

    try:
        return templates.TemplateResponse(
            request=request,
            name=name,
            context=context,
            status_code=status_code,
        )
    except TypeError:
        return templates.TemplateResponse(name, context, status_code=status_code)


def _is_api_request(request: Request) -> bool:
    """Return whether the current request targets the JSON API surface."""

    return request.url.path.startswith("/api/")


def _api_error_code(status_code: int) -> str:
    """Map HTTP status codes to stable API error codes."""

    return {
        400: "bad_request",
        401: "unauthorized",
        403: "forbidden",
        404: "not_found",
        409: "conflict",
        422: "validation_error",
        500: "internal_server_error",
    }.get(status_code, "http_error")


def _api_error_response(
    request: Request,
    *,
    status_code: int,
    message: str,
    code: str | None = None,
    details: Any | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    """Build the standardized API error envelope."""

    payload: dict[str, Any] = {
        "status": "error",
        "error": {
            "code": code or _api_error_code(status_code),
            "message": message,
            "path": request.url.path,
        },
    }
    request_id = request.headers.get("x-request-id")
    if request_id:
        payload["error"]["request_id"] = request_id
    if details is not None:
        payload["error"]["details"] = details
    return JSONResponse(payload, status_code=status_code, headers=headers)


@app.exception_handler(StarletteHTTPException)
async def handle_http_exception(request: Request, exc: StarletteHTTPException):
    """Return standardized API errors while preserving default HTML behavior elsewhere."""

    if not _is_api_request(request):
        return await fastapi_http_exception_handler(request, exc)

    message = exc.detail if isinstance(exc.detail, str) else HTTPStatus(exc.status_code).phrase
    details = None if isinstance(exc.detail, str) else exc.detail
    return _api_error_response(
        request,
        status_code=exc.status_code,
        message=message,
        details=details,
        headers=dict(exc.headers or {}),
    )


@app.exception_handler(RequestValidationError)
async def handle_validation_exception(request: Request, exc: RequestValidationError):
    """Return structured validation errors for API routes."""

    if not _is_api_request(request):
        return await request_validation_exception_handler(request, exc)

    return _api_error_response(
        request,
        status_code=422,
        message="Request validation failed.",
        details=exc.errors(),
    )


@app.exception_handler(Exception)
async def handle_unexpected_exception(request: Request, exc: Exception):
    """Return safe standardized JSON for unexpected API failures."""

    if not _is_api_request(request):
        return HTMLResponse("Internal Server Error", status_code=500)

    details = None
    if web_settings.expose_internal_error_details:
        details = {
            "exception": exc.__class__.__name__,
            "message": str(exc),
        }
    return _api_error_response(
        request,
        status_code=500,
        message="Internal server error.",
        details=details,
    )


def build_pipeline(csv_path: Path) -> Pipeline:
    """Build the deterministic analysis pipeline."""

    return Pipeline(
        [
            DataLoader(csv_path),
            SchemaDetector(),
            UnitConverter(),
            SpikeFilter(window_size=5, threshold_sigma=3.0),
            MonotonicityChecker(),
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
        ]
    )


def ctx_to_dict(ctx: AnalysisContext, filename: str) -> dict[str, Any]:
    """Return the canonical dashboard payload for an analysis context."""

    return build_analysis_payload(ctx, filename)


def _resolve_upload_path(filename: str | None) -> Path:
    """Resolve a safe upload target inside the uploads directory."""

    if not filename:
        raise HTTPException(status_code=400, detail="Uploaded file must include a filename.")

    safe_name = Path(filename).name
    if safe_name in {"", ".", ".."}:
        raise HTTPException(status_code=400, detail="Uploaded file has an invalid filename.")
    return UPLOAD_DIR / safe_name


def _parse_analysis_id(result_id: str) -> UUID | None:
    """Parse a result identifier into a UUID."""

    try:
        return UUID(result_id)
    except ValueError:
        return None


def _parse_uuid(raw_value: str | None) -> UUID | None:
    """Parse optional UUID query values."""

    if raw_value in {None, ""}:
        return None
    try:
        return UUID(raw_value)
    except ValueError:
        return None


def _parse_enum_member(enum_cls: type[Any], raw_value: str | None) -> Any | None:
    """Parse optional enum query values without raising on invalid HTML filters."""

    if raw_value in {None, ""}:
        return None
    try:
        return enum_cls(raw_value)
    except ValueError:
        return None


def _get_recent_results_payloads(db: Session, limit: int = 10) -> list[dict[str, Any]]:
    """Load recent persisted results."""

    repo = AnalysisResultRepository(db)
    return [result.analysis_payload for result in repo.list_recent(limit=limit)]


def _get_persisted_result(db: Session, result_id: str):
    """Load a persisted analysis by its public UUID string."""

    parsed_id = _parse_analysis_id(result_id)
    if parsed_id is None:
        return None
    repo = AnalysisResultRepository(db)
    return repo.get_by_id(parsed_id)


def _get_dashboard_state(
    db: Session,
    *,
    selected_result_id: str | None = None,
    limit: int = 10,
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    """Return the selected dashboard result and the recent archive list."""

    batch_results = _get_recent_results_payloads(db, limit=limit)
    current = batch_results[0] if batch_results else None

    if not selected_result_id:
        return current, batch_results

    persisted = _get_persisted_result(db, selected_result_id)
    if persisted is None:
        return current, batch_results

    current = persisted.analysis_payload
    if all(result["id"] != current["id"] for result in batch_results):
        batch_results = [current, *batch_results[: max(limit - 1, 0)]]
    return current, batch_results


def _serialize_audit_logs(db: Session, entries: list[Any]) -> list[dict[str, Any]]:
    """Serialize audit DTOs with lightweight actor metadata for API/UI consumption."""

    user_repo = UserRepository(db)
    actor_cache: dict[str, dict[str, Any] | None] = {}
    items: list[dict[str, Any]] = []

    for entry in entries:
        actor = None
        if entry.actor_user_id is not None:
            actor_key = str(entry.actor_user_id)
            if actor_key not in actor_cache:
                actor_user = user_repo.get_by_id(entry.actor_user_id)
                actor_cache[actor_key] = (
                    {
                        "id": str(actor_user.id),
                        "email": actor_user.email,
                        "full_name": actor_user.full_name,
                        "role": actor_user.role.value,
                    }
                    if actor_user is not None
                    else None
                )
            actor = actor_cache[actor_key]

        items.append(
            {
                "id": str(entry.id),
                "occurred_at": entry.occurred_at.isoformat(),
                "actor_user_id": str(entry.actor_user_id) if entry.actor_user_id else None,
                "actor": actor,
                "action": entry.action.value,
                "entity_type": entry.entity_type.value,
                "entity_id": entry.entity_id,
                "request_id": entry.request_id,
                "ip_address": entry.ip_address,
                "user_agent": entry.user_agent,
                "status": entry.status.value,
                "before_snapshot": entry.before_snapshot,
                "after_snapshot": entry.after_snapshot,
                "event_meta": entry.event_meta,
            }
        )

    return items


def _serialize_users(entries: list[UserRead]) -> list[dict[str, Any]]:
    """Serialize users for dashboard and JSON responses."""

    return [
        {
            "id": str(entry.id),
            "email": entry.email,
            "full_name": entry.full_name,
            "role": entry.role.value,
            "is_active": entry.is_active,
            "created_at": entry.created_at.isoformat(),
            "updated_at": entry.updated_at.isoformat(),
            "last_login_at": entry.last_login_at.isoformat() if entry.last_login_at else None,
        }
        for entry in entries
    ]


def _get_user_payloads(db: Session, *, include_inactive: bool = True) -> list[dict[str, Any]]:
    """Load user management data for admin surfaces."""

    repo = UserRepository(db)
    return _serialize_users(repo.list_all(include_inactive=include_inactive))


def _workspace_copy(role: UserRole) -> dict[str, str]:
    """Return role-specific dashboard copy."""

    if role == UserRole.ADMIN:
        return {
            "label": "Admin Control Plane",
            "summary": "Manage users, review audit history, upload analyses, and clean the archive.",
        }
    if role == UserRole.ANALYST:
        return {
            "label": "Analyst Workspace",
            "summary": "Upload new tensile datasets, inspect persisted analyses, and download reports.",
        }
    return {
        "label": "Read-only Workspace",
        "summary": "Browse persisted analyses and reports without write or management permissions.",
    }


def _get_recent_audit_payloads(
    db: Session,
    *,
    limit: int = 25,
    entity_type: AuditEntityType | None = None,
    entity_id: str | None = None,
    action: AuditAction | None = None,
    status: AuditStatus | None = None,
    actor_user_id: UUID | None = None,
) -> list[dict[str, Any]]:
    """Load recent audit trail entries with optional entity filtering."""

    bounded_limit = max(1, min(limit, 200))
    repo = AuditLogRepository(db)
    entries = repo.list_filtered(
        limit=bounded_limit,
        entity_type=entity_type.value if entity_type is not None else None,
        entity_id=entity_id,
        action=action.value if action is not None else None,
        status=status.value if status is not None else None,
        actor_user_id=actor_user_id,
    )
    return _serialize_audit_logs(db, entries)


def _resolve_report_context(
    context_snapshot: dict[str, Any],
) -> tuple[AnalysisContext | None, str, str | None]:
    """Resolve a report context directly from the persisted snapshot."""

    try:
        return build_analysis_context_from_snapshot(context_snapshot), "snapshot_rehydrated", None
    except (TypeError, ValueError, KeyError) as exc:
        return None, "simplified_fallback", str(exc)


@app.get("/api/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""

    return {"status": "ok", "version": CURVEINTEL_VERSION, "engine": "CurveIntel"}


@app.get("/login", response_class=HTMLResponse)
async def login_page(
    request: Request,
    db: Session = Depends(get_db_session),
    current_user: UserRead | None = Depends(get_optional_current_user),
):
    """Login page with bootstrap registration support."""

    if current_user is not None:
        return RedirectResponse(url="/", status_code=303)

    bootstrap_mode = UserRepository(db).count_users() == 0
    return render_template(
        request=request,
        name="login.html",
        context={"request": request, "bootstrap_mode": bootstrap_mode},
    )


@app.get("/", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    db: Session = Depends(get_db_session),
    current_user: UserRead | None = Depends(get_optional_current_user),
):
    """Authenticated dashboard page."""

    if current_user is None:
        return RedirectResponse(url="/login", status_code=303)

    selected_result_id = request.query_params.get("id")
    current, recent_results = _get_dashboard_state(
        db,
        selected_result_id=selected_result_id,
        limit=10,
    )
    can_upload = current_user.role in {UserRole.ADMIN, UserRole.ANALYST}
    can_manage_results = current_user.role == UserRole.ADMIN
    audit_limit_raw = request.query_params.get("audit_limit", "12")
    try:
        audit_limit = max(5, min(int(audit_limit_raw), 50))
    except ValueError:
        audit_limit = 12

    audit_filters = {
        "entity_type": _parse_enum_member(
            AuditEntityType, request.query_params.get("audit_entity_type")
        ),
        "entity_id": request.query_params.get("audit_entity_id", "").strip() or None,
        "action": _parse_enum_member(AuditAction, request.query_params.get("audit_action")),
        "status": _parse_enum_member(AuditStatus, request.query_params.get("audit_status")),
        "actor_user_id": _parse_uuid(request.query_params.get("audit_actor_user_id")),
        "limit": audit_limit,
    }
    audit_logs = (
        _get_recent_audit_payloads(
            db,
            limit=audit_limit,
            entity_type=audit_filters["entity_type"],
            entity_id=audit_filters["entity_id"],
            action=audit_filters["action"],
            status=audit_filters["status"],
            actor_user_id=audit_filters["actor_user_id"],
        )
        if can_manage_results
        else []
    )
    admin_users = _get_user_payloads(db, include_inactive=True) if can_manage_results else []
    db_mode = "SQLite" if os.getenv("DATABASE_URL", "sqlite://").startswith("sqlite") else "PostgreSQL"
    return render_template(
        request=request,
        name="dashboard.html",
        context={
            "request": request,
            "current": current,
            "batch_results": recent_results,
            "has_data": current is not None,
            "current_user": current_user,
            "can_upload": can_upload,
            "can_manage_results": can_manage_results,
            "selected_result_id": current["id"] if current is not None else None,
            "audit_logs": audit_logs,
            "admin_users": admin_users,
            "audit_filters": {
                "entity_type": audit_filters["entity_type"].value
                if audit_filters["entity_type"] is not None
                else "",
                "entity_id": audit_filters["entity_id"] or "",
                "action": audit_filters["action"].value if audit_filters["action"] else "",
                "status": audit_filters["status"].value if audit_filters["status"] else "",
                "actor_user_id": str(audit_filters["actor_user_id"])
                if audit_filters["actor_user_id"] is not None
                else "",
                "limit": audit_limit,
            },
            "workspace_copy": _workspace_copy(current_user.role),
            "db_mode": db_mode,
        },
    )


@app.get("/guide", response_class=HTMLResponse)
async def guide_page(request: Request) -> HTMLResponse:
    """Usage guide page."""

    return render_template(
        request=request,
        name="guide.html",
        context={"request": request},
    )


@app.post("/api/analyze")
async def analyze(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db_session),
    current_user: UserRead = Depends(require_roles(UserRole.ADMIN, UserRole.ANALYST)),
) -> JSONResponse:
    """Upload a CSV file, persist the result, and emit an audit event."""

    save_path = _resolve_upload_path(file.filename)
    content = await file.read()
    with open(save_path, "wb") as file_handle:
        file_handle.write(content)

    try:
        pipeline = build_pipeline(save_path)
        ctx = AnalysisContext()
        ctx = pipeline.run(ctx)
        payload = ctx_to_dict(ctx, file.filename)
        persisted = persist_analysis_result(
            db,
            ctx,
            file.filename,
            source_file_path=save_path,
            created_by_user_id=current_user.id,
            analysis_id=payload["id"],
        )
        result = persisted.analysis_payload
        append_audit_event(
            db,
            request,
            action=AuditAction.CREATE,
            entity_type=AuditEntityType.ANALYSIS_RESULT,
            entity_id=str(persisted.id),
            actor_user_id=current_user.id,
            after_snapshot=result,
            event_meta={"source_filename": file.filename},
        )
        return JSONResponse({"status": "success", "data": result})
    except Exception as exc:
        append_audit_event(
            db,
            request,
            action=AuditAction.CREATE,
            entity_type=AuditEntityType.SYSTEM,
            entity_id=save_path.name,
            actor_user_id=current_user.id,
            status=AuditStatus.FAILURE,
            event_meta={"operation": "analyze", "error": str(exc)[:500]},
        )
        raise HTTPException(status_code=500, detail="Analysis execution failed.") from exc


@app.get("/api/results")
async def get_results(
    db: Session = Depends(get_db_session),
    _: UserRead = Depends(require_roles(UserRole.ADMIN, UserRole.ANALYST, UserRole.VIEWER)),
) -> JSONResponse:
    """Return persisted batch results."""

    return JSONResponse({"results": _get_recent_results_payloads(db, limit=100)})


@app.get("/api/users")
async def get_users(
    request: Request,
    include_inactive: bool = True,
    db: Session = Depends(get_db_session),
    current_user: UserRead = Depends(require_roles(UserRole.ADMIN)),
) -> JSONResponse:
    """Return users for admin management surfaces."""

    users = _get_user_payloads(db, include_inactive=include_inactive)
    append_audit_event(
        db,
        request,
        action=AuditAction.READ,
        entity_type=AuditEntityType.USER,
        entity_id="list",
        actor_user_id=current_user.id,
        event_meta={"include_inactive": include_inactive, "returned_count": len(users)},
    )
    return JSONResponse({"users": users, "count": len(users)})


@app.patch("/api/users/{user_id}")
async def update_user(
    user_id: str,
    payload: UserUpdate,
    request: Request,
    db: Session = Depends(get_db_session),
    current_user: UserRead = Depends(require_roles(UserRole.ADMIN)),
) -> JSONResponse:
    """Update role and activation state for an existing user."""

    parsed_id = _parse_uuid(user_id)
    if parsed_id is None:
        raise HTTPException(status_code=404, detail="User not found.")

    repo = UserRepository(db)
    existing = repo.get_by_id(parsed_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="User not found.")

    demotes_last_admin = (
        existing.role == UserRole.ADMIN
        and existing.is_active
        and (
            payload.is_active is False
            or (payload.role is not None and payload.role != UserRole.ADMIN)
        )
    )
    if demotes_last_admin and repo.count_active_admins(exclude_user_id=existing.id) == 0:
        raise HTTPException(
            status_code=409,
            detail="At least one active admin must remain in the system.",
        )

    updated = repo.update_managed_user(parsed_id, payload)
    if updated is None:
        raise HTTPException(status_code=404, detail="User not found.")

    append_audit_event(
        db,
        request,
        action=AuditAction.UPDATE,
        entity_type=AuditEntityType.USER,
        entity_id=user_id,
        actor_user_id=current_user.id,
        before_snapshot=existing.model_dump(mode="json"),
        after_snapshot=updated.model_dump(mode="json"),
        event_meta={
            "updated_fields": [
                field_name
                for field_name, value in payload.model_dump().items()
                if value is not None
            ]
        },
    )
    return JSONResponse({"status": "success", "user": updated.model_dump(mode="json")})


@app.get("/api/audit-logs")
async def get_audit_logs(
    request: Request,
    entity_type: AuditEntityType | None = None,
    entity_id: str | None = None,
    action: AuditAction | None = None,
    status: AuditStatus | None = None,
    actor_user_id: UUID | None = None,
    limit: int = 50,
    db: Session = Depends(get_db_session),
    current_user: UserRead = Depends(require_roles(UserRole.ADMIN)),
) -> JSONResponse:
    """Return recent audit trail entries for admins."""

    if entity_id is not None and entity_type is None:
        raise HTTPException(
            status_code=422, detail="entity_type is required when entity_id is provided."
        )

    items = _get_recent_audit_payloads(
        db,
        limit=limit,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        status=status,
        actor_user_id=actor_user_id,
    )
    append_audit_event(
        db,
        request,
        action=AuditAction.READ,
        entity_type=AuditEntityType.AUDIT_LOG,
        entity_id=entity_id or "recent",
        actor_user_id=current_user.id,
        event_meta={
            "filter_entity_type": entity_type.value if entity_type is not None else None,
            "filter_entity_id": entity_id,
            "filter_action": action.value if action is not None else None,
            "filter_status": status.value if status is not None else None,
            "filter_actor_user_id": str(actor_user_id) if actor_user_id is not None else None,
            "returned_count": len(items),
        },
    )
    return JSONResponse({"items": items, "count": len(items)})


@app.get("/api/report/{result_id}/pdf", response_model=None)
async def download_pdf(
    result_id: str,
    request: Request,
    db: Session = Depends(get_db_session),
    current_user: UserRead = Depends(
        require_roles(UserRole.ADMIN, UserRole.ANALYST, UserRole.VIEWER)
    ),
):
    """Download a PDF report for a single persisted result."""

    persisted = _get_persisted_result(db, result_id)
    if persisted is None:
        raise HTTPException(status_code=404, detail="Analysis result not found.")

    result = persisted.analysis_payload
    pdf_path = UPLOAD_DIR / f"report_{result_id}.pdf"
    ctx, report_source, report_context_error = _resolve_report_context(persisted.context_snapshot)

    if ctx:
        generate_pdf_report(
            ctx,
            output_path=pdf_path,
            company_name="CurveIntel Analysis Engine",
            test_standard="ISO 6892-1:2019",
        )
    else:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import cm
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

        doc = SimpleDocTemplate(str(pdf_path), pagesize=A4)
        styles = getSampleStyleSheet()
        elements = []
        elements.append(Paragraph("CurveIntel Analysis Report", styles["Title"]))
        elements.append(Spacer(1, 0.5 * cm))
        elements.append(Paragraph(f"File: {result['filename']}", styles["Normal"]))
        elements.append(Paragraph(f"Date: {result['timestamp']}", styles["Normal"]))
        elements.append(Paragraph(f"Quality: {result['quality']['score']}/100", styles["Normal"]))
        elements.append(Spacer(1, 0.5 * cm))
        elements.append(Paragraph("Mechanical Properties", styles["Heading2"]))
        properties = result["properties"]
        rows = [["Property", "Value"]]
        if properties.get("elastic_modulus_gpa"):
            rows.append(["E", f"{properties['elastic_modulus_gpa']} GPa"])
        if properties.get("yield_strength_mpa"):
            rows.append(["Rp0.2", f"{properties['yield_strength_mpa']} MPa"])
        if properties.get("ultimate_tensile_mpa"):
            rows.append(["Rm", f"{properties['ultimate_tensile_mpa']} MPa"])
        if properties.get("elongation_at_break_pct"):
            rows.append(["At", f"{properties['elongation_at_break_pct']}%"])
        table = Table(rows, colWidths=[6 * cm, 8 * cm])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1565c0")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ]
            )
        )
        elements.append(table)
        elements.append(Spacer(1, 1 * cm))
        elements.append(
            Paragraph(
                "<i>Context not available - simplified report. "
                "Re-upload the file for the full ISO report.</i>",
                styles["Normal"],
            )
        )
        doc.build(elements)

    append_audit_event(
        db,
        request,
        action=AuditAction.DOWNLOAD,
        entity_type=AuditEntityType.REPORT,
        entity_id=result_id,
        actor_user_id=current_user.id,
        after_snapshot={"result_id": result_id, "filename": result["filename"]},
        event_meta={
            "report_source": report_source,
            "context_error": report_context_error,
        },
    )

    def iterfile():
        with open(pdf_path, "rb") as file_handle:
            yield from file_handle

    return StreamingResponse(
        iterfile(),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=CurveIntel_{result_id}.pdf"},
    )


@app.delete("/api/results/clear")
async def clear_results(
    request: Request,
    db: Session = Depends(get_db_session),
    current_user: UserRead = Depends(require_roles(UserRole.ADMIN)),
) -> JSONResponse:
    """Soft-delete all active persisted results."""

    repo = AnalysisResultRepository(db)
    active_results = repo.list_recent(limit=None)
    deleted_count = 0
    for active_result in active_results:
        deleted = repo.soft_delete(active_result.id, deleted_by_user_id=current_user.id)
        if deleted is None:
            continue
        deleted_count += 1
        append_audit_event(
            db,
            request,
            action=AuditAction.DELETE,
            entity_type=AuditEntityType.ANALYSIS_RESULT,
            entity_id=str(deleted.id),
            actor_user_id=current_user.id,
            before_snapshot=active_result.analysis_payload,
            after_snapshot={
                "id": str(deleted.id),
                "deleted_at": deleted.deleted_at.isoformat() if deleted.deleted_at else None,
                "deleted_by_user_id": str(current_user.id),
            },
        )

    return JSONResponse({"status": "cleared", "deleted_count": deleted_count})


@app.get("/api/results/{result_id}")
async def get_result(
    result_id: str,
    db: Session = Depends(get_db_session),
    _: UserRead = Depends(require_roles(UserRole.ADMIN, UserRole.ANALYST, UserRole.VIEWER)),
) -> JSONResponse:
    """Return a single persisted result."""

    persisted = _get_persisted_result(db, result_id)
    if persisted is None:
        raise HTTPException(status_code=404, detail="Analysis result not found.")
    return JSONResponse(persisted.analysis_payload)


@app.delete("/api/results/{result_id}")
async def delete_result(
    result_id: str,
    request: Request,
    db: Session = Depends(get_db_session),
    current_user: UserRead = Depends(require_roles(UserRole.ADMIN)),
) -> JSONResponse:
    """Soft-delete a single persisted result."""

    parsed_id = _parse_analysis_id(result_id)
    if parsed_id is None:
        raise HTTPException(status_code=404, detail="Analysis result not found.")

    repo = AnalysisResultRepository(db)
    existing = repo.get_by_id(parsed_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Analysis result not found.")

    deleted = repo.soft_delete(parsed_id, deleted_by_user_id=current_user.id)
    if deleted is None:
        raise HTTPException(status_code=404, detail="Analysis result not found.")

    append_audit_event(
        db,
        request,
        action=AuditAction.DELETE,
        entity_type=AuditEntityType.ANALYSIS_RESULT,
        entity_id=result_id,
        actor_user_id=current_user.id,
        before_snapshot=existing.analysis_payload,
        after_snapshot={
            "id": result_id,
            "deleted_at": deleted.deleted_at.isoformat() if deleted.deleted_at else None,
            "deleted_by_user_id": str(current_user.id),
        },
    )
    return JSONResponse({"status": "deleted", "id": result_id})


def _analyze_path(csv_path: Path) -> tuple[dict[str, Any], AnalysisContext] | tuple[None, None]:
    """Run the pipeline synchronously for a file path."""

    try:
        pipeline = build_pipeline(csv_path)
        ctx = AnalysisContext()
        ctx = pipeline.run(ctx)
        if ctx.has_data:
            return ctx_to_dict(ctx, csv_path.name), ctx
    except Exception:
        pass
    return None, None


def _demo_data_enabled() -> bool:
    """Return whether demo seeding is explicitly enabled."""

    return os.getenv("CURVEINTEL_LOAD_DEMO_DATA", "").strip().lower() in {"1", "true", "yes", "on"}


def _resolve_demo_files() -> list[Path]:
    """Resolve demo files from the configured directory."""

    demo_root = os.getenv("CURVEINTEL_DEMO_DATA_DIR", "").strip()
    if not demo_root:
        print("[STARTUP] Demo seeding requested but CURVEINTEL_DEMO_DATA_DIR is not set.")
        return []

    base = Path(demo_root)
    return [
        base / "C00Al6xxxT4Numisheet2020R01T1.521W17.91-S-Stress-Strain.csv",
        base / "C00FeDP1180Numisheet2020R01T1.046W17.93-S-Stress-Strain.csv",
        base / "C00FeDP980Numisheet2020R01T1.424W17.93-S-Stress-Strain.csv",
    ]


async def load_demo_data() -> None:
    """Seed demo data only when explicitly enabled."""

    if not _demo_data_enabled():
        return

    demo_files = _resolve_demo_files()
    if not demo_files:
        return

    db = _open_db_session()
    seeded_count = 0
    try:
        print("[STARTUP] Loading explicit demo data...")
        for demo_file in demo_files:
            if not demo_file.exists():
                continue

            result, ctx = _analyze_path(demo_file)
            if not result or ctx is None:
                continue

            persisted = persist_analysis_result(
                db,
                ctx,
                demo_file.name,
                source_file_path=demo_file,
                analysis_id=result["id"],
            )
            payload = persisted.analysis_payload
            seeded_count += 1
            append_audit_event(
                db,
                None,
                action=AuditAction.SEED,
                entity_type=AuditEntityType.ANALYSIS_RESULT,
                entity_id=str(persisted.id),
                after_snapshot=payload,
                event_meta={"seed_kind": "demo_data"},
            )
            print(
                f"  [OK] {demo_file.name}: UTS={payload['properties']['ultimate_tensile_mpa']} MPa"
            )
        print(f"[STARTUP] {seeded_count} demo analyses ready.")
    finally:
        db.close()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
