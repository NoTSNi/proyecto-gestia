"""GESTIA Audit Models - AuditLog."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Index, String, Text, JSON
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from gestia_core.models.base import Base, UUIDMixin

if TYPE_CHECKING:
    pass


class AuditLog(Base, UUIDMixin):
    """Log de auditoría inmutable (append-only)."""

    __tablename__ = "audit_logs"

    # Quién
    usuario_id: Mapped[str | None] = mapped_column(PG_UUID(as_uuid=False), nullable=True)
    usuario_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    usuario_tipo: Mapped[str | None] = mapped_column(String(30), nullable=True)

    # Qué
    accion: Mapped[str] = mapped_column(String(100), nullable=False)
    recurso: Mapped[str] = mapped_column(String(100), nullable=False)
    recurso_id: Mapped[str | None] = mapped_column(PG_UUID(as_uuid=False), nullable=True)

    # Detalles
    cambios: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Contexto
    ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)

    # Timestamp (inmutable)
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(datetime.now().astimezone().tzinfo), nullable=False
    )

    __table_args__ = (
        Index("ix_audit_tenant_recurso_fecha", "created_at"),
        Index("ix_audit_usuario_fecha", "usuario_id", "created_at"),
        Index("ix_audit_correlation", "correlation_id"),
    )