"""GESTIA API - Calendario Routes."""

from __future__ import annotations

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from gestia_core.database import get_db
from gestia_core.models import CalendarioEvento
from gestia_core.schemas import CalendarioEventoCreate, CalendarioEventoUpdate, CalendarioEventoResponse, PaginatedResponse
from gestia_core.security import get_current_user, get_current_tenant

router = APIRouter()


@router.post("", response_model=CalendarioEventoResponse, status_code=status.HTTP_201_CREATED, summary="Create calendar event")
async def create_evento(
    evento_data: CalendarioEventoCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant),
):
    """Create calendar event."""
    evento = CalendarioEvento(**evento_data.model_dump(), tenant_id=tenant_id)
    db.add(evento)
    await db.commit()
    await db.refresh(evento)
    return evento


@router.get("", response_model=PaginatedResponse, summary="List calendar events")
async def list_eventos(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    categoria: str | None = Query(None),
    tipo_evento: str | None = Query(None),
    estado: str | None = Query(None),
    fecha_desde: datetime | None = Query(None),
    fecha_hasta: datetime | None = Query(None),
    anio_fiscal: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """List calendar events."""
    query = select(CalendarioEvento).where(CalendarioEvento.tenant_id == tenant_id)

    if categoria:
        query = query.where(CalendarioEvento.categoria == categoria)
    if tipo_evento:
        query = query.where(CalendarioEvento.tipo_evento == tipo_evento)
    if estado:
        query = query.where(CalendarioEvento.estado == estado)
    if fecha_desde:
        query = query.where(CalendarioEvento.fecha_limite >= fecha_desde)
    if fecha_hasta:
        query = query.where(CalendarioEvento.fecha_limite <= fecha_hasta)
    if anio_fiscal:
        query = query.where(CalendarioEvento.anio_fiscal == anio_fiscal)

    query = query.order_by(CalendarioEvento.fecha_limite.asc())

    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0

    query = query.offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    eventos = result.scalars().all()

    total_pages = (total + per_page - 1) // per_page
    return PaginatedResponse(
        data=[CalendarioEventoResponse.model_validate(e) for e in eventos],
        meta={"total": total, "page": page, "per_page": per_page, "total_pages": total_pages},
        links={},
    )


@router.get("/proximos", summary="Get upcoming deadlines")
async def get_proximos(
    dias: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """Get upcoming deadlines within N days."""
    from datetime import datetime, timezone, timedelta
    ahora = datetime.now(timezone.utc)
    limite = ahora + timedelta(days=dias)

    result = await db.execute(
        select(CalendarioEvento)
        .where(
            CalendarioEvento.tenant_id == tenant_id,
            CalendarioEvento.fecha_limite >= ahora,
            CalendarioEvento.fecha_limite <= limite,
            CalendarioEvento.estado == "pendiente",
        )
        .order_by(CalendarioEvento.fecha_limite.asc())
    )
    eventos = result.scalars().all()
    return [CalendarioEventoResponse.model_validate(e) for e in eventos]


@router.get("/{evento_id}", response_model=CalendarioEventoResponse, summary="Get event by ID")
async def get_evento(
    evento_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """Get event by ID."""
    result = await db.execute(
        select(CalendarioEvento).where(CalendarioEvento.id == evento_id, CalendarioEvento.tenant_id == tenant_id)
    )
    evento = result.scalar_one_or_none()
    if not evento:
        raise HTTPException(status_code=404, detail="Event not found")
    return evento


@router.patch("/{evento_id}", response_model=CalendarioEventoResponse, summary="Update event")
async def update_evento(
    evento_id: str,
    evento_data: CalendarioEventoUpdate,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """Update event."""
    result = await db.execute(
        select(CalendarioEvento).where(CalendarioEvento.id == evento_id, CalendarioEvento.tenant_id == tenant_id)
    )
    evento = result.scalar_one_or_none()
    if not evento:
        raise HTTPException(status_code=404, detail="Event not found")

    for field, value in evento_data.model_dump(exclude_unset=True).items():
        setattr(evento, field, value)

    await db.commit()
    await db.refresh(evento)
    return evento


@router.post("/sync", summary="Sync fiscal/laboral calendar for year")
async def sync_calendar(
    anio: int = Query(..., ge=2020, le=2030),
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """Trigger n8n calendar sync for year."""
    # TODO: Trigger n8n workflow
    return {"message": f"Calendar sync triggered for {anio}", "triggered": True}