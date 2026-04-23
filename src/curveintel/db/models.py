"""SQLAlchemy ORM models for CurveIntel persistence."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, JSON, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.curveintel.db.database import Base
from src.curveintel.db.enums import AuditAction, AuditEntityType, AuditStatus, UserRole


def utcnow() -> datetime:
    """Return a timezone-aware UTC timestamp."""

    return datetime.now(timezone.utc)


UUID_TYPE = Uuid(as_uuid=True)
JSON_TYPE = JSON().with_variant(JSONB, "postgresql")


def enum_values(enum_cls: type[Any]) -> list[str]:
    """Return enum values in declaration order for SQLAlchemy enum columns."""

    return [member.value for member in enum_cls]


class User(Base):
    """Application user persisted for authentication and ownership."""

    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(UUID_TYPE, primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role", values_callable=enum_values),
        nullable=False,
        default=UserRole.VIEWER,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_analyses: Mapped[list["AnalysisResult"]] = relationship(
        back_populates="created_by",
        foreign_keys="AnalysisResult.created_by_user_id",
    )
    deleted_analyses: Mapped[list["AnalysisResult"]] = relationship(
        back_populates="deleted_by",
        foreign_keys="AnalysisResult.deleted_by_user_id",
    )
    audit_events: Mapped[list["AuditLog"]] = relationship(
        back_populates="actor_user",
        foreign_keys="AuditLog.actor_user_id",
    )


class AnalysisResult(Base):
    """Persisted tensile analysis result and serialized trace."""

    __tablename__ = "analysis_results"

    id: Mapped[UUID] = mapped_column(UUID_TYPE, primary_key=True, default=uuid4)
    source_filename: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    source_file_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    input_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    material_type: Mapped[str] = mapped_column(String(64), nullable=False, default="unknown")
    stress_type: Mapped[str] = mapped_column(String(32), nullable=False, default="engineering")
    quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    quality_grade: Mapped[str | None] = mapped_column(String(32), nullable=True)
    elastic_modulus_gpa: Mapped[float | None] = mapped_column(Float, nullable=True)
    yield_strength_mpa: Mapped[float | None] = mapped_column(Float, nullable=True)
    yield_lower_mpa: Mapped[float | None] = mapped_column(Float, nullable=True)
    ultimate_tensile_mpa: Mapped[float | None] = mapped_column(Float, nullable=True)
    elongation_at_break_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    uniform_elongation_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    strain_hardening_n: Mapped[float | None] = mapped_column(Float, nullable=True)
    strength_coefficient_k: Mapped[float | None] = mapped_column(Float, nullable=True)
    toughness_mj_m3: Mapped[float | None] = mapped_column(Float, nullable=True)
    analysis_payload: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, nullable=False)
    context_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, nullable=False)
    engine_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_by_user_id: Mapped[UUID | None] = mapped_column(
        UUID_TYPE,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        index=True,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    deleted_by_user_id: Mapped[UUID | None] = mapped_column(
        UUID_TYPE,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    created_by: Mapped[User | None] = relationship(
        back_populates="created_analyses",
        foreign_keys=[created_by_user_id],
    )
    deleted_by: Mapped[User | None] = relationship(
        back_populates="deleted_analyses",
        foreign_keys=[deleted_by_user_id],
    )


class AuditLog(Base):
    """Append-only audit trail entry."""

    __tablename__ = "audit_logs"

    id: Mapped[UUID] = mapped_column(UUID_TYPE, primary_key=True, default=uuid4)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        index=True,
    )
    actor_user_id: Mapped[UUID | None] = mapped_column(
        UUID_TYPE,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    action: Mapped[AuditAction] = mapped_column(
        Enum(AuditAction, name="audit_action", values_callable=enum_values),
        nullable=False,
    )
    entity_type: Mapped[AuditEntityType] = mapped_column(
        Enum(AuditEntityType, name="audit_entity_type", values_callable=enum_values),
        nullable=False,
        index=True,
    )
    entity_id: Mapped[str] = mapped_column(String(128), nullable=False)
    request_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[AuditStatus] = mapped_column(
        Enum(AuditStatus, name="audit_status", values_callable=enum_values),
        nullable=False,
    )
    before_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE, nullable=True)
    after_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE, nullable=True)
    event_meta: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, nullable=False, default=dict)

    actor_user: Mapped[User | None] = relationship(
        back_populates="audit_events",
        foreign_keys=[actor_user_id],
    )
