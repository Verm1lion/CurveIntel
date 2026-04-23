"""Repository layer for CurveIntel persistence."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.curveintel.db.enums import UserRole
from src.curveintel.db.models import AnalysisResult, AuditLog, User
from src.curveintel.db.schemas import (
    AnalysisRead,
    AnalysisSnapshotCreate,
    AuditEventCreate,
    AuditLogRead,
    UserCreate,
    UserRead,
    UserUpdate,
)


def utcnow() -> datetime:
    """Return a timezone-aware UTC timestamp."""

    return datetime.now(timezone.utc)


class UserRepository:
    """CRUD operations for users."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, user_in: UserCreate) -> UserRead:
        """Create a user from validated input."""

        user = User(
            email=user_in.email,
            full_name=user_in.full_name,
            password_hash=user_in.password_hash,
            role=user_in.role,
            is_active=user_in.is_active,
        )
        self.session.add(user)
        self._commit_refresh(user)
        return UserRead.model_validate(user)

    def get_by_id(self, user_id: UUID) -> UserRead | None:
        """Return a user by primary key."""

        user = self.session.get(User, user_id)
        return UserRead.model_validate(user) if user else None

    def get_model_by_id(self, user_id: UUID) -> User | None:
        """Return a user ORM model by primary key."""

        return self.session.get(User, user_id)

    def get_by_email(self, email: str) -> UserRead | None:
        """Return a user by normalized email."""

        stmt = select(User).where(User.email == email.strip().lower())
        user = self.session.execute(stmt).scalar_one_or_none()
        return UserRead.model_validate(user) if user else None

    def get_model_by_email(self, email: str) -> User | None:
        """Return a user ORM model by normalized email."""

        stmt = select(User).where(User.email == email.strip().lower())
        return self.session.execute(stmt).scalar_one_or_none()

    def list_active(self) -> list[UserRead]:
        """List all active users."""

        stmt = select(User).where(User.is_active.is_(True)).order_by(User.created_at.desc())
        return [UserRead.model_validate(user) for user in self.session.scalars(stmt)]

    def list_all(self, include_inactive: bool = True) -> list[UserRead]:
        """List users ordered by most recently created first."""

        stmt = select(User).order_by(User.created_at.desc())
        if not include_inactive:
            stmt = stmt.where(User.is_active.is_(True))
        return [UserRead.model_validate(user) for user in self.session.scalars(stmt)]

    def count_users(self) -> int:
        """Return the total number of users."""

        stmt = select(func.count(User.id))
        return int(self.session.execute(stmt).scalar_one())

    def has_active_admin(self) -> bool:
        """Return whether at least one active admin exists."""

        stmt = select(User.id).where(User.is_active.is_(True), User.role == UserRole.ADMIN).limit(1)
        return self.session.execute(stmt).scalar_one_or_none() is not None

    def count_active_admins(self, exclude_user_id: UUID | None = None) -> int:
        """Return the number of active admin users."""

        stmt = select(func.count(User.id)).where(
            User.is_active.is_(True),
            User.role == UserRole.ADMIN,
        )
        if exclude_user_id is not None:
            stmt = stmt.where(User.id != exclude_user_id)
        return int(self.session.execute(stmt).scalar_one())

    def update_last_login(
        self, user_id: UUID, last_login_at: datetime | None = None
    ) -> UserRead | None:
        """Update the last-login timestamp for a user."""

        user = self.session.get(User, user_id)
        if user is None:
            return None

        user.last_login_at = last_login_at or utcnow()
        user.updated_at = utcnow()
        self._commit_refresh(user)
        return UserRead.model_validate(user)

    def update_managed_user(self, user_id: UUID, payload: UserUpdate) -> UserRead | None:
        """Apply admin-managed updates to an existing user."""

        user = self.session.get(User, user_id)
        if user is None:
            return None

        if payload.full_name is not None:
            user.full_name = payload.full_name
        if payload.role is not None:
            user.role = payload.role
        if payload.is_active is not None:
            user.is_active = payload.is_active
        user.updated_at = utcnow()
        self._commit_refresh(user)
        return UserRead.model_validate(user)

    def _commit_refresh(self, instance: User) -> None:
        try:
            self.session.commit()
        except IntegrityError:
            self.session.rollback()
            raise
        self.session.refresh(instance)


