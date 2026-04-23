"""JWT security and password hashing helpers for CurveIntel."""

from __future__ import annotations

import logging
import secrets
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from uuid import UUID

from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.orm import Session

from src.curveintel.db.enums import UserRole
from src.curveintel.db.repository import UserRepository
from src.curveintel.db.schemas import UserCreate, UserRead


logger = logging.getLogger(__name__)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
_development_secret = secrets.token_urlsafe(48)


class AuthSettings(BaseSettings):
    """Authentication settings loaded from the environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    jwt_secret_key: str | None = Field(default=None, validation_alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", validation_alias="JWT_ALGORITHM")
    jwt_access_token_expire_minutes: int = Field(
        default=60,
        validation_alias="JWT_ACCESS_TOKEN_EXPIRE_MINUTES",
    )
    auth_token_cookie_name: str = Field(
        default="curveintel_access_token",
        validation_alias="AUTH_TOKEN_COOKIE_NAME",
    )
    auth_cookie_secure: bool = Field(default=False, validation_alias="AUTH_COOKIE_SECURE")
    curveintel_env: str = Field(default="development", validation_alias="CURVEINTEL_ENV")
    auth_bootstrap_admin_email: str = Field(
        default="admin@curveintel.local",
        validation_alias="AUTH_BOOTSTRAP_ADMIN_EMAIL",
    )
    auth_bootstrap_admin_full_name: str = Field(
        default="CurveIntel Admin",
        validation_alias="AUTH_BOOTSTRAP_ADMIN_FULL_NAME",
    )
    auth_bootstrap_admin_password: str | None = Field(
        default=None,
        validation_alias="AUTH_BOOTSTRAP_ADMIN_PASSWORD",
    )

    @property
    def signing_key(self) -> str:
        """Return the JWT signing key with safe development fallback behavior."""

        if self.jwt_secret_key:
            return self.jwt_secret_key

        environment = self.curveintel_env.strip().lower()
        if environment in {"production", "prod", "staging"}:
            raise RuntimeError("JWT_SECRET_KEY must be set in production-like environments.")

        logger.warning(
            "JWT_SECRET_KEY is not set. Using an ephemeral development key; tokens will be invalidated on restart."
        )
        return _development_secret


class TokenPayload(BaseModel):
    """Decoded JWT payload."""

    sub: UUID
    email: str
    role: UserRole
    exp: int
    iat: int


@lru_cache(maxsize=1)
def get_auth_settings() -> AuthSettings:
    """Return cached auth settings."""

    return AuthSettings()


def reset_auth_state() -> None:
    """Reset cached auth settings for tests."""

    get_auth_settings.cache_clear()


def get_password_hash(password: str) -> str:
    """Hash a plaintext password."""

    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against its hash."""

    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(user: UserRead) -> str:
    """Create a signed JWT for a user."""

    settings = get_auth_settings()
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=settings.jwt_access_token_expire_minutes)
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role.value,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    return jwt.encode(payload, settings.signing_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> TokenPayload:
    """Decode and validate a JWT."""

    settings = get_auth_settings()
    try:
        payload = jwt.decode(token, settings.signing_key, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise ValueError("Invalid or expired access token.") from exc
    return TokenPayload.model_validate(payload)


def ensure_default_admin(session: Session) -> UserRead | None:
    """Seed the default admin user when configured and absent."""

    repo = UserRepository(session)
    if repo.has_active_admin():
        return None

    settings = get_auth_settings()
    if not settings.auth_bootstrap_admin_password:
        logger.warning(
            "No active admin user exists and AUTH_BOOTSTRAP_ADMIN_PASSWORD is not set. "
            "Use /api/auth/register once to bootstrap the first admin."
        )
        return None

    created = repo.create(
        UserCreate(
            email=settings.auth_bootstrap_admin_email,
            full_name=settings.auth_bootstrap_admin_full_name,
            password_hash=get_password_hash(settings.auth_bootstrap_admin_password),
            role=UserRole.ADMIN,
        )
    )
    logger.info("Seeded default CurveIntel admin user: %s", created.email)
    return created
