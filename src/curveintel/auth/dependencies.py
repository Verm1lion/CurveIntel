"""FastAPI auth dependencies and RBAC guards."""

from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from src.curveintel.auth.security import decode_access_token, get_auth_settings
from src.curveintel.db.database import get_db_session
from src.curveintel.db.enums import UserRole
from src.curveintel.db.repository import UserRepository
from src.curveintel.db.schemas import UserRead


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def _get_request_token(request: Request, bearer_token: str | None) -> str | None:
    """Extract a token from the Authorization header or auth cookie."""

    if bearer_token:
        return bearer_token

    cookie_name = get_auth_settings().auth_token_cookie_name
    cookie_token = request.cookies.get(cookie_name)
    if cookie_token:
        return cookie_token
    return None


def get_optional_current_user(
    request: Request,
    db: Session = Depends(get_db_session),
    bearer_token: str | None = Depends(oauth2_scheme),
) -> UserRead | None:
    """Return the authenticated user when present."""

    token = _get_request_token(request, bearer_token)
    if token is None:
        return None

    try:
        payload = decode_access_token(token)
    except ValueError:
        return None

    repo = UserRepository(db)
    user = repo.get_by_id(payload.sub)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user no longer exists.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def get_current_user(user: UserRead | None = Depends(get_optional_current_user)) -> UserRead:
    """Require an authenticated user."""

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def get_current_active_user(user: UserRead = Depends(get_current_user)) -> UserRead:
    """Require an active user."""

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive users cannot access this resource.",
        )
    return user


def require_roles(*roles: UserRole) -> Callable[[UserRead], UserRead]:
    """Require one of the provided roles."""

    allowed_roles = set(roles)

    def dependency(user: UserRead = Depends(get_current_active_user)) -> UserRead:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role for this action."
            )
        return user

    return dependency
