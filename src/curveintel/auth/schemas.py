"""Pydantic schemas for auth and RBAC flows."""

from __future__ import annotations

import re
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints, field_validator

from src.curveintel.db.enums import UserRole
from src.curveintel.db.schemas import UserRead


PASSWORD_PATTERN = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).+$")


class LoginRequest(BaseModel):
    """Validated login payload."""

    email: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=320)]
    password: Annotated[str, StringConstraints(min_length=1, max_length=128)]


class RegisterRequest(BaseModel):
    """Validated registration payload."""

    email: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=320)]
    full_name: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)
    ]
    password: Annotated[str, StringConstraints(min_length=12, max_length=128)]
    role: UserRole | None = None

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        """Enforce a basic password policy."""

        if not PASSWORD_PATTERN.match(value):
            raise ValueError("password must include uppercase, lowercase, and numeric characters.")
        return value


class TokenResponse(BaseModel):
    """Bearer token response model."""

    model_config = ConfigDict(from_attributes=True)

    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserRead


class MessageResponse(BaseModel):
    """Simple message response."""

    detail: str
