"""Database package exports for CurveIntel."""

from src.curveintel.db.database import (
    Base,
    DatabaseSettings,
    SessionLocal,
    engine,
    get_database_settings,
    get_db_session,
    get_engine,
    reset_database_state,
)
from src.curveintel.db.enums import AuditAction, AuditEntityType, AuditStatus, UserRole
from src.curveintel.db.models import AnalysisResult, AuditLog, User
from src.curveintel.db.repository import (
    AnalysisResultRepository,
    AuditLogRepository,
    UserRepository,
)
from src.curveintel.db.service import (
    append_audit_event,
    ensure_database_schema_ready,
    persist_analysis_result,
    soft_delete_analyses,
)
from src.curveintel.db.schemas import (
    AnalysisRead,
    AnalysisSnapshotCreate,
    AuditEventCreate,
    AuditLogRead,
    UserCreate,
    UserRead,
)

__all__ = [
    "AnalysisRead",
    "AnalysisResult",
    "AnalysisResultRepository",
    "AnalysisSnapshotCreate",
    "AuditAction",
    "AuditEntityType",
    "AuditEventCreate",
    "AuditLog",
    "AuditLogRead",
    "AuditLogRepository",
    "AuditStatus",
    "Base",
    "DatabaseSettings",
    "SessionLocal",
    "User",
    "UserCreate",
    "UserRead",
    "UserRepository",
    "UserRole",
    "append_audit_event",
    "engine",
    "ensure_database_schema_ready",
    "get_database_settings",
    "get_db_session",
    "get_engine",
    "persist_analysis_result",
    "reset_database_state",
    "soft_delete_analyses",
]
