"""GESTIA Payroll Models - Nomina, Contrato."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, Numeric, String, Text, UniqueConstraint, JSON
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from gestia_core.models.base import Base, TimestampMixin, UUIDMixin, TenantMixin
from gestia_core.models.enums import TipoNomina

if TYPE_CHECKING:
    from gestia_core.models.tenant import Empresa


class Nomina(Base, UUIDMixin, TimestampMixin, TenantMixin):
    """Nómina de empleado."""

    __tablename__ = "nominas"

    empleado_id: Mapped[str] = mapped_column(PG_UUID(as_uuid=False), nullable=False, index=True)
    empleado_nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    empleado_nif: Mapped[str] = mapped_column(String(20), nullable=False)
    empleado_naf: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Período
    anio: Mapped[int] = mapped_column(nullable=False)
    mes: Mapped[int] = mapped_column(nullable=False)
    tipo: Mapped[str] = mapped_column(String(30), default=TipoNomina.MENSUAL)

    # Fechas
    fecha_devengo_inicio: Mapped[datetime] = mapped_column(nullable=False)
    fecha_devengo_fin: Mapped[datetime] = mapped_column(nullable=False)
    fecha_pago: Mapped[datetime | None] = mapped_column(nullable=True)

    # Datos nómina (JSON estructurado)
    datos_nomina: Mapped[dict] = mapped_column(JSONB, default=dict)

    # TC1/TC2
    tc1_generado: Mapped[bool] = mapped_column(default=False)
    tc1_datos: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    tc2_generado: Mapped[bool] = mapped_column(default=False)
    tc2_datos: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Estado
    estado: Mapped[str] = mapped_column(String(30), default="borrador")

    # Relaciones
    empresa: Mapped[Empresa] = relationship(
        "Empresa",
        back_populates="nominas",
        lazy="selectin",
        primaryjoin="Nomina.tenant_id==Empresa.id",
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "empleado_id", "anio", "mes", "tipo", name="uq_nomina_empleado_periodo"),
        Index("ix_nominas_anio_mes_estado", "tenant_id", "anio", "mes", "estado"),
    )


class Contrato(Base, UUIDMixin, TimestampMixin, TenantMixin):
    """Contrato laboral."""

    __tablename__ = "contratos"

    empleado_id: Mapped[str] = mapped_column(PG_UUID(as_uuid=False), nullable=False, index=True)
    empleado_nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    empleado_nif: Mapped[str] = mapped_column(String(20), nullable=False)

    # Tipo contrato
    tipo_contrato: Mapped[str] = mapped_column(String(50), nullable=False)
    codigo_contrato: Mapped[str] = mapped_column(String(10), nullable=False)

    # Fechas
    fecha_inicio: Mapped[datetime] = mapped_column(nullable=False)
    fecha_fin: Mapped[datetime | None] = mapped_column(nullable=True)
    fecha_fin_estimada: Mapped[datetime | None] = mapped_column(nullable=True)

    # Jornada
    jornada_tipo: Mapped[str] = mapped_column(String(30), default="completa")
    jornada_horas_semana: Mapped[float | None] = mapped_column(Numeric(4, 1), nullable=True)

    # Salario
    salario_base: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    complementos: Mapped[dict] = mapped_column(JSONB, default=dict)
    convenio_colectivo: Mapped[str | None] = mapped_column(String(200), nullable=True)
    grupo_cotizacion: Mapped[int] = mapped_column(default=1)

    # Centro de trabajo
    centro_trabajo: Mapped[str | None] = mapped_column(String(200), nullable=True)
    ccc: Mapped[str | None] = mapped_column(String(11), nullable=True)

    # Estado
    estado: Mapped[str] = mapped_column(String(30), default="activo")
    causa_baja: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Relaciones
    empresa: Mapped[Empresa] = relationship(
        "Empresa",
        back_populates="contratos",
        lazy="selectin",
        primaryjoin="Contrato.tenant_id==Empresa.id",
    )

    __table_args__ = (
        Index("ix_contratos_empleado_estado", "tenant_id", "empleado_id", "estado"),
        Index("ix_contratos_fecha_fin", "tenant_id", "fecha_fin"),
    )