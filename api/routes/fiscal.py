"""GESTIA API - Fiscal Routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from gestia_core.database import get_db
from gestia_core.models import ModeloFiscal
from gestia_core.schemas import ModeloFiscalCreate, ModeloFiscalUpdate, ModeloFiscalResponse, PaginatedResponse
from gestia_core.security import get_current_user, get_current_tenant

router = APIRouter()


@router.post("", response_model=ModeloFiscalResponse, status_code=status.HTTP_201_CREATED, summary="Create modelo fiscal")
async def create_modelo(
    modelo_data: ModeloFiscalCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant),
):
    """Create modelo fiscal."""
    # Check unique constraint
    result = await db.execute(
        select(ModeloFiscal).where(
            ModeloFiscal.tenant_id == tenant_id,
            ModeloFiscal.codigo_modelo == modelo_data.codigo_modelo,
            ModeloFiscal.anio == modelo_data.anio,
            ModeloFiscal.periodo == modelo_data.periodo,
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Modelo already exists for this period")

    modelo = ModeloFiscal(**modelo_data.model_dump(), tenant_id=tenant_id)
    db.add(modelo)
    await db.commit()
    await db.refresh(modelo)
    return modelo


@router.get("", response_model=PaginatedResponse, summary="List modelos fiscales")
async def list_modelos(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    codigo_modelo: str | None = Query(None),
    estado: str | None = Query(None),
    anio: int | None = Query(None),
    periodo: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """List modelos fiscales."""
    query = select(ModeloFiscal).where(ModeloFiscal.tenant_id == tenant_id)

    if codigo_modelo:
        query = query.where(ModeloFiscal.codigo_modelo == codigo_modelo)
    if estado:
        query = query.where(ModeloFiscal.estado == estado)
    if anio:
        query = query.where(ModeloFiscal.anio == anio)
    if periodo:
        query = query.where(ModeloFiscal.periodo == periodo)

    query = query.order_by(ModeloFiscal.fecha_limite_presentacion.asc())

    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0

    query = query.offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    modelos = result.scalars().all()

    total_pages = (total + per_page - 1) // per_page
    return PaginatedResponse(
        data=[ModeloFiscalResponse.model_validate(m) for m in modelos],
        meta={"total": total, "page": page, "per_page": per_page, "total_pages": total_pages},
        links={},
    )


@router.get("/{modelo_id}", response_model=ModeloFiscalResponse, summary="Get modelo by ID")
async def get_modelo(
    modelo_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """Get modelo by ID."""
    result = await db.execute(
        select(ModeloFiscal).where(ModeloFiscal.id == modelo_id, ModeloFiscal.tenant_id == tenant_id)
    )
    modelo = result.scalar_one_or_none()
    if not modelo:
        raise HTTPException(status_code=404, detail="Modelo not found")
    return modelo


@router.patch("/{modelo_id}", response_model=ModeloFiscalResponse, summary="Update modelo")
async def update_modelo(
    modelo_id: str,
    modelo_data: ModeloFiscalUpdate,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """Update modelo fiscal."""
    result = await db.execute(
        select(ModeloFiscal).where(ModeloFiscal.id == modelo_id, ModeloFiscal.tenant_id == tenant_id)
    )
    modelo = result.scalar_one_or_none()
    if not modelo:
        raise HTTPException(status_code=404, detail="Modelo not found")

    for field, value in modelo_data.model_dump(exclude_unset=True).items():
        setattr(modelo, field, value)

    await db.commit()
    await db.refresh(modelo)
    return modelo


@router.post("/{modelo_id}/calcular", summary="Calculate modelo (trigger agent)")
async def calcular_modelo(
    modelo_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """Trigger contable agent to calculate modelo."""
    result = await db.execute(
        select(ModeloFiscal).where(ModeloFiscal.id == modelo_id, ModeloFiscal.tenant_id == tenant_id)
    )
    modelo = result.scalar_one_or_none()
    if not modelo:
        raise HTTPException(status_code=404, detail="Modelo not found")

    # TODO: Trigger contable agent via n8n or direct call
    return {"message": f"Calculation triggered for {modelo.codigo_modelo}", "modelo_id": modelo_id}


@router.post("/{modelo_id}/presentar", summary="Submit modelo to AEAT")
async def presentar_modelo(
    modelo_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """Submit modelo to AEAT (generate XML, send)."""
    result = await db.execute(
        select(ModeloFiscal).where(ModeloFiscal.id == modelo_id, ModeloFiscal.tenant_id == tenant_id)
    )
    modelo = result.scalar_one_or_none()
    if not modelo:
        raise HTTPException(status_code=404, detail="Modelo not found")

    if modelo.estado != "validado":
        raise HTTPException(status_code=400, detail="Modelo must be validated before submission")

    # TODO: Generate XML, submit via AEAT API
    return {"message": f"Submission triggered for {modelo.codigo_modelo}", "modelo_id": modelo_id}