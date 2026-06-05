from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import DBSession
from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)
from app.db.models import AuditEvent, RefreshToken, Tenant, User, UserRole, UserStatus
from app.schemas.auth import LoginRequest, RefreshRequest, RegisterRequest, TokenResponse, UserProfile

router = APIRouter(prefix="/auth", tags=["auth"])


def token_hash(token: str) -> str:
    # Lightweight deterministic hash for refresh-token persistence.
    import hashlib

    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@router.post("/register", response_model=UserProfile, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: DBSession) -> User:
    tenant = db.scalar(select(Tenant).where(Tenant.id == payload.tenant_id))
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found.")

    existing = db.scalar(
        select(User).where(User.tenant_id == payload.tenant_id, User.email == payload.email.lower())
    )
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered for this tenant.")

    role = payload.role.lower()
    valid_roles = {r.value for r in UserRole}
    if role not in valid_roles:
        role = UserRole.MANAGER.value

    user = User(
        tenant_id=payload.tenant_id,
        email=payload.email.lower(),
        full_name=payload.full_name,
        role=role,
        password_hash=hash_password(payload.password),
        status=UserStatus.ACTIVE.value,
    )
    db.add(user)
    db.flush()
    db.add(
        AuditEvent(
            tenant_id=user.tenant_id,
            actor_type="user",
            actor_id=user.id,
            action="auth.register",
            target_type="user",
            target_id=user.id,
            metadata={"role": role},
        )
    )
    db.commit()
    return user


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: DBSession) -> TokenResponse:
    user = db.scalar(
        select(User).where(
            User.tenant_id == payload.tenant_id,
            User.email == payload.email.lower(),
            User.status == UserStatus.ACTIVE.value,
        )
    )
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials.")

    access_token = create_access_token({"sub": user.id, "tenant_id": user.tenant_id, "role": user.role})
    refresh_token = create_refresh_token({"sub": user.id, "tenant_id": user.tenant_id, "role": user.role})

    settings = get_settings()
    refresh_exp = datetime.now(timezone.utc) + timedelta(days=settings.jwt_refresh_days)
    db.add(
        RefreshToken(
            tenant_id=user.tenant_id,
            user_id=user.id,
            token_hash=token_hash(refresh_token),
            expires_at=refresh_exp,
        )
    )
    user.last_login_at = datetime.now(timezone.utc)
    db.add(
        AuditEvent(
            tenant_id=user.tenant_id,
            actor_type="user",
            actor_id=user.id,
            action="auth.login",
            target_type="user",
            target_id=user.id,
            metadata={},
        )
    )
    db.commit()
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.jwt_access_minutes * 60,
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, db: DBSession) -> TokenResponse:
    from app.core.security import decode_token

    token_data = decode_token(payload.refresh_token)
    if token_data.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type.")

    user_id = token_data.get("sub")
    tenant_id = token_data.get("tenant_id")
    if not user_id or not tenant_id:
        raise HTTPException(status_code=401, detail="Invalid token payload.")

    stored = db.scalar(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash(payload.refresh_token),
            RefreshToken.tenant_id == tenant_id,
            RefreshToken.user_id == user_id,
            RefreshToken.revoked_at.is_(None),
        )
    )
    if not stored or stored.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Refresh token expired or revoked.")

    user = db.scalar(select(User).where(User.id == user_id, User.tenant_id == tenant_id))
    if not user or user.status != UserStatus.ACTIVE.value:
        raise HTTPException(status_code=401, detail="User inactive.")

    access_token = create_access_token({"sub": user.id, "tenant_id": user.tenant_id, "role": user.role})
    refresh_token = create_refresh_token({"sub": user.id, "tenant_id": user.tenant_id, "role": user.role})

    settings = get_settings()
    stored.revoked_at = datetime.now(timezone.utc)
    db.add(
        RefreshToken(
            tenant_id=user.tenant_id,
            user_id=user.id,
            token_hash=token_hash(refresh_token),
            expires_at=datetime.now(timezone.utc) + timedelta(days=settings.jwt_refresh_days),
        )
    )
    db.add(
        AuditEvent(
            tenant_id=user.tenant_id,
            actor_type="user",
            actor_id=user.id,
            action="auth.refresh",
            target_type="user",
            target_id=user.id,
            metadata={},
        )
    )
    db.commit()
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.jwt_access_minutes * 60,
    )
