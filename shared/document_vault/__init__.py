"""GESTIA Shared - Document Vault (OCR, RAG, Classification)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO
from uuid import uuid4


@dataclass
class DocumentMetadata:
    filename: str
    content_type: str
    size_bytes: int
    sha256: str
    page_count: int | None = None


class DocumentVault:
    """Document storage with OCR, classification, and RAG indexing."""

    def __init__(self, minio_client, vector_store, n8n_client):
        self.minio = minio_client
        self.vector_store = vector_store
        self.n8n = n8n_client

    async def upload(
        self,
        tenant_id: str,
        file: BinaryIO,
        filename: str,
        content_type: str,
        source: str = "portal",
    ) -> str:
        """Upload document to quarantine, return document_id."""
        content = file.read()
        sha256 = self._sha256(content)
        file.seek(0)

        object_key = f"{tenant_id}/quarantine/{sha256}{Path(filename).suffix}"
        await self.minio.put_object("gestia-quarantine", object_key, content)

        doc_id = str(uuid4())
        # TODO: Save to DB with estado="cuarentena"

        await self.n8n.trigger_ingestion(
            tenant_id=tenant_id,
            document_id=doc_id,
            object_key=object_key,
            filename=filename,
            content_type=content_type,
            source=source,
        )

        return doc_id

    async def get_document(self, tenant_id: str, doc_id: str) -> bytes | None:
        pass

    async def search_similar(
        self,
        tenant_id: str,
        query: str,
        top_k: int = 10,
        filter_metadata: dict | None = None,
    ) -> list[dict]:
        return await self.vector_store.search(
            tenant_id=tenant_id,
            query=query,
            top_k=top_k,
            filter=filter_metadata,
        )

    def _sha256(self, data: bytes) -> str:
        import hashlib
        return hashlib.sha256(data).hexdigest()


# OCR Engines
class OCREngine:
    async def extract(self, file_path: Path) -> tuple[str, float, dict]:
        raise NotImplementedError


class DoclingOCR(OCREngine):
    async def extract(self, file_path: Path) -> tuple[str, float, dict]:
        return "", 0.0, {"engine": "docling", "status": "not_implemented"}


class MarkerOCR(OCREngine):
    async def extract(self, file_path: Path) -> tuple[str, float, dict]:
        return "", 0.0, {"engine": "marker", "status": "not_implemented"}


class AzureDocumentIntelligence(OCREngine):
    async def extract(self, file_path: Path) -> tuple[str, float, dict]:
        return "", 0.0, {"engine": "azure", "status": "not_implemented"}