"""GESTIA Calendar Models - CalendarioEvento."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from gestia_core.models.base import Base, TimestampMixin, UUIDMixin, TenantMixin

if TYPE_CHECKING:
    from gestia_core.models.tenant import Empresa
    from gestia_core.models.fiscal import ModeloFiscal


class CalendarioEvento(Base, UUIDMixin, TimestampMixin, TenantMixin):
    """Eventos de calendario fiscal, laboral, mercantil."""

    __tablename__ = "calendario_eventos"

    # Identificación
    titulo: Mapped[str] = mapped_column(String(300), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Categoría y tipo
    categoria: Mapped[str] = mapped_column(String(50), nullable=False)
    tipo_evento: Mapped[str] = mapped_column(String(100), nullable=False)

    # Fechas
    fecha_inicio: Mapped[datetime] = mapped_column(nullable=False, index=True)
    fecha_fin: Mapped[datetime | None] = mapped_column(nullable=True)
    fecha_limite: Mapped[datetime] = mapped_column(nullable=False, index=True)
    todo_el_dia: Mapped[bool] = mapped_column(default=False)

    # Recurrencia
    es_recurrente: Mapped[bool] = mapped_column(default=False)
    regla_rrule: Mapped[str | None] = mapped_column(String(500), nullable=True)
    anio_fiscal: Mapped[int] = mapped_column(nullable=False, index=True)
    periodo: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Estado y acciones
    estado: Mapped[str] = mapped_column(String(30), default="pendiente")
    requiere_accion: Mapped[bool] = mapped_column(default=True)
    accion_sugerida: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # Modelo fiscal asociado (opcional)
    modelo_fiscal_id: Mapped[str | None] = mapped_column(
        PG_UUID(as_uuid=False), ForeignKey("modelos_fiscales.id", ondelete="SET NULL"), nullable=True
    )

    # Notificaciones
    notificado_15d: Mapped[bool] = mapped_column(default=False)
    notificado_7d: Mapped[bool] = mapped_column(default=False)
    notificado_1d: Mapped[bool] = mapped_column(default=False)
    notificado_dia: Mapped[bool] = mapped_column(default=False)

    # Relaciones
    empresa: Mapped[Empresa] = relationship(
        "Empresa",
        back_populates="eventos_calendario",
        lazy="selectin",
        primaryjoin="CalendarioEvento.tenant_id==Empresa.id",
    )

    __table_args__ = (
        Index("ix_calendario_tenant_fecha_limite", "tenant_id", "fecha_limite"),
        Index("ix_calendario_tenant_categoria", "tenant_id", "categoria", "fecha_limite"),
        Index("ix_calendario_anio_periodo", "tenant_id", "anio_fiscal", "periodo"),
    )