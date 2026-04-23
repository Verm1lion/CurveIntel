"""Pydantic DTOs for CurveIntel database boundaries."""

from __future__ import annotations

import hashlib
import ipaddress
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Annotated
from uuid import UUID, uuid4

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from src import __version__ as CURVEINTEL_VERSION
from src.curveintel.db.enums import AuditAction, AuditEntityType, AuditStatus, UserRole


EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
NON_EMPTY_255 = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)
]


def utcnow() -> datetime:
    """Return a timezone-aware UTC timestamp."""

    return datetime.now(timezone.utc)


def _ensure_json_serializable(value: dict[str, Any], field_name: str) -> dict[str, Any]:
    """Validate that a payload is JSON serializable."""

    try:
        json.dumps(value)
    except TypeError as exc:
        raise ValueError(f"{field_name} must be JSON serializable.") from exc
    return value


class UserCreate(BaseModel):
    """Validated input for creating a user record."""

    email: str
    full_name: NON_EMPTY_255
    password_hash: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=20, max_length=255)
    ]
    role: UserRole = UserRole.VIEWER
    is_active: bool = True

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        """Normalize and validate an email address."""

        normalized = value.strip().lower()
        if len(normalized) > 320 or not EMAIL_REGEX.match(normalized):
            raise ValueError("email must be a valid email address.")
        return normalized


class UserRead(BaseModel):
    """Safe user DTO for read operations."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime
    last_login_at: datetime | None = None


class AnalysisSnapshotCreate(BaseModel):
    """Validated snapshot payload used to persist an analysis result."""

    id: UUID = Field(default_factory=uuid4)
    source_filename: str | None = None
    source_file_path: str | None = None
    input_sha256: str | None = None
    material_type: str | None = None
    stress_type: str | None = None
    quality_score: float | None = None
    quality_grade: str | None = None
    elastic_modulus_gpa: float | None = None
    yield_strength_mpa: float | None = None
    yield_lower_mpa: float | None = None
    ultimate_tensile_mpa: float | None = None
    elongation_at_break_pct: float | None = None
    uniform_elongation_pct: float | None = None
    strain_hardening_n: float | None = None
    strength_coefficient_k: float | None = None
    toughness_mj_m3: float | None = None
    analysis_payload: dict[str, Any]
    context_snapshot: dict[str, Any]
    engine_version: str | None = CURVEINTEL_VERSION
    created_by_user_id: UUID | None = None
    created_at: datetime = Field(default_factory=utcnow)

    @field_validator("analysis_payload")
    @classmethod
    def validate_analysis_payload(cls, value: dict[str, Any]) -> dict[str, Any]:
        """Ensure the analysis payload is serializable."""

        return _ensure_json_serializable(value, "analysis_payload")

    @field_validator("context_snapshot")
    @classmethod
    def validate_context_snapshot(cls, value: dict[str, Any]) -> dict[str, Any]:
        """Ensure the context snapshot is serializable."""

        return _ensure_json_serializable(value, "context_snapshot")

    @field_validator("input_sha256")
    @classmethod
    def validate_sha256(cls, value: str | None) -> str | None:
        """Validate optional SHA-256 input digests."""

        if value is None:
            return value
        normalized = value.strip().lower()
        if not re.fullmatch(r"[a-f0-9]{64}", normalized):
            raise ValueError("input_sha256 must be a 64-character hexadecimal digest.")
        return normalized

    @model_validator(mode="after")
    def derive_indexed_fields(self) -> "AnalysisSnapshotCreate":
        """Populate indexed columns from the canonical JSON payload."""

        payload = self.analysis_payload
        context_metadata = self.context_snapshot.get("metadata", {})
        props = payload.get("properties", {})
        quality = payload.get("quality", {})

        if not self.source_filename:
            self.source_filename = str(
                payload.get("filename")
                or context_metadata.get("source_file")
                or context_metadata.get("source_filename")
                or ""
            ).strip()
        if not self.source_filename:
            raise ValueError("source_filename is required.")

        if self.source_file_path is not None:
            self.source_file_path = str(Path(self.source_file_path))

        if self.input_sha256 is None and self.source_file_path:
            source_path = Path(self.source_file_path)
            if source_path.exists() and source_path.is_file():
                self.input_sha256 = hashlib.sha256(source_path.read_bytes()).hexdigest()

        self.material_type = self.material_type or str(
            payload.get("material_type") or context_metadata.get("material_type") or "unknown"
        )
        self.stress_type = self.stress_type or str(
            payload.get("stress_type") or context_metadata.get("stress_type") or "engineering"
        )
        self.quality_score = (
            self.quality_score if self.quality_score is not None else quality.get("score")
        )
        self.quality_grade = self.quality_grade or quality.get("grade")
        self.elastic_modulus_gpa = (
            self.elastic_modulus_gpa
            if self.elastic_modulus_gpa is not None
            else props.get("elastic_modulus_gpa")
        )
        self.yield_strength_mpa = (
            self.yield_strength_mpa
            if self.yield_strength_mpa is not None
            else props.get("yield_strength_mpa")
        )
        self.yield_lower_mpa = (
            self.yield_lower_mpa
            if self.yield_lower_mpa is not None
            else props.get("yield_lower_mpa")
        )
        self.ultimate_tensile_mpa = (
            self.ultimate_tensile_mpa
            if self.ultimate_tensile_mpa is not None
            else props.get("ultimate_tensile_mpa")
        )
        self.elongation_at_break_pct = (
            self.elongation_at_break_pct
            if self.elongation_at_break_pct is not None
            else props.get("elongation_at_break_pct")
        )
        self.uniform_elongation_pct = (
            self.uniform_elongation_pct
            if self.uniform_elongation_pct is not None
            else props.get("uniform_elongation_pct")
        )
        self.strain_hardening_n = (
            self.strain_hardening_n
            if self.strain_hardening_n is not None
            else props.get("strain_hardening_n")
        )
        self.strength_coefficient_k = (
            self.strength_coefficient_k
            if self.strength_coefficient_k is not None
            else props.get("strength_coefficient_k")
        )
        self.toughness_mj_m3 = (
            self.toughness_mj_m3
            if self.toughness_mj_m3 is not None
            else props.get("toughness_mj_m3")
        )

        return self


class AnalysisRead(BaseModel):
    """Read DTO for persisted analysis results."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_filename: str
    source_file_path: str | None = None
    input_sha256: str | None = None
    material_type: str
    stress_type: str
    quality_score: float | None = None
    quality_grade: str | None = None
    elastic_modulus_gpa: float | None = None
    yield_strength_mpa: float | None = None
    yield_lower_mpa: float | None = None
    ultimate_tensile_mpa: float | None = None
    elongation_at_break_pct: float | None = None
    uniform_elongation_pct: float | None = None
    strain_hardening_n: float | None = None
    strength_coefficient_k: float | None = None
    toughness_mj_m3: float | None = None
    analysis_payload: dict[str, Any]
    context_snapshot: dict[str, Any]
    engine_version: str | None = None
    created_by_user_id: UUID | None = None
    created_at: datetime
    deleted_at: datetime | None = None
    deleted_by_user_id: UUID | None = None


