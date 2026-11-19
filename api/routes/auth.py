"""GESTIA API - Auth Routes."""

from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from gestia_core.config import get_settings
from gestia_core.database import get_db
from gestia_core.models import Usuario, RefreshToken
from gestia_core.schemas import TokenResponse, RefreshTokenRequest, UsuarioResponse, UsuarioCreate
from gestia_core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user,
    hash_password,
    verify_password,
)

router = APIRouter()
settings = get_settings()


@router.post("/login", response_model=TokenResponse, summary="Login with email/password")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """Authenticate user and return access + refresh tokens."""
    result = await db.execute(select(Usuario).where(Usuario.email == form_data.username))
    user = result.scalar_one_or_none()

    if not user or not user.activo or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Update last access
    from datetime import datetime, timezone
    user.ultimo_acceso = datetime.now(timezone.utc)

    # Create tokens
    access_token = create_access_token(user)
    refresh_token = create_refresh_token(user)

    # Store refresh token hash
    token_data = decode_token(refresh_token)
    if token_data:
        rt = RefreshToken(
            token_hash=hash_password(token_data.jti),
            usuario_id=user.id,
            expira_en=datetime.fromtimestamp(token_data.exp, tz=timezone.utc),
        )
        db.add(rt)

    await db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/refresh", response_model=TokenResponse, summary="Refresh access token")
async def refresh_token(
    request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
):
    """Exchange refresh token for new access token."""
    token_data = decode_token(request.refresh_token)
    if not token_data or token_data.type != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    # Verify not revoked
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == hash_password(token_data.jti))
    )
    rt = result.scalar_one_or_none()
    if not rt or rt.revocado:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token revoked",
        )

    # Get user
    result = await db.execute(select(Usuario).where(Usuario.id == token_data.sub))
    user = result.scalar_one_or_none()
    if not user or not user.activo:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    # Revoke old refresh token
    rt.revocado = True
    from datetime import datetime, timezone
    rt.revocado_en = datetime.now(timezone.utc)

    # Create new tokens
    new_access = create_access_token(user)
    new_refresh = create_refresh_token(user)

    # Store new refresh token
    new_token_data = decode_token(new_refresh)
    if new_token_data:
        new_rt = RefreshToken(
            token_hash=hash_password(new_token_data.jti),
            usuario_id=user.id,
            expira_en=datetime.fromtimestamp(new_token_data.exp, tz=timezone.utc),
        )
        db.add(new_rt)

    await db.commit()

    return TokenResponse(
        access_token=new_access,
        refresh_token=new_refresh,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/logout", summary="Logout (revoke refresh token)")
async def logout(
    request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
):
    """Revoke refresh token."""
    token_data = decode_token(request.refresh_token)
    if not token_data or token_data.type != "refresh":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid token",
        )

    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == hash_password(token_data.jti))
    )
    rt = result.scalar_one_or_none()
    if rt:
        rt.revocado = True
        from datetime import datetime, timezone
        rt.revocado_en = datetime.now(timezone.utc)
        await db.commit()

    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UsuarioResponse, summary="Get current user profile")
async def get_me(user: Usuario = Depends(get_current_user)):
    """Get current authenticated user profile."""
    return user


@router.post("/register", response_model=UsuarioResponse, status_code=status.HTTP_201_CREATED, summary="Register new user (admin only)")
async def register(
    user_data: UsuarioCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Register new user (requires admin role)."""
    # Check admin role
    from gestia_core.models import RolSistema
    if RolSistema.ADMIN_ASESORIA not in current_user.roles and RolSistema.SUPERADMIN not in current_user.roles:
        raise HTTPException(status_code=403, detail="Admin role required")

    # Check email unique
    result = await db.execute(select(Usuario).where(Usuario.email == user_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    # Create user
    user = Usuario(
        email=user_data.email,
        password_hash=hash_password(user_data.password),
        nombre=user_data.nombre,
        apellidos=user_data.apellidos,
        telefono=user_data.telefono,
        tipo=user_data.tipo,
        roles=user_data.roles,
        tenant_id=current_user.tenant_id,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return user