#!/usr/bin/env python3
"""
GESTIA Agents - Enhanced Specialist Base with Infrastructure Integration.
"""
from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Optional

import httpx

from agents.base_agent import BaseAgent, AgentContext, AgentResponse


class InfrastructureClient:
    """Client for interacting with GESTIA infrastructure services."""
    
    def __init__(self):
        self.docling_url = os.getenv("DOCLING_URL", "http://localhost:8001")
        self.embedding_url = os.getenv("EMBEDDING_URL", "http://localhost:8002")
        self.api_url = os.getenv("API_URL", "http://localhost:8000")
        self.timeout = 30.0
    
    async def ocr_document(self, file_path: str) -> dict:
        """Extract text and structure from document via Docling OCR."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                with open(file_path, "rb") as f:
                    files = {"file": (os.path.basename(file_path), f, "application/octet-stream")}
                    resp = await client.post(f"{self.docling_url}/ocr", files=files)
                    resp.raise_for_status()
                    return resp.json()
        except Exception as e:
            return {"error": str(e), "text": "", "tables": []}
    
    async def get_embeddings(self, texts: list[str]) -> list[list[float]]:
        """Get vector embeddings for texts."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    f"{self.embedding_url}/embed",
                    json={"texts": texts}
                )
                resp.raise_for_status()
                return resp.json().get("embeddings", [])
        except Exception as e:
            return [[] for _ in texts]
    
    async def search_similar(self, query: str, top_k: int = 5) -> list[dict]:
        """Search similar documents in vector store."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    f"{self.embedding_url}/search",
                    json={"query": query, "top_k": top_k}
                )
                resp.raise_for_status()
                return resp.json().get("results", [])
        except Exception as e:
            return []
    
    async def call_api(self, endpoint: str, method: str = "GET", data: dict = None) -> dict:
        """Call internal API."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                url = f"{self.api_url}{endpoint}"
                if method == "GET":
                    resp = await client.get(url)
                else:
                    resp = await client.post(url, json=data)
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            return {"error": str(e)}


