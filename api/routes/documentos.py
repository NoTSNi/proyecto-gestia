"""GESTIA API - Documentos Routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from gestia_core.database import get_db
from gestia_core.models import Documento, ChunkDocumento
from gestia_core.schemas import (
    DocumentoCreate,
    DocumentoResponse,
    DocumentoUploadResponse,
    PaginatedResponse,
)
from gestia_core.security import get_current_user, get_current_tenant
from gestia_core.utils import sha256_hash, validate_file_type, validate_file_size, sanitize_filename

router = APIRouter()


@router.post("/upload", response_model=DocumentoUploadResponse, status_code=status.HTTP_202_ACCEPTED, summary="Upload document for processing")
async def upload_document(
    file: UploadFile = File(...),
    tipo: str = "otro",
    fuente: str = "portal",
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant),
):
    """Upload document - returns immediately, processing happens async via n8n."""
    # Read file
    content = await file.read()
    size = len(content)

    # Validate
    ok, err = validate_file_type(file.content_type or "", file.filename or "")
    if not ok:
        raise HTTPException(status_code=400, detail=err)

    ok, err = validate_file_size(size)
    if not ok:
        raise HTTPException(status_code=400, detail=err)

    # Hash
    file_hash = sha256_hash(content)

    # Check duplicate
    from gestia_core.models import Empresa
    result = await db.execute(
        select(Documento).where(Documento.tenant_id == tenant_id, Documento.sha256 == file_hash)
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Document already exists (same content)")

    # Save to MinIO (placeholder - implement with boto3/minio client)
    from gestia_core.config import get_settings
    settings = get_settings()
    filename_storage = f"{file_hash}{Path(file.filename).suffix}"
    object_key = f"{tenant_id}/{filename_storage}"

    # TODO: Upload to MinIO
    # minio_client.put_object(settings.MINIO_BUCKET, object_key, content)

    # Create document record in quarantine
    doc = Documento(
        tenant_id=tenant_id,
        filename_original=sanitize_filename(file.filename),
        filename_storage=filename_storage,
        content_type=file.content_type or "application/octet-stream",
        size_bytes=size,
        sha256=file_hash,
        bucket=settings.MINIO_BUCKET,
        object_key=object_key,
        tipo=tipo,
        fuente=fuente,
        estado="cuarentena",
        correlation_id=generate_correlation_id(),
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    # Trigger n8n ingestion workflow (async)
    # await trigger_n8n_ingestion(doc.id, tenant_id, object_key)

    return DocumentoUploadResponse(
        document_id=doc.id,
        correlation_id=doc.correlation_id,
        estado=doc.estado,
        estimated_processing_seconds=30,
        tracking_url=f"/api/v1/documentos/{doc.id}/tracking",
    )


@router.get("", response_model=PaginatedResponse, summary="List documents")
async def list_documentos(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    tipo: str | None = Query(None),
    estado: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """List documents for current tenant."""
    query = select(Documento).where(Documento.tenant_id == tenant_id)

    if tipo:
        query = query.where(Documento.tipo == tipo)
    if estado:
        query = query.where(Documento.estado == estado)

    query = query.order_by(Documento.created_at.desc())

    # Count
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0

    # Paginate
    query = query.offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    docs = result.scalars().all()

    total_pages = (total + per_page - 1) // per_page
    return PaginatedResponse(
        data=[DocumentoResponse.model_validate(d) for d in docs],
        meta={"total": total, "page": page, "per_page": per_page, "total_pages": total_pages},
        links={},
    )


@router.get("/{doc_id}", response_model=DocumentoResponse, summary="Get document by ID")
async def get_documento(
    doc_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """Get document by ID."""
    result = await db.execute(
        select(Documento).where(Documento.id == doc_id, Documento.tenant_id == tenant_id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.get("/{doc_id}/chunks", summary="Get document chunks (RAG)")
async def get_document_chunks(
    doc_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant),
):
    """Get document chunks for RAG."""
    # Verify document exists
    result = await db.execute(
        select(Documento).where(Documento.id == doc_id, Documento.tenant_id == tenant_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Document not found")

    result = await db.execute(
        select(ChunkDocumento)
        .where(ChunkDocumento.documento_id == doc_id, ChunkDocumento.tenant_id == tenant_id)
        .order_by(ChunkDocumento.chunk_index)
    )
    chunks = result.scalars().all()
    return [{"index": c.chunk_index, "content": c.content, "tokens": c.token_count} for c in chunks]


def generate_correlation_id() -> str:
    import uuid
    return str(uuid.uuid4())


from pathlib import Path