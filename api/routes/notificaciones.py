"""GESTIA API - Notificaciones Routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from gestia_core.database import get_db
from gestia_core.models import Notificacion
from gestia_core.schemas import PaginatedResponse
from gestia_core.security import get_current_user, get_current_tenant

router = APIRouter()


@router.get("", response_model=PaginatedResponse, summary="List notificaciones")
async def list_notificaciones(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    canal: str | None = Query(None),
    estado: str | None = Query(None),
    destinatario_tipo: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """List notificaciones."""
    query = select(Notificacion).where(Notificacion.tenant_id == tenant_id)

    if canal:
        query = query.where(Notificacion.canal == canal)
    if estado:
        query = query.where(Notificacion.estado == estado)
    if destinatario_tipo:
        query = query.where(Notificacion.destinatario_tipo == destinatario_tipo)

    query = query.order_by(Notificacion.created_at.desc())

    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0

    query = query.offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    notificaciones = result.scalars().all()

    total_pages = (total + per_page - 1) // per_page
    return PaginatedResponse(
        data=[{
            "id": n.id,
            "canal": n.canal,
            "destinatario_tipo": n.destinatario_tipo,
            "destinatario_id": n.destinatario_id,
            "asunto": n.asunto,
            "estado": n.estado,
            "enviado_en": n.enviado_en,
            "created_at": n.created_at,
        } for n in notificaciones],
        meta={"total": total, "page": page, "per_page": per_page, "total_pages": total_pages},
        links={},
    )


@router.get("/{notificacion_id}", summary="Get notificacion by ID")
async def get_notificacion(
    notificacion_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """Get notificacion by ID."""
    result = await db.execute(
        select(Notificacion).where(Notificacion.id == notificacion_id, Notificacion.tenant_id == tenant_id)
    )
    n = result.scalar_one_or_none()
    if not n:
        raise HTTPException(status_code=404, detail="Notificacion not found")
    return {
        "id": n.id,
        "canal": n.canal,
        "destinatario_tipo": n.destinatario_tipo,
        "destinatario_id": n.destinatario_id,
        "asunto": n.asunto,
        "cuerpo": n.cuerpo,
        "cuerpo_html": n.cuerpo_html,
        "template_id": n.template_id,
        "template_data": n.template_data,
        "estado": n.estado,
        "enviado_en": n.enviado_en,
        "error": n.error,
        "reintentos": n.reintentos,
        "external_id": n.external_id,
        "created_at": n.created_at,
    }