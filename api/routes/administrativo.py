"""GESTIA API - Administrativo Routes (Escritos)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from gestia_core.database import get_db
from gestia_core.models import EscritoAdministrativo
from gestia_core.schemas import EscritoAdministrativoCreate, EscritoAdministrativoUpdate, EscritoAdministrativoResponse, PaginatedResponse
from gestia_core.security import get_current_user, get_current_tenant

router = APIRouter(prefix="/administrativo", tags=["Administrativo"])


@router.post("/escritos", response_model=EscritoAdministrativoResponse, status_code=status.HTTP_201_CREATED, summary="Create escrito administrativo")
async def create_escrito(
    escrito_data: EscritoAdministrativoCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant),
):
    """Create escrito administrativo."""
    escrito = EscritoAdministrativo(**escrito_data.model_dump(), tenant_id=tenant_id)
    db.add(escrito)
    await db.commit()
    await db.refresh(escrito)
    return escrito


@router.get("/escritos", response_model=PaginatedResponse, summary="List escritos administrativos")
async def list_escritos(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    tipo: str | None = Query(None),
    estado: str | None = Query(None),
    organo: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """List escritos administrativos."""
    query = select(EscritoAdministrativo).where(EscritoAdministrativo.tenant_id == tenant_id)

    if tipo:
        query = query.where(EscritoAdministrativo.tipo == tipo)
    if estado:
        query = query.where(EscritoAdministrativo.estado == estado)
    if organo:
        query = query.where(EscritoAdministrativo.organo_destinatario.ilike(f"%{organo}%"))

    query = query.order_by(EscritoAdministrativo.created_at.desc())

    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0

    query = query.offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    escritos = result.scalars().all()

    total_pages = (total + per_page - 1) // per_page
    return PaginatedResponse(
        data=[EscritoAdministrativoResponse.model_validate(e) for e in escritos],
        meta={"total": total, "page": page, "per_page": per_page, "total_pages": total_pages},
        links={},
    )


@router.get("/escritos/{escrito_id}", response_model=EscritoAdministrativoResponse, summary="Get escrito by ID")
async def get_escrito(
    escrito_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """Get escrito by ID."""
    result = await db.execute(
        select(EscritoAdministrativo).where(
            EscritoAdministrativo.id == escrito_id, EscritoAdministrativo.tenant_id == tenant_id
        )
    )
    escrito = result.scalar_one_or_none()
    if not escrito:
        raise HTTPException(status_code=404, detail="Escrito not found")
    return escrito


@router.patch("/escritos/{escrito_id}", response_model=EscritoAdministrativoResponse, summary="Update escrito")
async def update_escrito(
    escrito_id: str,
    escrito_data: EscritoAdministrativoUpdate,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """Update escrito."""
    result = await db.execute(
        select(EscritoAdministrativo).where(
            EscritoAdministrativo.id == escrito_id, EscritoAdministrativo.tenant_id == tenant_id
        )
    )
    escrito = result.scalar_one_or_none()
    if not escrito:
        raise HTTPException(status_code=404, detail="Escrito not found")

    for field, value in escrito_data.model_dump(exclude_unset=True).items():
        setattr(escrito, field, value)

    await db.commit()
    await db.refresh(escrito)
    return escrito