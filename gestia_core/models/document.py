"""GESTIA Document Models - Documento, ChunkDocumento."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import ForeignKey, Index, Integer, String, Text, UniqueConstraint, JSON
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from gestia_core.models.base import Base, TimestampMixin, UUIDMixin, TenantMixin
from gestia_core.models.enums import EstadoDocumento, TipoDocumento

if TYPE_CHECKING:
    from gestia_core.models.tenant import Empresa


class Documento(Base, UUIDMixin, TimestampMixin, TenantMixin):
    """Documento subido al vault (factura, contrato, escrito, etc.)."""

    __tablename__ = "documentos"

    # Archivo original
    filename_original: Mapped[str] = mapped_column(String(500), nullable=False)
    filename_storage: Mapped[str] = mapped_column(String(500), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    # MinIO/S3
    bucket: Mapped[str] = mapped_column(String(100), nullable=False)
    object_key: Mapped[str] = mapped_column(String(500), nullable=False)
    version_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Clasificación
    tipo: Mapped[str] = mapped_column(String(50), default=TipoDocumento.OTRO, nullable=False)
    estado: Mapped[str] = mapped_column(String(30), default=EstadoDocumento.CUARENTENA, nullable=False)

    # OCR / Extracción
    ocr_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    ocr_confidence: Mapped[float | None] = mapped_column(nullable=True)
    ocr_engine: Mapped[str | None] = mapped_column(String(50), nullable=True)
    metadatos_extraidos: Mapped[dict] = mapped_column(JSONB, default=dict)

    # RAG / Embeddings
    chunks_count: Mapped[int] = mapped_column(Integer, default=0)
    embeddings_model: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Procesamiento
    procesado_en: Mapped[datetime | None] = mapped_column(nullable=True)
    error_procesamiento: Mapped[str | None] = mapped_column(Text, nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)

    # Fuente de ingesta
    fuente: Mapped[str] = mapped_column(String(50), default="portal")

    # Relaciones
    empresa: Mapped[Empresa] = relationship(
        "Empresa",
        back_populates="documentos",
        lazy="selectin",
        primaryjoin="Documento.tenant_id==Empresa.id",
    )
    chunks: Mapped[list[ChunkDocumento]] = relationship(
        "ChunkDocumento",
        back_populates="documento",
        lazy="selectin",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "sha256", name="uq_documento_tenant_hash"),
        Index("ix_documentos_tipo_estado", "tenant_id", "tipo", "estado"),
        Index("ix_documentos_fecha_tipo", "tenant_id", "created_at", "tipo"),
    )


class ChunkDocumento(Base, UUIDMixin, TimestampMixin, TenantMixin):
    """Chunk de documento para RAG (vector embedding)."""

    __tablename__ = "chunks_documento"

    documento_id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=False), ForeignKey("documentos.id", ondelete="CASCADE"), nullable=False, index=True
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False)

    # Vector embedding (pgvector) - se usa tipo ARRAY o vector extension
    embedding: Mapped[list[float] | None] = mapped_column(JSONB, nullable=True)

    # Metadatos del chunk
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    section_title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Relaciones
    documento: Mapped[Documento] = relationship("Documento", back_populates="chunks", lazy="selectin")

    __table_args__ = (
        Index("ix_chunks_documento_doc_idx", "documento_id", "chunk_index"),
    )


# Import datetime para type hints
from datetime import datetime