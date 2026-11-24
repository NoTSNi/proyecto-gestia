#!/usr/bin/env python3
"""
Embedding Service - FastAPI wrapper for text embeddings (sentence-transformers).
"""
from __future__ import annotations

from typing import Optional, List

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Embedding Service", version="1.0.0")


class EmbedRequest(BaseModel):
    text: str
    model: str = "text-embedding-3-small"


class EmbedResponse(BaseModel):
    embedding: List[float]
    model: str
    dimensions: int


class BatchEmbedRequest(BaseModel):
    texts: List[str]
    model: str = "text-embedding-3-small"


class BatchEmbedResponse(BaseModel):
    embeddings: List[List[float]]
    model: str
    dimensions: int


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "embedding-service"}


@app.on_event("startup")
async def load_model():
    global _model
    try:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("all-MiniLM-L6-v2")  # 384 dims, fast, good for Spanish
        print("✅ Embedding model loaded: all-MiniLM-L6-v2")
    except ImportError:
        _model = None
        print("⚠️ sentence-transformers not installed")


@app.post("/embed", response_model=EmbedResponse)
async def embed_endpoint(request: EmbedRequest):
    """Generate embedding for a single text."""
    if _model is None:
        raise HTTPException(status_code=500, detail="Model not loaded")

    try:
        embedding = _model.encode(request.text).tolist()
        return EmbedResponse(
            embedding=embedding,
            model=request.model,
            dimensions=len(embedding),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Embedding failed: {str(e)}")


@app.post("/embed/batch", response_model=BatchEmbedResponse)
async def embed_batch_endpoint(request: BatchEmbedRequest):
    """Generate embeddings for multiple texts."""
    if _model is None:
        raise HTTPException(status_code=500, detail="Model not loaded")

    try:
        embeddings = _model.encode(request.texts).tolist()
        return BatchEmbedResponse(
            embeddings=embeddings,
            model=request.model,
            dimensions=len(embeddings[0]) if embeddings else 0,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch embedding failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


_model = None