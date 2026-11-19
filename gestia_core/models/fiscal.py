"""GESTIA Fiscal Models - ModeloFiscal."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, Numeric, String, Text, UniqueConstraint, JSON
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from gestia_core.models.base import Base, TimestampMixin, UUIDMixin, TenantMixin
from gestia_core.models.enums import EstadoModeloFiscal

if TYPE_CHECKING:
    from gestia_core.models.tenant import Empresa


class ModeloFiscal(Base, UUIDMixin, TimestampMixin, TenantMixin):
    """Modelos fiscales (303, 200, 111, 190, 347, 349, 390, etc.)."""

    __tablename__ = "modelos_fiscales"

    # Identificación
    codigo_modelo: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Período
    anio: Mapped[int] = mapped_column(nullable=False)
    periodo: Mapped[str] = mapped_column(String(20), nullable=False)
    fecha_inicio_periodo: Mapped[datetime] = mapped_column(nullable=False)
    fecha_fin_periodo: Mapped[datetime] = mapped_column(nullable=False)
    fecha_limite_presentacion: Mapped[datetime] = mapped_column(nullable=False, index=True)

    # Estado
    estado: Mapped[str] = mapped_column(String(30), default=EstadoModeloFiscal.BORRADOR, nullable=False)

    # Datos calculados (JSON flexible por modelo)
    datos_calculados: Mapped[dict] = mapped_column(JSONB, default=dict)

    # XML AEAT
    xml_aeat: Mapped[str | None] = mapped_column(Text, nullable=True)
    xml_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Presentación
    presentado_en: Mapped[datetime | None] = mapped_column(nullable=True)
    numero_justificante: Mapped[str | None] = mapped_column(String(50), nullable=True)
    csv_aeat: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Pago
    importe_pagar: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    pagado: Mapped[bool] = mapped_column(default=False)
    fecha_pago: Mapped[datetime | None] = mapped_column(nullable=True)
    metodo_pago: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Errores/Validación
    errores_validacion: Mapped[list[dict]] = mapped_column(JSONB, default=list)

    # Relaciones
    empresa: Mapped[Empresa] = relationship(
        "Empresa",
        back_populates="modelos_fiscales",
        lazy="selectin",
        primaryjoin="ModeloFiscal.tenant_id==Empresa.id",
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "codigo_modelo", "anio", "periodo", name="uq_modelo_tenant_anio_periodo"),
        Index("ix_modelos_estado_fecha", "tenant_id", "estado", "fecha_limite_presentacion"),
    )