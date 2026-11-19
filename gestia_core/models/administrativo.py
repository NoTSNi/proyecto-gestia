"""GESTIA Administrativo Models - EscritoAdministrativo."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from gestia_core.models.base import Base, TimestampMixin, UUIDMixin, TenantMixin

if TYPE_CHECKING:
    from gestia_core.models.tenant import Empresa
    from gestia_core.models.document import Documento


class EscritoAdministrativo(Base, UUIDMixin, TimestampMixin, TenantMixin):
    """Escritos, recursos, licencias, subvenciones."""

    __tablename__ = "escritos_administrativos"

    # Clasificación
    tipo: Mapped[str] = mapped_column(String(50), nullable=False)
    organo_destinatario: Mapped[str] = mapped_column(String(200), nullable=False)
    referencia_expediente: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Fechas
    fecha_presentacion: Mapped[datetime | None] = mapped_column(nullable=True)
    fecha_limite_respuesta: Mapped[datetime | None] = mapped_column(nullable=True)
    fecha_resolucion: Mapped[datetime | None] = mapped_column(nullable=True)

    # Contenido
    asunto: Mapped[str] = mapped_column(String(300), nullable=False)
    hechos: Mapped[str | None] = mapped_column(Text, nullable=True)
    fundamentos_derecho: Mapped[str | None] = mapped_column(Text, nullable=True)
    suplico: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Estado
    estado: Mapped[str] = mapped_column(String(30), default="borrador")
    resultado: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Documentos asociados
    documento_id: Mapped[str | None] = mapped_column(
        PG_UUID(as_uuid=False), ForeignKey("documentos.id", ondelete="SET NULL"), nullable=True
    )

    # Relaciones
    empresa: Mapped[Empresa] = relationship(
        "Empresa",
        back_populates="escritos_admin",
        lazy="selectin",
        primaryjoin="EscritoAdministrativo.tenant_id==Empresa.id",
    )

    __table_args__ = (
        Index("ix_escritos_tipo_estado", "tenant_id", "tipo", "estado"),
        Index("ix_escritos_fecha_limite", "tenant_id", "fecha_limite_respuesta"),
    )