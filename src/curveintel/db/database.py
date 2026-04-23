"""SQLAlchemy engine and session management for CurveIntel."""

from __future__ import annotations

from functools import lru_cache
from typing import Generator

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class DatabaseSettings(BaseSettings):
    """Database connection settings loaded from the environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    database_url: str = Field(
        default="sqlite:///./curveintel.db",
        validation_alias="DATABASE_URL",
    )
    db_echo: bool = Field(default=False, validation_alias="DB_ECHO")
    db_pool_pre_ping: bool = Field(default=True, validation_alias="DB_POOL_PRE_PING")

    @property
    def sqlalchemy_url(self) -> URL:
        """Return the parsed SQLAlchemy URL."""

        return make_url(self.database_url)

    @property
    def is_sqlite(self) -> bool:
        """Return whether the configured backend is SQLite."""

        return self.sqlalchemy_url.get_backend_name() == "sqlite"


@lru_cache(maxsize=1)
def get_database_settings() -> DatabaseSettings:
    """Return cached database settings."""

    return DatabaseSettings()


class Base(DeclarativeBase):
    """Declarative base for ORM models."""


engine: Engine | None = None
SessionLocal = sessionmaker(autoflush=False, autocommit=False, expire_on_commit=False)


def get_engine() -> Engine:
    """Return the configured SQLAlchemy engine."""

    global engine
    if engine is None:
        settings = get_database_settings()
        connect_args: dict[str, object] = {}
        if settings.is_sqlite:
            connect_args["check_same_thread"] = False

        engine = create_engine(
            settings.database_url,
            echo=settings.db_echo,
            pool_pre_ping=settings.db_pool_pre_ping,
            future=True,
            connect_args=connect_args,
        )
        SessionLocal.configure(bind=engine)

    return engine


def get_db_session() -> Generator[Session, None, None]:
    """Yield a database session for FastAPI dependencies."""

    get_engine()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def reset_database_state() -> None:
    """Reset cached settings and engine state for tests."""

    global engine
    if engine is not None:
        engine.dispose()
        engine = None

    SessionLocal.configure(bind=None)
    get_database_settings.cache_clear()
