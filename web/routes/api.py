#!/usr/bin/env python3
"""
GESTIA Web - API routes for HTMX interactions.
"""
from __future__ import annotations

from fastapi import APIRouter, Request, Query
from fastapi.responses import HTMLResponse, JSONResponse

router = APIRouter()


async def render(template_name: str, request: Request, **context) -> HTMLResponse:
    """Helper to render template using app's render_template."""
    render_fn = request.app.state.render_template
    context = {"request": request, **context}
    return await render_fn(template_name, context)


@router.get("/clients", response_class=HTMLResponse)
async def get_clients_dropdown(request: Request):
    """Return client options for dropdown."""
    clients = [
        {"id": "tech-solutions", "name": "Tech Solutions SL", "nif": "B87654321"},
        {"id": "comercial-norte", "name": "Comercial Norte SA", "nif": "A12345678"},
        {"id": "inmobiliaria-sur", "name": "Inmobiliaria Sur SL", "nif": "B98765432"},
        {"id": "hosteleria-este", "name": "Hostelería Este SL", "nif": "B55555555"},
        {"id": "constructora-oeste", "name": "Constructora Oeste SA", "nif": "A99999999"},
    ]
    return await render("partials/client_options.html", request, clients=clients)


@router.get("/client/{client_id}/stats")
async def get_client_stats(client_id: str):
    """Get stats for a specific client."""
    stats = {
        "tech-solutions": {"iva": "1.250€", "irpf": "3.420€", "ss": "8.750€", "alerts": 2},
        "comercial-norte": {"iva": "URGENTE", "irpf": "2.100€", "ss": "12.300€", "alerts": 5},
        "inmobiliaria-sur": {"iva": "OK", "irpf": "1.800€", "ss": "5.600€", "alerts": 0},
    }
    return stats.get(client_id, {})


@router.get("/notifications")
async def get_notifications():
    """Get recent notifications."""
    return [
        {"id": 1, "type": "warning", "message": "Modelo 303 vence en 2 días", "client": "Comercial Norte SA"},
        {"id": 2, "type": "info", "message": "Nuevo documento subido", "client": "Tech Solutions SL"},
        {"id": 3, "type": "success", "message": "Depósito cuentas completado", "client": "Inmobiliaria Sur SL"},
    ]


@router.post("/documents/upload")
async def upload_document(request: Request):
    """Handle document upload via HTMX."""
    form = await request.form()
    file = form.get("file")
    client_id = form.get("client_id")
    
    # Simulate processing
    return HTMLResponse(
        f'<div class="p-4 bg-green-50 border border-green-200 rounded-lg">'
        f'✅ Documento "{file.filename}" subido correctamente para {client_id}'
        f'</div>'
    )


@router.get("/tasks/upcoming")
async def get_upcoming_tasks(days: int = Query(7)):
    """Get upcoming tasks for dashboard."""
    tasks = [
        {"id": 1, "title": "Modelo 303 - Comercial Norte SA", "due": "20/04", "urgent": True},
        {"id": 2, "title": "TC1/TC2 - Tech Solutions SL", "due": "30/04", "urgent": False},
        {"id": 3, "title": "Nómina abril - Hostelería Este", "due": "25/04", "urgent": False},
    ]
    return {"tasks": tasks}


@router.get("/health")
async def health():
    return {"status": "ok"}


# ---- N8N Webhook Endpoints ----

@router.post("/gestia/ingest")
async def n8n_ingest_document(request: Request):
    """Handle n8n document ingestion webhook."""
    form = await request.form()
    document_id = form.get("document_id")
    tenant_id = form.get("tenant_id")
    object_key = form.get("object_key")
    filename = form.get("filename")
    
    # Process the document ingestion
    # In production, this would trigger OCR, embeddings, vector DB storage, etc.
    print(f"📄 Document ingestion webhook: document_id={document_id}, tenant_id={tenant_id}")
    
    # Return success response
    return HTMLResponse(
        f'<div class="p-4 bg-green-50 border border-green-200 rounded-lg">'
        f'✅ Documento "{filename}" procesado para {tenant_id}'
        f'</div>'
    )


@router.post("/gestia/notify")
async def n8n_notify(request: Request):
    """Handle n8n notification webhook."""
    form = await request.form()
    notification_id = form.get("notification_id")
    canal = form.get("canal")
    destinatario = form.get("destinatario_tipo")
    asunto = form.get("asunto")
    cuerpo = form.get("cuerpo")
    
    # Route notification by channel
    print(f"📧 Notification webhook: canal={canal}, asunto={asunto}")
    
    # Return success response
    return HTMLResponse(
        f'<div class="p-4 bg-blue-50 border border-blue-500/30 rounded-lg">'
        f'📧 Notificación encolada: {canal} - {asunto}'
        f'</div>'
    )


@router.post("/gestia/calendar")
async def n8n_calendar(request: Request):
    """Handle n8n calendar webhook."""
    form = await request.form()
    tenant_id = form.get("tenant_id")
    anio = form.get("anio")
    eventos = form.get("eventos")
    
    # Process calendar events
    print(f"📅 Calendar webhook: tenant_id={tenant_id}, anio={anio}, eventos={len(eventos) if eventos else 0} eventos")
    
    # Return success response
    return HTMLResponse(
        f'<div class="p-4 bg-purple-50 border border-purple-500/30 rounded-lg">'
        f'📅 Eventos calendarios procesados para {tenant_id} ({anio})'
        f'</div>'
    )


# Export for routes
__all__ = ["router"]
