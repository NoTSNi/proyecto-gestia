"""GESTIA API - Empresas Routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from gestia_core.database import get_db
from gestia_core.models import Empresa
from gestia_core.schemas import (
    EmpresaCreate,
    EmpresaUpdate,
    EmpresaResponse,
    PaginatedResponse,
)
from gestia_core.security import get_current_user, get_current_tenant, require_admin

router = APIRouter()


@router.post("", response_model=EmpresaResponse, status_code=status.HTTP_201_CREATED, summary="Create new empresa")
async def create_empresa(
    empresa_data: EmpresaCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_admin),
):
    """Create new empresa (tenant). Admin only."""
    from gestia_core.utils import validate_nif

    if not validate_nif(empresa_data.nif):
        raise HTTPException(status_code=400, detail="Invalid NIF/CIF")

    # Check NIF unique
    result = await db.execute(select(Empresa).where(Empresa.nif == empresa_data.nif.upper()))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="NIF already registered")

    empresa = Empresa(**empresa_data.model_dump())
    empresa.nif = empresa.nif.upper()
    db.add(empresa)
    await db.commit()
    await db.refresh(empresa)

    return empresa


@router.get("", response_model=PaginatedResponse, summary="List empresas")
async def list_empresas(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    estado: str | None = Query(None),
    search: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant),
):
    """List empresas (filtered by tenant for non-superadmin)."""
    from gestia_core.models import RolSistema

    query = select(Empresa)

    # Superadmin ve todas, resto solo su tenant
    if RolSistema.SUPERADMIN not in current_user.roles:
        query = query.where(Empresa.id == tenant_id)

    if estado:
        query = query.where(Empresa.estado == estado)
    if search:
        query = query.where(Empresa.nombre.ilike(f"%{search}%"))

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0

    # Paginate
    query = query.offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    empresas = result.scalars().all()

    total_pages = (total + per_page - 1) // per_page
    return PaginatedResponse(
        data=[EmpresaResponse.model_validate(e) for e in empresas],
        meta={
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
        },
        links={
            "self": f"?page={page}&per_page={per_page}",
            "next": f"?page={page+1}&per_page={per_page}" if page < total_pages else None,
            "prev": f"?page={page-1}&per_page={per_page}" if page > 1 else None,
            "last": f"?page={total_pages}&per_page={per_page}",
        },
    )


@router.get("/{empresa_id}", response_model=EmpresaResponse, summary="Get empresa by ID")
async def get_empresa(
    empresa_id: str,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant),
):
    """Get empresa by ID."""
    from gestia_core.models import RolSistema

    query = select(Empresa).where(Empresa.id == empresa_id)
    if RolSistema.SUPERADMIN not in current_user.roles:
        query = query.where(Empresa.id == tenant_id)

    result = await db.execute(query)
    empresa = result.scalar_one_or_none()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa not found")

    return empresa


@router.patch("/{empresa_id}", response_model=EmpresaResponse, summary="Update empresa")
async def update_empresa(
    empresa_id: str,
    empresa_data: EmpresaUpdate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_admin),
    tenant_id: str = Depends(get_current_tenant),
):
    """Update empresa."""
    from gestia_core.models import RolSistema

    query = select(Empresa).where(Empresa.id == empresa_id)
    if RolSistema.SUPERADMIN not in current_user.roles:
        query = query.where(Empresa.id == tenant_id)

    result = await db.execute(query)
    empresa = result.scalar_one_or_none()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa not found")

    update_data = empresa_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(empresa, field, value)

    await db.commit()
    await db.refresh(empresa)
    return empresa


@router.delete("/{empresa_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete empresa (soft)")
async def delete_empresa(
    empresa_id: str,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_admin),
    tenant_id: str = Depends(get_current_tenant),
):
    """Soft delete empresa (set estado=baja)."""
    from gestia_core.models import RolSistema
    from datetime import datetime, timezone

    query = select(Empresa).where(Empresa.id == empresa_id)
    if RolSistema.SUPERADMIN not in current_user.roles:
        query = query.where(Empresa.id == tenant_id)

    result = await db.execute(query)
    empresa = result.scalar_one_or_none()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa not found")

    empresa.estado = "baja"
    empresa.fecha_baja = datetime.now(timezone.utc)
    await db.commit()