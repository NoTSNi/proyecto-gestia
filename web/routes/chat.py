"""GESTIA Web - Chat con agentes (Fase A)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from web.security import get_current_user, require_roles
from web.services.advisory import consultar_gestia

ADVISOR_ROLES = ("superadmin", "admin_asesoria", "asesor_contable", "asesor_mercantil",
                 "asesor_administrativo", "asesor_personal")
router = APIRouter(dependencies=[Depends(require_roles(*ADVISOR_ROLES))])


def _initials(name: str) -> str:
    parts = [p for p in name.split() if p]
    if not parts:
        return "??"
    return "".join(p[0].upper() for p in parts[:2])


@router.get("/chat", response_class=HTMLResponse)
async def chat_page(request: Request):
    user = await get_current_user(request)
    return await request.app.state.render_template(
        "advisor_chat.html",
        {
            "request": request, "user": user,
            "user_initials": _initials(user["full_name"]),
            "user_name": user["full_name"], "user_role": "Asesor",
            "rol": user["rol"],
        },
    )


@router.post("/chat")
async def chat_ask(request: Request):
    """Handle a chat message and return the response as HTML partial for HTMX."""
    user = await get_current_user(request)
    form = await request.form()
    query_val = (form.get("query") or "")
    query = str(query_val).strip()
    tenant_id: str | None = user.get("tenant_id")

    if not query:
        return HTMLResponse(
            "<p class='text-text-tertiary text-sm'>Escribe una consulta para GESTIA.</p>"
        )

    if not tenant_id:
        return HTMLResponse(
            "<p class='text-danger-400 text-sm'>Tu usuario no tiene empresa asignada. Contacta con el administrador.</p>"
        )

    result = await consultar_gestia(query, tenant_id=tenant_id, user_id=user["id"])

    response_text = result["response"]
    success = result["success"]

    # Sanitizar: todo el contenido es HTML escapado por Jinja2 en la plantilla
    return await request.app.state.render_template(
        "partials/_chat_answer.html",
        {
            "request": request,
            "query": query,
            "answer": response_text,
            "success": success,
            "agent": result["agent"],
            "routing_confidence": result.get("routing_confidence"),
            "strategy": result.get("strategy"),
            "specialists": result.get("specialists_consulted", []),
        },
    )