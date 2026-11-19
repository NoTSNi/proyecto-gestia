"""GESTIA API - Personal Routes (Nóminas, Contratos)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from gestia_core.database import get_db
from gestia_core.models import Nomina, Contrato
from gestia_core.schemas import NominaCreate, NominaUpdate, NominaResponse, ContratoCreate, ContratoUpdate, ContratoResponse, PaginatedResponse
from gestia_core.security import get_current_user, get_current_tenant

router = APIRouter(prefix="/personal", tags=["Personal"])


# ----- NÓMINAS -----

@router.post("/nominas", response_model=NominaResponse, status_code=status.HTTP_201_CREATED, summary="Create nómina")
async def create_nomina(
    nomina_data: NominaCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant),
):
    """Create nómina."""
    nomina = Nomina(**nomina_data.model_dump(), tenant_id=tenant_id)
    db.add(nomina)
    await db.commit()
    await db.refresh(nomina)
    return nomina


@router.get("/nominas", response_model=PaginatedResponse, summary="List nóminas")
async def list_nominas(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    anio: int | None = Query(None),
    mes: int | None = Query(None),
    empleado_id: str | None = Query(None),
    estado: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """List nóminas."""
    query = select(Nomina).where(Nomina.tenant_id == tenant_id)

    if anio:
        query = query.where(Nomina.anio == anio)
    if mes:
        query = query.where(Nomina.mes == mes)
    if empleado_id:
        query = query.where(Nomina.empleado_id == empleado_id)
    if estado:
        query = query.where(Nomina.estado == estado)

    query = query.order_by(Nomina.anio.desc(), Nomina.mes.desc())

    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0

    query = query.offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    nominas = result.scalars().all()

    total_pages = (total + per_page - 1) // per_page
    return PaginatedResponse(
        data=[NominaResponse.model_validate(n) for n in nominas],
        meta={"total": total, "page": page, "per_page": per_page, "total_pages": total_pages},
        links={},
    )


@router.get("/nominas/{nomina_id}", response_model=NominaResponse, summary="Get nómina by ID")
async def get_nomina(
    nomina_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """Get nómina by ID."""
    result = await db.execute(
        select(Nomina).where(Nomina.id == nomina_id, Nomina.tenant_id == tenant_id)
    )
    nomina = result.scalar_one_or_none()
    if not nomina:
        raise HTTPException(status_code=404, detail="Nómina not found")
    return nomina


@router.patch("/nominas/{nomina_id}", response_model=NominaResponse, summary="Update nómina")
async def update_nomina(
    nomina_id: str,
    nomina_data: NominaUpdate,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """Update nómina."""
    result = await db.execute(
        select(Nomina).where(Nomina.id == nomina_id, Nomina.tenant_id == tenant_id)
    )
    nomina = result.scalar_one_or_none()
    if not nomina:
        raise HTTPException(status_code=404, detail="Nómina not found")

    for field, value in nomina_data.model_dump(exclude_unset=True).items():
        setattr(nomina, field, value)

    await db.commit()
    await db.refresh(nomina)
    return nomina


@router.post("/nominas/{nomina_id}/calcular", summary="Calculate nómina (trigger agent)")
async def calcular_nomina(
    nomina_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """Trigger personal agent to calculate nómina."""
    result = await db.execute(
        select(Nomina).where(Nomina.id == nomina_id, Nomina.tenant_id == tenant_id)
    )
    nomina = result.scalar_one_or_none()
    if not nomina:
        raise HTTPException(status_code=404, detail="Nómina not found")

    # TODO: Trigger personal agent
    return {"message": f"Nómina calculation triggered", "nomina_id": nomina_id}


@router.post("/nominas/{nomina_id}/generar-tc1-tc2", summary="Generate TC1/TC2")
async def generar_tc1_tc2(
    nomina_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """Generate TC1/TC2 for nómina."""
    result = await db.execute(
        select(Nomina).where(Nomina.id == nomina_id, Nomina.tenant_id == tenant_id)
    )
    nomina = result.scalar_one_or_none()
    if not nomina:
        raise HTTPException(status_code=404, detail="Nómina not found")

    # TODO: Trigger TC1/TC2 generation
    return {"message": "TC1/TC2 generation triggered", "nomina_id": nomina_id}


# ----- CONTRATOS -----

@router.post("/contratos", response_model=ContratoResponse, status_code=status.HTTP_201_CREATED, summary="Create contrato")
async def create_contrato(
    contrato_data: ContratoCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant),
):
    """Create contrato laboral."""
    contrato = Contrato(**contrato_data.model_dump(), tenant_id=tenant_id)
    db.add(contrato)
    await db.commit()
    await db.refresh(contrato)
    return contrato


@router.get("/contratos", response_model=PaginatedResponse, summary="List contratos")
async def list_contratos(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    empleado_id: str | None = Query(None),
    estado: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """List contratos."""
    query = select(Contrato).where(Contrato.tenant_id == tenant_id)

    if empleado_id:
        query = query.where(Contrato.empleado_id == empleado_id)
    if estado:
        query = query.where(Contrato.estado == estado)

    query = query.order_by(Contrato.fecha_inicio.desc())

    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0

    query = query.offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    contratos = result.scalars().all()

    total_pages = (total + per_page - 1) // per_page
    return PaginatedResponse(
        data=[ContratoResponse.model_validate(c) for c in contratos],
        meta={"total": total, "page": page, "per_page": per_page, "total_pages": total_pages},
        links={},
    )


@router.get("/contratos/{contrato_id}", response_model=ContratoResponse, summary="Get contrato by ID")
async def get_contrato(
    contrato_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """Get contrato by ID."""
    result = await db.execute(
        select(Contrato).where(Contrato.id == contrato_id, Contrato.tenant_id == tenant_id)
    )
    contrato = result.scalar_one_or_none()
    if not contrato:
        raise HTTPException(status_code=404, detail="Contrato not found")
    return contrato


@router.patch("/contratos/{contrato_id}", response_model=ContratoResponse, summary="Update contrato")
async def update_contrato(
    contrato_id: str,
    contrato_data: ContratoUpdate,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """Update contrato."""
    result = await db.execute(
        select(Contrato).where(Contrato.id == contrato_id, Contrato.tenant_id == tenant_id)
    )
    contrato = result.scalar_one_or_none()
    if not contrato:
        raise HTTPException(status_code=404, detail="Contrato not found")

    for field, value in contrato_data.model_dump(exclude_unset=True).items():
        setattr(contrato, field, value)

    await db.commit()
    await db.refresh(contrato)
    return contrato