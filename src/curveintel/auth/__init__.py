"""Authentication package exports for CurveIntel."""

from src.curveintel.auth.dependencies import (
    get_current_active_user,
    get_current_user,
    get_optional_current_user,
    require_roles,
)
from src.curveintel.auth.security import (
    AuthSettings,
    TokenPayload,
    create_access_token,
    decode_access_token,
    ensure_default_admin,
    get_auth_settings,
    get_password_hash,
    reset_auth_state,
    verify_password,
)

__all__ = [
    "AuthSettings",
    "TokenPayload",
    "create_access_token",
    "decode_access_token",
    "ensure_default_admin",
    "get_auth_settings",
    "get_current_active_user",
    "get_current_user",
    "get_optional_current_user",
    "get_password_hash",
    "require_roles",
    "reset_auth_state",
    "verify_password",
]
