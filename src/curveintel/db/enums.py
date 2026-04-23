"""Shared database enums for CurveIntel persistence models."""

from enum import Enum


class UserRole(str, Enum):
    """Supported application roles."""

    ADMIN = "admin"
    ANALYST = "analyst"
    VIEWER = "viewer"


class AuditAction(str, Enum):
    """Append-only audit actions."""

    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    READ = "read"
    DOWNLOAD = "download"
    LOGIN = "login"
    LOGOUT = "logout"
    REGISTER = "register"
    SEED = "seed"


class AuditEntityType(str, Enum):
    """Entities addressable by the audit trail."""

    USER = "user"
    ANALYSIS_RESULT = "analysis_result"
    AUDIT_LOG = "audit_log"
    REPORT = "report"
    SYSTEM = "system"


class AuditStatus(str, Enum):
    """Outcome of an audited action."""

    SUCCESS = "success"
    FAILURE = "failure"
