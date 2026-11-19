"""GESTIA Security - Auth, JWT, RBAC, Password hashing."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional
from uuid import uuid4

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from gestia_core.config import get_settings
from gestia_core.database import get_db
from gestia_core.models import Usuario, RefreshToken
from gestia_core.models.enums import RolSistema
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


settings = get_settings()

# --------------------------------------------
# PASSWORD HASHING
# --------------------------------------------

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


# --------------------------------------------
# JWT TOKENS
# --------------------------------------------

class TokenData(BaseModel):
    sub: str  # user_id
    email: str
    tenant_id: str
    roles: list[str]
    tipo: str
    exp: int
    iat: int
    jti: str  # token ID para revocación


def create_access_token(
    user: Usuario,
    expires_delta: timedelta | None = None,
) -> str:
    """Create JWT access token."""
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    jti = str(uuid4())
    to_encode = {
        "sub": str(user.id),
        "email": user.email,
        "tenant_id": str(user.tenant_id),
        "roles": user.roles,
        "tipo": user.tipo,
        "exp": int(expire.timestamp()),
        "iat": int(datetime.now(timezone.utc).timestamp()),
        "jti": jti,
    }
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(
    user: Usuario,
    expires_delta: timedelta | None = None,
) -> str:
    """Create JWT refresh token (longer expiry)."""
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))
    jti = str(uuid4())
    to_encode = {
        "sub": str(user.id),
        "type": "refresh",
        "exp": int(expire.timestamp()),
        "iat": int(datetime.now(timezone.utc).timestamp()),
        "jti": jti,
    }
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> TokenData | None:
    """Decode and validate JWT token."""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return TokenData(**payload)
    except JWTError:
        return None


# --------------------------------------------
# FASTAPI DEPENDENCIES
# --------------------------------------------

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Usuario:
    """Get current authenticated user from JWT."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token_data = decode_token(credentials.credentials)
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verificar refresh token no revocado
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == hash_password(token_data.jti))
    )
    refresh_token = result.scalar_one_or_none()
    if refresh_token and refresh_token.revocado:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Cargar usuario
    result = await db.execute(select(Usuario).where(Usuario.id == token_data.sub))
    user = result.scalar_one_or_none()
    if not user or not user.activo:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    return user


async def get_current_tenant(
    user: Annotated[Usuario, Depends(get_current_user)],
) -> str:
    """Get current tenant_id from authenticated user."""
    return str(user.tenant_id)


def require_roles(*allowed_roles: str):
    """Dependency factory for role-based access control."""
    async def role_checker(user: Annotated[Usuario, Depends(get_current_user)]) -> Usuario:
        if not any(role in user.roles for role in allowed_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required roles: {allowed_roles}",
            )
        return user
    return role_checker


# Common role dependencies
require_admin = require_roles(RolSistema.SUPERADMIN, RolSistema.ADMIN_ASESORIA)
require_asesor = require_roles(
    RolSistema.ASESOR_MERCANTIL,
    RolSistema.ASESOR_ADMINISTRATIVO,
    RolSistema.ASESOR_CONTABLE,
    RolSistema.ASESOR_PERSONAL,
    RolSistema.ADMIN_ASESORIA,
    RolSistema.SUPERADMIN,
)
require_cliente = require_roles(RolSistema.CLIENTE_TITULAR, RolSistema.CLIENTE_EMPLEADO)


# --------------------------------------------
# RLS CONTEXT MIDDLEWARE
# --------------------------------------------

async def set_rls_context(request: Request, db: AsyncSession):
    """Middleware to set RLS context for current tenant."""
    # Se ejecuta después de get_current_user
    if hasattr(request.state, "user"):
        from gestia_core.database import set_tenant_context
        set_tenant_context(db, str(request.state.user.tenant_id))