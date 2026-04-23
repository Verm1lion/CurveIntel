"""Authentication API routes for CurveIntel."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from src.curveintel.auth.dependencies import get_current_active_user, get_optional_current_user
from src.curveintel.auth.schemas import (
    LoginRequest,
    MessageResponse,
    RegisterRequest,
    TokenResponse,
)
from src.curveintel.auth.security import (
    create_access_token,
    get_auth_settings,
    get_password_hash,
    verify_password,
)
from src.curveintel.db.database import get_db_session
from src.curveintel.db.enums import AuditAction, AuditEntityType, AuditStatus, UserRole
from src.curveintel.db.repository import UserRepository
from src.curveintel.db.schemas import UserCreate, UserRead
from src.curveintel.db.service import append_audit_event


router = APIRouter(prefix="/api/auth", tags=["auth"])


def _set_auth_cookie(response: Response, access_token: str) -> None:
    """Attach the auth cookie to a response."""

    settings = get_auth_settings()
    response.set_cookie(
        key=settings.auth_token_cookie_name,
        value=access_token,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite="lax",
        max_age=settings.jwt_access_token_expire_minutes * 60,
        path="/",
    )


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register_user(
    payload: RegisterRequest,
    request: Request,
    db: Session = Depends(get_db_session),
    current_user: UserRead | None = Depends(get_optional_current_user),
) -> UserRead:
    """Register a new user with bootstrap and admin-controlled flows."""

    repo = UserRepository(db)
    existing_users = repo.count_users()

    if existing_users == 0:
        assigned_role = UserRole.ADMIN
    else:
        if current_user is None or current_user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins can register new users after bootstrap.",
            )
        assigned_role = payload.role or UserRole.VIEWER

    if (
        assigned_role == UserRole.ADMIN
        and existing_users > 0
        and (current_user is None or current_user.role != UserRole.ADMIN)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can create admin users."
        )

    existing = repo.get_by_email(payload.email)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="A user with this email already exists."
        )

    created = repo.create(
        UserCreate(
            email=payload.email,
            full_name=payload.full_name,
            password_hash=get_password_hash(payload.password),
            role=assigned_role,
            is_active=True,
        )
    )
    append_audit_event(
        db,
        request,
        action=AuditAction.REGISTER,
        entity_type=AuditEntityType.USER,
        entity_id=str(created.id),
        actor_user_id=current_user.id if current_user is not None else created.id,
        after_snapshot=created.model_dump(mode="json"),
        event_meta={"registered_role": created.role.value, "bootstrap": existing_users == 0},
    )
    return created


@router.post("/login", response_model=TokenResponse)
def login_user(
    payload: LoginRequest,
    response: Response,
    request: Request,
    db: Session = Depends(get_db_session),
) -> TokenResponse:
    """Authenticate a user and issue a bearer token."""

    repo = UserRepository(db)
    user_model = repo.get_model_by_email(payload.email)
    if user_model is None or not verify_password(payload.password, user_model.password_hash):
        append_audit_event(
            db,
            request,
            action=AuditAction.LOGIN,
            entity_type=AuditEntityType.USER,
            entity_id=payload.email.strip().lower(),
            status=AuditStatus.FAILURE,
            event_meta={"reason": "invalid_credentials"},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password."
        )

    if not user_model.is_active:
        append_audit_event(
            db,
            request,
            action=AuditAction.LOGIN,
            entity_type=AuditEntityType.USER,
            entity_id=str(user_model.id),
            actor_user_id=user_model.id,
            status=AuditStatus.FAILURE,
            event_meta={"reason": "inactive_user"},
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Inactive users cannot sign in."
        )

    user = repo.update_last_login(user_model.id)
    assert user is not None
    access_token = create_access_token(user)
    _set_auth_cookie(response, access_token)
    append_audit_event(
        db,
        request,
        action=AuditAction.LOGIN,
        entity_type=AuditEntityType.USER,
        entity_id=str(user.id),
        actor_user_id=user.id,
        after_snapshot=user.model_dump(mode="json"),
    )
    return TokenResponse(
        access_token=access_token,
        expires_in=get_auth_settings().jwt_access_token_expire_minutes * 60,
        user=user,
    )


@router.post("/logout", response_model=MessageResponse)
def logout_user(
    response: Response,
    request: Request,
    db: Session = Depends(get_db_session),
    current_user: UserRead | None = Depends(get_optional_current_user),
) -> MessageResponse:
    """Clear the auth cookie."""

    settings = get_auth_settings()
    response.delete_cookie(settings.auth_token_cookie_name, path="/")
    if current_user is not None:
        append_audit_event(
            db,
            request,
            action=AuditAction.LOGOUT,
            entity_type=AuditEntityType.USER,
            entity_id=str(current_user.id),
            actor_user_id=current_user.id,
        )
    return MessageResponse(detail="Signed out.")


@router.get("/me", response_model=UserRead)
def get_me(current_user: UserRead = Depends(get_current_active_user)) -> UserRead:
    """Return the current authenticated user."""

    return current_user
