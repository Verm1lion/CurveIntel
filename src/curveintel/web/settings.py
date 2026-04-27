"""Environment-backed web settings for CurveIntel."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class WebSettings(BaseSettings):
    """Runtime settings for the FastAPI web layer."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    curveintel_env: str = Field(default="development", validation_alias="CURVEINTEL_ENV")
    cors_allow_origins_raw: str = Field(
        default="http://localhost:8000,http://127.0.0.1:8000,http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173",
        validation_alias="CORS_ALLOW_ORIGINS",
    )
    cors_allow_methods_raw: str = Field(
        default="GET,POST,PUT,PATCH,DELETE,OPTIONS",
        validation_alias="CORS_ALLOW_METHODS",
    )
    cors_allow_headers_raw: str = Field(
        default="Authorization,Content-Type,X-Request-ID",
        validation_alias="CORS_ALLOW_HEADERS",
    )
    cors_allow_credentials: bool = Field(default=True, validation_alias="CORS_ALLOW_CREDENTIALS")

    @staticmethod
    def _parse_csv(value: str) -> list[str]:
        """Parse a comma-delimited config string into a normalized list."""

        return [item.strip() for item in value.split(",") if item.strip()]

    @property
    def cors_allow_origins(self) -> list[str]:
        """Return the configured CORS allowlist."""

        return self._parse_csv(self.cors_allow_origins_raw)

    @property
    def cors_allow_methods(self) -> list[str]:
        """Return the configured CORS methods."""

        return self._parse_csv(self.cors_allow_methods_raw)

    @property
    def cors_allow_headers(self) -> list[str]:
        """Return the configured CORS headers."""

        return self._parse_csv(self.cors_allow_headers_raw)

    @property
    def expose_internal_error_details(self) -> bool:
        """Return whether internal exception details may be surfaced in API responses."""

        return self.curveintel_env.strip().lower() in {
            "development",
            "dev",
            "local",
            "test",
            "testing",
        }

    @model_validator(mode="after")
    def validate_cors_config(self) -> "WebSettings":
        """Reject insecure wildcard+credential combinations for cookie-based auth."""

        if "*" in self.cors_allow_origins and self.cors_allow_credentials:
            raise ValueError(
                "CORS_ALLOW_ORIGINS cannot include '*' when CORS_ALLOW_CREDENTIALS is enabled."
            )
        return self


@lru_cache(maxsize=1)
def get_web_settings() -> WebSettings:
    """Return cached web settings."""

    return WebSettings()


def reset_web_settings() -> None:
    """Reset cached web settings for tests."""

    get_web_settings.cache_clear()
