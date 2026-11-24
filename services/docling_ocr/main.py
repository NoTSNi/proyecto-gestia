#!/usr/bin/env python3
"""
Docling OCR Service - FastAPI wrapper for Docling document processing.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI(title="Docling OCR Service", version="1.0.0")


class OCRRequest(BaseModel):
    file_path: str
    languages: list[str] = ["es", "en"]


class OCRResponse(BaseModel):
    text: str
    confidence: float
    metadata: dict
    pages: int


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "docling-ocr"}


@app.post("/ocr", response_model=OCRResponse)
async def ocr_endpoint(
    file: Optional[UploadFile] = File(None),
    file_path: Optional[str] = Form(None),
    languages: str = Form("es,en"),
):
    """
    Process document with Docling OCR.
    Accepts either file upload or file_path (for n8n workflow).
    """
    try:
        from docling.document_converter import DocumentConverter
        from docling.datamodel.base_models import InputFormat
        from docling.datamodel.pipeline_options import PdfPipelineOptions
    except ImportError:
        raise HTTPException(status_code=500, detail="Docling not installed")

    # Handle file upload or file path
    if file:
        # Save uploaded file to temp
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name
    elif file_path:
        tmp_path = file_path
    else:
        raise HTTPException(status_code=400, detail="file or file_path required")

    try:
        # Configure Docling
        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_ocr = True
        pipeline_options.do_table_structure = True
        pipeline_options.ocr_options.lang = languages.split(",")

        converter = DocumentConverter(
            format_options={
                InputFormat.PDF: pipeline_options,
            }
        )

        # Convert
        result = converter.convert(tmp_path)

        # Extract text
        full_text = result.document.export_to_markdown()
        
        # Calculate confidence (Docling doesn't provide direct confidence, estimate)
        confidence = 0.9 if len(full_text) > 100 else 0.5

        # Extract metadata
        metadata = {
            "pages": len(result.document.pages) if hasattr(result.document, 'pages') else 1,
            "tables": len(result.document.tables) if hasattr(result.document, 'tables') else 0,
            "languages": languages,
        }

        return OCRResponse(
            text=full_text,
            confidence=confidence,
            metadata=metadata,
            pages=metadata["pages"],
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OCR failed: {str(e)}")
    finally:
        # Cleanup temp file if we created it
        if file and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except:
                pass


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)