"""GESTIA Web - Seguridad: JWT + dependencias de autenticación por cookies.

Sesión vía cookie httpOnly con JWT (jose). Se expone:
- login(): valida credenciales contra SQLite y fija cookie
- logout(): borra cookie
- get_current_user(): dependencia FastAPI que carga usuario desde cookie
- require_roles(): dependencia de RBAC
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import Depends, HTTPException, Request, status
from jose import JWTError, jwt

from gestia_core.config import get_settings
from web import database

settings = get_settings()

COOKIE_NAME = "gestia_token"


def create_access_token(user: dict, expires_minutes: int | None = None) -> str:
    """Crea JWT con identidad y tenant del usuario."""
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {
        "sub": user["id"],
        "email": user["email"],
        "tenant_id": user.get("tenant_id"),
        "rol": user["rol"],
        "exp": int(expire.timestamp()),
        "iat": int(datetime.now(timezone.utc).timestamp()),
        "jti": str(uuid4()),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except JWTError:
        return None


def read_token_from_cookie(request: Request) -> str | None:
    return request.cookies.get(COOKIE_NAME)


async def get_current_user(request: Request) -> dict:
    """Carga el usuario autenticado desde la cookie JWT."""
    token = read_token_from_cookie(request)
    payload = decode_token(token) if token else None
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No autenticado")

    user = await database.get_usuario_by_email(payload["email"])
    if not user or not user.get("activo"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario no válido")
    user["tenant_id"] = payload.get("tenant_id") or user.get("tenant_id")
    user["rol"] = payload.get("rol") or user.get("rol")
    return user


def require_roles(*allowed_roles: str):
    """Dependency factory para RBAC."""

    async def checker(user: dict = Depends(get_current_user)) -> dict:
        if user["rol"] not in allowed_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sin permisos")
        return user

    return checker


def is_asesor(rol: str) -> bool:
    return rol in ("superadmin", "admin_asesoria", "asesor_contable", "asesor_mercantil",
                   "asesor_administrativo", "asesor_personal")


def is_cliente(rol: str) -> bool:
    return rol in ("cliente_titular", "cliente_empleado")


def role_label(rol: str) -> str:
    labels = {
        "superadmin": "Superadministrador",
        "admin_asesoria": "Admin de Asesoría",
        "asesor_contable": "Asesor Contable",
        "asesor_mercantil": "Asesor Mercantil",
        "asesor_administrativo": "Asesor Administrativo",
        "asesor_personal": "Asesor de Personal",
        "cliente_titular": "Cliente - Titular",
        "cliente_empleado": "Cliente - Empleado",
    }
    return labels.get(rol, rol)
