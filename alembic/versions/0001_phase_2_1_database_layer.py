"""Create Phase 2.1 persistence tables."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0001_phase_2_1"
down_revision = None
branch_labels = None
depends_on = None


def _json_type(dialect_name: str) -> sa.TypeEngine:
    """Return the dialect-specific JSON type."""

    if dialect_name == "postgresql":
        return postgresql.JSONB(astext_type=sa.Text())
    return sa.JSON()


def _enum_type(dialect_name: str, *values: str, name: str) -> sa.TypeEngine:
    """Return a reusable enum type for the active dialect."""

    if dialect_name == "postgresql":
        # PostgreSQL enum types are created explicitly below with checkfirst=True.
        # Prevent table creation from attempting to create the same named type again.
        return postgresql.ENUM(*values, name=name, create_type=False)
    return sa.Enum(*values, name=name)


def upgrade() -> None:
    bind = op.get_bind()
    dialect_name = bind.dialect.name
    json_type = _json_type(dialect_name)

    user_role = _enum_type(dialect_name, "admin", "analyst", "viewer", name="user_role")
    audit_action = _enum_type(
        dialect_name,
        "create",
        "update",
        "delete",
        "read",
        "download",
        "login",
        "logout",
        "register",
        "seed",
        name="audit_action",
    )
    audit_entity_type = _enum_type(
        dialect_name,
        "user",
        "analysis_result",
        "audit_log",
        "report",
        "system",
        name="audit_entity_type",
    )
    audit_status = _enum_type(dialect_name, "success", "failure", name="audit_status")

    if dialect_name == "postgresql":
        user_role.create(bind, checkfirst=True)
        audit_action.create(bind, checkfirst=True)
        audit_entity_type.create(bind, checkfirst=True)
        audit_status.create(bind, checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", user_role, nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "analysis_results",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("source_filename", sa.String(length=255), nullable=False),
        sa.Column("source_file_path", sa.Text(), nullable=True),
        sa.Column("input_sha256", sa.String(length=64), nullable=True),
        sa.Column("material_type", sa.String(length=64), nullable=False),
        sa.Column("stress_type", sa.String(length=32), nullable=False),
        sa.Column("quality_score", sa.Float(), nullable=True),
        sa.Column("quality_grade", sa.String(length=32), nullable=True),
        sa.Column("elastic_modulus_gpa", sa.Float(), nullable=True),
        sa.Column("yield_strength_mpa", sa.Float(), nullable=True),
        sa.Column("yield_lower_mpa", sa.Float(), nullable=True),
        sa.Column("ultimate_tensile_mpa", sa.Float(), nullable=True),
        sa.Column("elongation_at_break_pct", sa.Float(), nullable=True),
        sa.Column("uniform_elongation_pct", sa.Float(), nullable=True),
        sa.Column("strain_hardening_n", sa.Float(), nullable=True),
        sa.Column("strength_coefficient_k", sa.Float(), nullable=True),
        sa.Column("toughness_mj_m3", sa.Float(), nullable=True),
        sa.Column("analysis_payload", json_type, nullable=False),
        sa.Column("context_snapshot", json_type, nullable=False),
        sa.Column("engine_version", sa.String(length=32), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by_user_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["deleted_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_analysis_results_created_at", "analysis_results", ["created_at"], unique=False
    )
    op.create_index(
        "ix_analysis_results_created_by_user_id",
        "analysis_results",
        ["created_by_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_analysis_results_deleted_at", "analysis_results", ["deleted_at"], unique=False
    )
    op.create_index(
        "ix_analysis_results_deleted_by_user_id",
        "analysis_results",
        ["deleted_by_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_analysis_results_input_sha256", "analysis_results", ["input_sha256"], unique=False
    )
    op.create_index(
        "ix_analysis_results_source_filename", "analysis_results", ["source_filename"], unique=False
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("action", audit_action, nullable=False),
        sa.Column("entity_type", audit_entity_type, nullable=False),
        sa.Column("entity_id", sa.String(length=128), nullable=False),
        sa.Column("request_id", sa.String(length=128), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("status", audit_status, nullable=False),
        sa.Column("before_snapshot", json_type, nullable=True),
        sa.Column("after_snapshot", json_type, nullable=True),
        sa.Column("event_meta", json_type, nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_logs_actor_user_id", "audit_logs", ["actor_user_id"], unique=False)
    op.create_index("ix_audit_logs_entity_type", "audit_logs", ["entity_type"], unique=False)
    op.create_index("ix_audit_logs_occurred_at", "audit_logs", ["occurred_at"], unique=False)
    op.create_index("ix_audit_logs_request_id", "audit_logs", ["request_id"], unique=False)
    op.create_index(
        "ix_audit_logs_entity_lookup",
        "audit_logs",
        ["entity_type", "entity_id"],
        unique=False,
    )


def downgrade() -> None:
    bind = op.get_bind()
    dialect_name = bind.dialect.name

    op.drop_index("ix_audit_logs_entity_lookup", table_name="audit_logs")
    op.drop_index("ix_audit_logs_request_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_occurred_at", table_name="audit_logs")
    op.drop_index("ix_audit_logs_entity_type", table_name="audit_logs")
    op.drop_index("ix_audit_logs_actor_user_id", table_name="audit_logs")
    op.drop_table("audit_logs")

    op.drop_index("ix_analysis_results_source_filename", table_name="analysis_results")
    op.drop_index("ix_analysis_results_input_sha256", table_name="analysis_results")
    op.drop_index("ix_analysis_results_deleted_by_user_id", table_name="analysis_results")
    op.drop_index("ix_analysis_results_deleted_at", table_name="analysis_results")
    op.drop_index("ix_analysis_results_created_by_user_id", table_name="analysis_results")
    op.drop_index("ix_analysis_results_created_at", table_name="analysis_results")
    op.drop_table("analysis_results")

    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")

    if dialect_name == "postgresql":
        sa.Enum(name="audit_status").drop(bind, checkfirst=True)
        sa.Enum(name="audit_entity_type").drop(bind, checkfirst=True)
        sa.Enum(name="audit_action").drop(bind, checkfirst=True)
        sa.Enum(name="user_role").drop(bind, checkfirst=True)
