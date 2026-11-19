"""GESTIA Mercantil Models - LibroMercantil."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from gestia_core.models.base import Base, TimestampMixin, UUIDMixin, TenantMixin

if TYPE_CHECKING:
    from gestia_core.models.tenant import Empresa


class LibroMercantil(Base, UUIDMixin, TimestampMixin, TenantMixin):
    """Libros oficiales mercantiles (Diario, Mayor, Inventario, Actas)."""

    __tablename__ = "libros_mercantiles"

    tipo_libro: Mapped[str] = mapped_column(String(50), nullable=False)
    anio: Mapped[int] = mapped_column(nullable=False)
    tomo: Mapped[int | None] = mapped_column(nullable=True)
    folio_inicio: Mapped[int | None] = mapped_column(nullable=True)
    folio_fin: Mapped[int | None] = mapped_column(nullable=True)

    # Legalización
    legalizado: Mapped[bool] = mapped_column(Boolean, default=False)
    fecha_legalizacion: Mapped[datetime | None] = mapped_column(nullable=True)
    registro_mercantil: Mapped[str | None] = mapped_column(String(200), nullable=True)
    numero_legalizacion: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Depósito cuentas anuales
    deposito_cuentas: Mapped[bool] = mapped_column(Boolean, default=False)
    fecha_deposito: Mapped[datetime | None] = mapped_column(nullable=True)
    ejercicio_deposito: Mapped[int | None] = mapped_column(nullable=True)

    # Estado
    estado: Mapped[str] = mapped_column(String(30), default="abierto")

    # Relaciones
    empresa: Mapped[Empresa] = relationship(
        "Empresa",
        back_populates="libros_mercantiles",
        lazy="selectin",
        primaryjoin="LibroMercantil.tenant_id==Empresa.id",
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "tipo_libro", "anio", "tomo", name="uq_libro_tenant_anio_tomo"),
        Index("ix_libros_anio_estado", "tenant_id", "anio", "estado"),
    )