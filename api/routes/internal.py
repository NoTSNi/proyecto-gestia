"""GESTIA API - Internal Routes (n8n callbacks)."""

from __future__ import annotations

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from gestia_core.database import get_db
from gestia_core.models import Documento, ChunkDocumento
from gestia_core.security import get_current_user, get_current_tenant

router = APIRouter(prefix="/n8n", tags=["Internal"])


# --------------------------------------------
# SCHEMAS
# --------------------------------------------

class N8NIngestionCallback(BaseModel):
    document_id: str
    tenant_id: str
    chunks: list[dict]  # [{index, content, tokens, page, section, embedding}]
    classification: dict  # {tipo, confidence}
    metadatos: dict
    ocr_text: str | None = None
    ocr_confidence: float | None = None
    ocr_engine: str | None = None
    status: str = "completed"  # completed, error
    error: str | None = None


class N8NCalendarCallback(BaseModel):
    tenant_id: str
    anio: int
    eventos: list[dict]
    status: str = "completed"
    error: str | None = None


class N8NNotificationCallback(BaseModel):
    notification_id: str
    external_id: str | None = None
    status: str  # sent, failed
    error: str | None = None


# --------------------------------------------
# DOCUMENT INGESTION CALLBACK
# --------------------------------------------

@router.post("/callback/ingestion", status_code=status.HTTP_200_OK, summary="n8n document ingestion callback")
async def n8n_ingestion_callback(
    payload: N8NIngestionCallback,
    db: AsyncSession = Depends(get_db),
):
    """Callback from n8n after document processing."""
    # Verify document exists and belongs to tenant
    result = await db.execute(
        select(Documento).where(Documento.id == payload.document_id, Documento.tenant_id == payload.tenant_id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if payload.status == "error":
        doc.estado = "error"
        doc.error_procesamiento = payload.error
        doc.procesado_en = datetime.now(timezone.utc)
        await db.commit()
        return {"status": "error_recorded"}

    # Update document
    doc.estado = "indexado"
    doc.ocr_text = payload.ocr_text
    doc.ocr_confidence = payload.ocr_confidence
    doc.ocr_engine = payload.ocr_engine
    doc.metadatos_extraidos = payload.metadatos
    doc.chunks_count = len(payload.chunks)
    doc.embeddings_model = payload.chunks[0].get("embedding_model") if payload.chunks else None
    doc.procesado_en = datetime.now(timezone.utc)
    doc.tipo = payload.classification.get("tipo", doc.tipo)

    # Save chunks with embeddings
    for chunk_data in payload.chunks:
        chunk = ChunkDocumento(
            tenant_id=payload.tenant_id,
            documento_id=payload.document_id,
            chunk_index=chunk_data["index"],
            content=chunk_data["content"],
            token_count=chunk_data["tokens"],
            embedding=chunk_data.get("embedding"),
            page_number=chunk_data.get("page"),
            section_title=chunk_data.get("section"),
            metadata_json=chunk_data.get("metadata", {}),
        )
        db.add(chunk)

    await db.commit()
    return {"status": "ok", "chunks_saved": len(payload.chunks)}


# --------------------------------------------
# CALENDAR SYNC CALLBACK
# --------------------------------------------

@router.post("/callback/calendar", status_code=status.HTTP_200_OK, summary="n8n calendar sync callback")
async def n8n_calendar_callback(
    payload: N8NCalendarCallback,
    db: AsyncSession = Depends(get_db),
):
    """Callback from n8n after calendar sync."""
    from gestia_core.models import CalendarioEvento

    # Upsert eventos (simplified - in production use proper upsert)
    for evento_data in payload.eventos:
        evento = CalendarioEvento(
            tenant_id=payload.tenant_id,
            **evento_data,
        )
        db.add(evento)

    await db.commit()
    return {"status": "ok", "events_synced": len(payload.eventos)}


# --------------------------------------------
# NOTIFICATION CALLBACK
# --------------------------------------------

@router.post("/callback/notification", status_code=status.HTTP_200_OK, summary="n8n notification callback")
async def n8n_notification_callback(
    payload: N8NNotificationCallback,
    db: AsyncSession = Depends(get_db),
):
    """Callback from n8n after notification send."""
    from gestia_core.models import Notificacion

    result = await db.execute(
        select(Notificacion).where(Notificacion.id == payload.notification_id)
    )
    notif = result.scalar_one_or_none()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")

    notif.estado = payload.status
    notif.enviado_en = datetime.now(timezone.utc) if payload.status == "sent" else None
    notif.external_id = payload.external_id
    notif.error = payload.error

    await db.commit()
    return {"status": "ok"}