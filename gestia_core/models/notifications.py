"""GESTIA Notification Models - Notificacion."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, String, Text, JSON
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from gestia_core.models.base import Base, TimestampMixin, UUIDMixin, TenantMixin
from gestia_core.models.enums import CanalNotificacion, TipoUsuario

if TYPE_CHECKING:
    from gestia_core.models.tenant import Empresa


class Notificacion(Base, UUIDMixin, TimestampMixin, TenantMixin):
    """Notificaciones multicanal (asesor y cliente)."""

    __tablename__ = "notificaciones"

    canal: Mapped[str] = mapped_column(String(30), nullable=False)
    destinatario_tipo: Mapped[str] = mapped_column(String(30), nullable=False)
    destinatario_id: Mapped[str | None] = mapped_column(PG_UUID(as_uuid=False), nullable=True)

    asunto: Mapped[str] = mapped_column(String(300), nullable=False)
    cuerpo: Mapped[str] = mapped_column(Text, nullable=False)
    cuerpo_html: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Template y datos
    template_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    template_data: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Estado envío
    estado: Mapped[str] = mapped_column(String(30), default="pendiente")
    enviado_en: Mapped[datetime | None] = mapped_column(nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    reintentos: Mapped[int] = mapped_column(default=0)
    max_reintentos: Mapped[int] = mapped_column(default=3)

    # Referencia externa
    external_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Relaciones
    empresa: Mapped[Empresa] = relationship(
        "Empresa",
        back_populates="notificaciones",
        lazy="selectin",
        primaryjoin="Notificacion.tenant_id==Empresa.id",
    )

    __table_args__ = (
        Index("ix_notificaciones_tenant_estado", "tenant_id", "estado"),
        Index("ix_notificaciones_destinatario", "destinatario_tipo", "destinatario_id"),
    )