class AnalysisResultRepository:
    """CRUD operations for persisted analysis results."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create_from_snapshot(self, snapshot: AnalysisSnapshotCreate) -> AnalysisRead:
        """Persist a validated analysis snapshot."""

        entity = AnalysisResult(
            id=snapshot.id,
            source_filename=snapshot.source_filename or "",
            source_file_path=snapshot.source_file_path,
            input_sha256=snapshot.input_sha256,
            material_type=snapshot.material_type or "unknown",
            stress_type=snapshot.stress_type or "engineering",
            quality_score=snapshot.quality_score,
            quality_grade=snapshot.quality_grade,
            elastic_modulus_gpa=snapshot.elastic_modulus_gpa,
            yield_strength_mpa=snapshot.yield_strength_mpa,
            yield_lower_mpa=snapshot.yield_lower_mpa,
            ultimate_tensile_mpa=snapshot.ultimate_tensile_mpa,
            elongation_at_break_pct=snapshot.elongation_at_break_pct,
            uniform_elongation_pct=snapshot.uniform_elongation_pct,
            strain_hardening_n=snapshot.strain_hardening_n,
            strength_coefficient_k=snapshot.strength_coefficient_k,
            toughness_mj_m3=snapshot.toughness_mj_m3,
            analysis_payload=snapshot.analysis_payload,
            context_snapshot=snapshot.context_snapshot,
            engine_version=snapshot.engine_version,
            created_by_user_id=snapshot.created_by_user_id,
            created_at=snapshot.created_at,
        )
        self.session.add(entity)
        self._commit_refresh(entity)
        return AnalysisRead.model_validate(entity)

    def get_by_id(self, analysis_id: UUID, include_deleted: bool = False) -> AnalysisRead | None:
        """Return an analysis result by ID."""

        stmt = select(AnalysisResult).where(AnalysisResult.id == analysis_id)
        if not include_deleted:
            stmt = stmt.where(AnalysisResult.deleted_at.is_(None))
        entity = self.session.execute(stmt).scalar_one_or_none()
        return AnalysisRead.model_validate(entity) if entity else None

    def list_recent(
        self, limit: int | None = 10, include_deleted: bool = False
    ) -> list[AnalysisRead]:
        """List recent analysis results."""

        if not include_deleted:
            stmt = select(AnalysisResult).where(AnalysisResult.deleted_at.is_(None))
        else:
            stmt = select(AnalysisResult)
        stmt = stmt.order_by(AnalysisResult.created_at.desc())
        if limit is not None:
            stmt = stmt.limit(limit)
        return [AnalysisRead.model_validate(item) for item in self.session.scalars(stmt)]

    def list_by_user(
        self,
        user_id: UUID,
        limit: int = 100,
        include_deleted: bool = False,
    ) -> list[AnalysisRead]:
        """List analysis results created by a specific user."""

        stmt = (
            select(AnalysisResult)
            .where(AnalysisResult.created_by_user_id == user_id)
            .order_by(AnalysisResult.created_at.desc())
            .limit(limit)
        )
        if not include_deleted:
            stmt = stmt.where(AnalysisResult.deleted_at.is_(None))
        return [AnalysisRead.model_validate(item) for item in self.session.scalars(stmt)]

    def soft_delete(
        self,
        analysis_id: UUID,
        deleted_by_user_id: UUID | None = None,
        deleted_at: datetime | None = None,
    ) -> AnalysisRead | None:
        """Soft-delete an analysis result."""

        entity = self.session.get(AnalysisResult, analysis_id)
        if entity is None:
            return None

        entity.deleted_at = deleted_at or utcnow()
        entity.deleted_by_user_id = deleted_by_user_id
        self._commit_refresh(entity)
        return AnalysisRead.model_validate(entity)

    def _commit_refresh(self, instance: AnalysisResult) -> None:
        try:
            self.session.commit()
        except IntegrityError:
            self.session.rollback()
            raise
        self.session.refresh(instance)


class AuditLogRepository:
    """Append-only access to audit logs."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def append(self, event: AuditEventCreate) -> AuditLogRead:
        """Append a new audit log entry."""

        entity = AuditLog(
            id=event.id,
            occurred_at=event.occurred_at,
            actor_user_id=event.actor_user_id,
            action=event.action,
            entity_type=event.entity_type,
            entity_id=event.entity_id,
            request_id=event.request_id,
            ip_address=event.ip_address,
            user_agent=event.user_agent,
            status=event.status,
            before_snapshot=event.before_snapshot,
            after_snapshot=event.after_snapshot,
            event_meta=event.event_meta,
        )
        self.session.add(entity)
        self._commit_refresh(entity)
        return AuditLogRead.model_validate(entity)

    def get_by_id(self, audit_id: UUID) -> AuditLogRead | None:
        """Return an audit event by ID."""

        entity = self.session.get(AuditLog, audit_id)
        return AuditLogRead.model_validate(entity) if entity else None

    def list_for_entity(
        self,
        entity_type: str,
        entity_id: str,
        limit: int = 100,
    ) -> list[AuditLogRead]:
        """List recent audit events for a single entity."""

        stmt = (
            select(AuditLog)
            .where(AuditLog.entity_type == entity_type, AuditLog.entity_id == entity_id)
            .order_by(AuditLog.occurred_at.desc())
            .limit(limit)
        )
        return [AuditLogRead.model_validate(item) for item in self.session.scalars(stmt)]

    def list_recent(self, limit: int = 100) -> list[AuditLogRead]:
        """List recent audit events."""

        stmt = select(AuditLog).order_by(AuditLog.occurred_at.desc()).limit(limit)
        return [AuditLogRead.model_validate(item) for item in self.session.scalars(stmt)]

    def list_filtered(
        self,
        *,
        limit: int = 100,
        entity_type: str | None = None,
        entity_id: str | None = None,
        action: str | None = None,
        status: str | None = None,
        actor_user_id: UUID | None = None,
    ) -> list[AuditLogRead]:
        """List recent audit events with optional filters."""

        stmt = select(AuditLog)
        if entity_type is not None:
            stmt = stmt.where(AuditLog.entity_type == entity_type)
        if entity_id is not None:
            stmt = stmt.where(AuditLog.entity_id == entity_id)
        if action is not None:
            stmt = stmt.where(AuditLog.action == action)
        if status is not None:
            stmt = stmt.where(AuditLog.status == status)
        if actor_user_id is not None:
            stmt = stmt.where(AuditLog.actor_user_id == actor_user_id)

        stmt = stmt.order_by(AuditLog.occurred_at.desc()).limit(limit)
        return [AuditLogRead.model_validate(item) for item in self.session.scalars(stmt)]

    def _commit_refresh(self, instance: AuditLog) -> None:
        try:
            self.session.commit()
        except IntegrityError:
            self.session.rollback()
            raise
        self.session.refresh(instance)
