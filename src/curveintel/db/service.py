"""Persistence and audit service helpers for CurveIntel."""

from __future__ import annotations

from collections.abc import Iterable
import ipaddress
from pathlib import Path
from typing import Any
from uuid import UUID

from fastapi import Request
from sqlalchemy import inspect
from sqlalchemy.orm import Session

from src.curveintel.db.database import get_engine
from src.curveintel.db.enums import AuditAction, AuditEntityType, AuditStatus
from src.curveintel.db.repository import AnalysisResultRepository, AuditLogRepository
from src.curveintel.db.schemas import AnalysisRead, AuditEventCreate, AuditLogRead
from src.curveintel.db.serializers import build_analysis_snapshot_from_context
from src.pipeline.base import AnalysisContext


REQUIRED_TABLES = {"users", "analysis_results", "audit_logs"}


def ensure_database_schema_ready() -> None:
    """Ensure the required DB tables exist before serving requests."""

    inspector = inspect(get_engine())
    existing_tables = set(inspector.get_table_names())
    missing_tables = REQUIRED_TABLES - existing_tables
    if missing_tables:
        missing_list = ", ".join(sorted(missing_tables))
        raise RuntimeError(
            "Database schema is not ready. Run `alembic upgrade head` before starting CurveIntel. "
            f"Missing tables: {missing_list}."
        )


def append_audit_event(
    session: Session,
    request: Request | None,
    *,
    action: AuditAction,
    entity_type: AuditEntityType,
    entity_id: str,
    actor_user_id: UUID | None = None,
    status: AuditStatus = AuditStatus.SUCCESS,
    before_snapshot: dict[str, Any] | None = None,
    after_snapshot: dict[str, Any] | None = None,
    event_meta: dict[str, Any] | None = None,
) -> AuditLogRead:
    """Append an audit event using request metadata when available."""

    request_id = None
    ip_address = None
    user_agent = None
    merged_meta = dict(event_meta or {})

    if request is not None:
        request_id = request.headers.get("x-request-id")
        raw_client_host = request.client.host if request.client else None
        if raw_client_host is not None:
            try:
                ipaddress.ip_address(raw_client_host)
                ip_address = raw_client_host
            except ValueError:
                merged_meta.setdefault("client_host", raw_client_host)
        user_agent = request.headers.get("user-agent")
        merged_meta.setdefault("path", request.url.path)
        merged_meta.setdefault("method", request.method)

    repo = AuditLogRepository(session)
    return repo.append(
        AuditEventCreate(
            actor_user_id=actor_user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            request_id=request_id,
            ip_address=ip_address,
            user_agent=user_agent,
            status=status,
            before_snapshot=before_snapshot,
            after_snapshot=after_snapshot,
            event_meta=merged_meta,
        )
    )


def persist_analysis_result(
    session: Session,
    ctx: AnalysisContext,
    filename: str,
    *,
    source_file_path: str | Path | None = None,
    created_by_user_id: UUID | None = None,
    analysis_id: UUID | str | None = None,
) -> AnalysisRead:
    """Persist a completed analysis context."""

    snapshot = build_analysis_snapshot_from_context(
        ctx,
        filename=filename,
        source_file_path=source_file_path,
        created_by_user_id=created_by_user_id,
        analysis_id=analysis_id,
    )
    repo = AnalysisResultRepository(session)
    return repo.create_from_snapshot(snapshot)


def soft_delete_analyses(
    session: Session,
    analysis_ids: Iterable[UUID],
    *,
    deleted_by_user_id: UUID | None = None,
) -> list[AnalysisRead]:
    """Soft-delete multiple analyses and return the mutated records."""

    repo = AnalysisResultRepository(session)
    deleted: list[AnalysisRead] = []
    for analysis_id in analysis_ids:
        result = repo.soft_delete(analysis_id, deleted_by_user_id=deleted_by_user_id)
        if result is not None:
            deleted.append(result)
    return deleted