class AuditEventCreate(BaseModel):
    """Validated input for appending an audit event."""

    id: UUID = Field(default_factory=uuid4)
    occurred_at: datetime = Field(default_factory=utcnow)
    actor_user_id: UUID | None = None
    action: AuditAction
    entity_type: AuditEntityType
    entity_id: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=128)
    ]
    request_id: Annotated[str | None, StringConstraints(strip_whitespace=True, max_length=128)] = (
        None
    )
    ip_address: str | None = None
    user_agent: Annotated[str | None, StringConstraints(strip_whitespace=True, max_length=2048)] = (
        None
    )
    status: AuditStatus = AuditStatus.SUCCESS
    before_snapshot: dict[str, Any] | None = None
    after_snapshot: dict[str, Any] | None = None
    event_meta: dict[str, Any] = Field(default_factory=dict)

    @field_validator("ip_address")
    @classmethod
    def validate_ip_address(cls, value: str | None) -> str | None:
        """Validate optional IP addresses."""

        if value is None:
            return value
        normalized = value.strip()
        ipaddress.ip_address(normalized)
        return normalized

    @field_validator("before_snapshot", "after_snapshot", "event_meta")
    @classmethod
    def validate_json_payloads(
        cls, value: dict[str, Any] | None, info: Any
    ) -> dict[str, Any] | None:
        """Ensure JSON snapshots are serializable."""

        if value is None:
            return value
        return _ensure_json_serializable(value, str(info.field_name))


class AuditLogRead(BaseModel):
    """Read DTO for audit trail entries."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    occurred_at: datetime
    actor_user_id: UUID | None = None
    action: AuditAction
    entity_type: AuditEntityType
    entity_id: str
    request_id: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    status: AuditStatus
    before_snapshot: dict[str, Any] | None = None
    after_snapshot: dict[str, Any] | None = None
    event_meta: dict[str, Any]
