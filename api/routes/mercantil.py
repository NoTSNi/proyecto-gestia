"""GESTIA API - Mercantil Routes (Libros)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from gestia_core.database import get_db
from gestia_core.models import LibroMercantil
from gestia_core.schemas import LibroMercantilCreate, LibroMercantilUpdate, LibroMercantilResponse, PaginatedResponse
from gestia_core.security import get_current_user, get_current_tenant

router = APIRouter(prefix="/mercantil", tags=["Mercantil"])


@router.post("/libros", response_model=LibroMercantilResponse, status_code=status.HTTP_201_CREATED, summary="Create libro mercantil")
async def create_libro(
    libro_data: LibroMercantilCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant),
):
    """Create libro mercantil."""
    libro = LibroMercantil(**libro_data.model_dump(), tenant_id=tenant_id)
    db.add(libro)
    await db.commit()
    await db.refresh(libro)
    return libro


@router.get("/libros", response_model=PaginatedResponse, summary="List libros mercantiles")
async def list_libros(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    tipo_libro: str | None = Query(None),
    anio: int | None = Query(None),
    estado: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """List libros mercantiles."""
    query = select(LibroMercantil).where(LibroMercantil.tenant_id == tenant_id)

    if tipo_libro:
        query = query.where(LibroMercantil.tipo_libro == tipo_libro)
    if anio:
        query = query.where(LibroMercantil.anio == anio)
    if estado:
        query = query.where(LibroMercantil.estado == estado)

    query = query.order_by(LibroMercantil.anio.desc())

    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0

    query = query.offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    libros = result.scalars().all()

    total_pages = (total + per_page - 1) // per_page
    return PaginatedResponse(
        data=[LibroMercantilResponse.model_validate(l) for l in libros],
        meta={"total": total, "page": page, "per_page": per_page, "total_pages": total_pages},
        links={},
    )


@router.get("/libros/{libro_id}", response_model=LibroMercantilResponse, summary="Get libro by ID")
async def get_libro(
    libro_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """Get libro by ID."""
    result = await db.execute(
        select(LibroMercantil).where(LibroMercantil.id == libro_id, LibroMercantil.tenant_id == tenant_id)
    )
    libro = result.scalar_one_or_none()
    if not libro:
        raise HTTPException(status_code=404, detail="Libro not found")
    return libro


@router.patch("/libros/{libro_id}", response_model=LibroMercantilResponse, summary="Update libro")
async def update_libro(
    libro_id: str,
    libro_data: LibroMercantilUpdate,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """Update libro."""
    result = await db.execute(
        select(LibroMercantil).where(LibroMercantil.id == libro_id, LibroMercantil.tenant_id == tenant_id)
    )
    libro = result.scalar_one_or_none()
    if not libro:
        raise HTTPException(status_code=404, detail="Libro not found")

    for field, value in libro_data.model_dump(exclude_unset=True).items():
        setattr(libro, field, value)

    await db.commit()
    await db.refresh(libro)
    return libro


@router.post("/libros/{libro_id}/legalizar", summary="Legalize libro")
async def legalizar_libro(
    libro_id: str,
    registro: str,
    numero: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """Mark libro as legalized."""
    from datetime import datetime, timezone

    result = await db.execute(
        select(LibroMercantil).where(LibroMercantil.id == libro_id, LibroMercantil.tenant_id == tenant_id)
    )
    libro = result.scalar_one_or_none()
    if not libro:
        raise HTTPException(status_code=404, detail="Libro not found")

    libro.legalizado = True
    libro.fecha_legalizacion = datetime.now(timezone.utc)
    libro.registro_mercantil = registro
    libro.numero_legalizacion = numero
    libro.estado = "legalizado"

    await db.commit()
    return {"message": "Libro legalizado", "libro_id": libro_id}


@router.post("/libros/{libro_id}/depositar", summary="Deposit cuentas anuales")
async def depositar_cuentas(
    libro_id: str,
    ejercicio: int,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """Mark libro as deposited."""
    from datetime import datetime, timezone

    result = await db.execute(
        select(LibroMercantil).where(LibroMercantil.id == libro_id, LibroMercantil.tenant_id == tenant_id)
    )
    libro = result.scalar_one_or_none()
    if not libro:
        raise HTTPException(status_code=404, detail="Libro not found")

    libro.deposito_cuentas = True
    libro.fecha_deposito = datetime.now(timezone.utc)
    libro.ejercicio_deposito = ejercicio
    libro.estado = "depositado"

    await db.commit()
    return {"message": "Cuentas depositadas", "libro_id": libro_id}