class EnhancedSpecialistBase(BaseAgent, ABC):
    """
    Enhanced base for domain specialists with:
    - Document Vault integration (OCR + Embeddings)
    - Database persistence
    - Structured action planning
    - Citation/traceability
    """
    
    domain: str = "general"
    capabilities: list[str] = []
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.domain = self.__class__.__name__.replace("Agent", "").lower()
        self.infra = InfrastructureClient()
        self.client_data_path = "cliente_ejemplo"
        self._context_metadata: dict | None = None
    
    # ============================================================
    # INFRASTRUCTURE INTEGRATION
    # ============================================================
    
    async def process_document(self, file_path: str) -> dict:
        """Process document through OCR + Embedding pipeline."""
        # OCR
        ocr_result = await self.infra.ocr_document(file_path)
        text = ocr_result.get("text", "")
        tables = ocr_result.get("tables", [])
        
        # Embeddings
        if text:
            chunks = self._chunk_text(text)
            embeddings = await self.infra.get_embeddings(chunks)
        else:
            chunks, embeddings = [], []
        
        return {
            "file": os.path.basename(file_path),
            "text": text,
            "chunks": chunks,
            "embeddings": embeddings,
            "tables": tables,
            "processed_at": datetime.now().isoformat(),
        }
    
    def _chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
        """Split text into overlapping chunks."""
        chunks = []
        for i in range(0, len(text), chunk_size - overlap):
            chunk = text[i:i + chunk_size]
            if chunk.strip():
                chunks.append(chunk.strip())
        return chunks
    
    async def search_knowledge(self, query: str, top_k: int = 5) -> list[dict]:
        """Busca en la KB curada del dominio (Fase F), con fallback al vector store.

        Primero consulta la base de conocimiento local del especialista
        (contable/mercantil/personal/administrativo). Si no hay resultados o
        el servicio externo está disponible, vuelve al vector store.
        """
        from agents.knowledge_base import KB_INSTANCE
        resultados = KB_INSTANCE.buscar(self.domain, query, top_k=top_k)
        if resultados:
            return [
                {
                    "titulo": r["titulo"],
                    "texto": r["texto"],
                    "fuentes": r.get("fuentes", []),
                    "vigente_desde": r.get("vigente_desde"),
                    "fuente": "kb_curated",
                }
                for r in resultados
            ]
        # Fallback: vector store externo
        return await self.infra.search_similar(query, top_k)
    
    async def get_client_context(self, tenant_id: str) -> dict:
        """Load client context from database (vía context.metadata) or test data.

        Prioridad:
        1. Datos reales inyectados en `context.metadata["client_data"]` (BD, web).
        2. Fichero `cliente_ejemplo/metadata.json` (demo/tests).
        """
        # Si la web puso datos reales del tenant, úsalos
        ctx_metadata = self._context_metadata or {}
        client_data = ctx_metadata.get("client_data")
        if client_data:
            return {"cliente_real": client_data, "fuente": "bd"}
        # Fallback a datos de demostración
        meta_path = os.path.join(self.client_data_path, "metadata.json")
        if os.path.exists(meta_path):
            with open(meta_path) as f:
                return json.load(f)
        return {}

    def bind_context_metadata(self, metadata: dict) -> None:
        """Fija metadata del contexto para usar datos reales en get_client_context()."""
        self._context_metadata = metadata or {}
    
    # ============================================================
    # STRUCTURED RESPONSE BUILDING
    # ============================================================
    
    def build_response(
        self,
        action: str,
        summary: str,
        details: dict = None,
        next_steps: list[str] = None,
        documents_needed: list[str] = None,
        deadlines: list[dict] = None,
        citations: list[str] = None,
        confidence: float = 0.9,
    ) -> AgentResponse:
        """Build structured specialist response."""
        data = {
            "action": action,
            "domain": self.domain,
            "confidence": confidence,
            "summary": summary,
            "details": details or {},
            "next_steps": next_steps or [],
            "documents_needed": documents_needed or [],
            "deadlines": deadlines or [],
            "citations": citations or [],
            "timestamp": datetime.now().isoformat(),
        }
        
        # Human-readable response
        response = f"**{self.domain.upper()} - {action.replace('_', ' ').title()}**\n\n{summary}\n"
        
        if next_steps:
            response += "\n📋 **Próximos pasos:**\n" + "\n".join(f"  {i+1}. {s}" for i, s in enumerate(next_steps))
        
        if documents_needed:
            response += "\n📄 **Documentos necesarios:**\n" + "\n".join(f"  • {d}" for d in documents_needed)
        
        if deadlines:
            response += "\n⏰ **Plazos:**\n" + "\n".join(f"  • {d['description']}: {d['date']}" for d in deadlines)
        
        if citations:
            response += "\n📚 **Referencias:**\n" + "\n".join(f"  • {c}" for c in citations)
        
        return AgentResponse(
            agent=self.name,
            success=True,
            response=response,
            data=data,
            actions=[{"type": "specialist_action", "action": action, **data}],
        )
    
    def build_error_response(self, error: str, action: str = "error") -> AgentResponse:
        """Build error response."""
        return AgentResponse(
            agent=self.name,
            success=False,
            response=f"❌ Error en {self.domain}: {error}",
            data={"action": action, "domain": self.domain, "error": error},
            error=error,
        )
    
    # ============================================================
    # ABSTRACT METHODS
    # ============================================================
    
    @abstractmethod
    async def analyze(self, query: str, context: AgentContext) -> dict:
        """Analyze query and return action plan."""
        pass
    
    async def process(self, query: str, context: AgentContext) -> AgentResponse:
        """Main entry point - analyze and execute."""
        try:
            analysis = await self.analyze(query, context)
            response = await self.execute(analysis, query, context)
            # Fase F: enriquecer con conocimiento curado del dominio (citas + fuentes)
            if response.success:
                await self._enrich_with_kb(query, response)
            return response
        except Exception as e:
            return self.build_error_response(str(e))

    async def _enrich_with_kb(self, query: str, response: AgentResponse) -> None:
        """Añade al response las referencias de la KB curada del dominio (Fase F).

        Consulta el conocimiento local (contable/mercantil/personal/administrativo)
        relacionado con la consulta y lo incorpora como 'kb_references' en data, más
        una leyenda '⚖ Referencia normativa' al final de la respuesta humana.
        No altera la acción principal; solo aporta contexto normativo.
        """
        try:
            from agents.knowledge_base import KB_INSTANCE
            refs = KB_INSTANCE.buscar(self.domain, query, top_k=3)
            if not refs:
                return
            kb_datos = [
                {
                    "titulo": r["titulo"],
                    "fuentes": r.get("fuentes", []),
                    "texto": r["texto"],
                    "vigente_desde": r.get("vigente_desde"),
                }
                for r in refs
            ]
            if response.data is None:
                response.data = {}
            response.data["kb_references"] = kb_datos
            # Leyenda normativa al final
            if not response.response.endswith("\n\n"):
                response.response += "\n"
            for r in refs:
                fuentes = ", ".join(r.get("fuentes", []))
                response.response += (
                    f"\n⚖ **{r['titulo']}** — {fuentes}"
                )
        except Exception:
            # El enriquecimiento nunca debe romper la respuesta
            pass
    
    @abstractmethod
    async def execute(self, analysis: dict, query: str, context: AgentContext) -> AgentResponse:
        """Execute the action plan."""
        pass


# ============================================================
# ACTION PLAN STRUCTURE
# ============================================================

class ActionPlan:
    """Structured action plan for specialist execution."""
    
    def __init__(
        self,
        action_type: str,
        query: str,
        confidence: float = 0.9,
        parameters: dict = None,
        requires_documents: list[str] = None,
        produces_documents: list[str] = None,
        estimated_time: str = "inmediato",
        requires_human_review: bool = False,
    ):
        self.action_type = action_type
        self.query = query
        self.confidence = confidence
        self.parameters = parameters or {}
        self.requires_documents = requires_documents or []
        self.produces_documents = produces_documents or []
        self.estimated_time = estimated_time
        self.requires_human_review = requires_human_review
    
    def to_dict(self) -> dict:
        return {
            "action_type": self.action_type,
            "query": self.query,
            "confidence": self.confidence,
            "parameters": self.parameters,
            "requires_documents": self.requires_documents,
            "produces_documents": self.produces_documents,
            "estimated_time": self.estimated_time,
            "requires_human_review": self.requires_human_review,
        }