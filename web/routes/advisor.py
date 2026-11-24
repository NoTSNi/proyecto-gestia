#!/usr/bin/env python3
"""
GESTIA Web - Advisor routes.
"""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

router = APIRouter()


async def render(template_name: str, request: Request, **context) -> HTMLResponse:
    """Helper to render template using app's render_template."""
    render_fn = request.app.state.render_template
    context = {"request": request, **context}
    return await render_fn(template_name, context)


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Advisor dashboard."""
    return await render(
        "advisor_dashboard.html",
        request,
        user_initials="AG",
        user_name="Ana García",
        user_role="Asesora Senior",
    )


@router.get("/clientes", response_class=HTMLResponse)
async def clientes(request: Request):
    """Advisor clients list."""
    return await render(
        "advisor_clientes.html",
        request,
        user_initials="AG",
        user_name="Ana García",
        user_role="Asesora Senior",
    )


@router.get("/tareas", response_class=HTMLResponse)
async def tareas(request: Request):
    """Advisor tasks page."""
    return await render(
        "advisor_tareas.html",
        request,
        user_initials="AG",
        user_name="Ana García",
        user_role="Asesora Senior",
    )


@router.get("/documentos", response_class=HTMLResponse)
async def documentos(request: Request):
    """Advisor documents page."""
    return await render(
        "advisor_documentos.html",
        request,
        user_initials="AG",
        user_name="Ana García",
        user_role="Asesora Senior",
    )


@router.get("/calendario", response_class=HTMLResponse)
async def calendario(request: Request):
    """Advisor calendar page."""
    return await render(
        "advisor_calendario.html",
        request,
        user_initials="AG",
        user_name="Ana García",
        user_role="Asesora Senior",
    )


@router.get("/comunicaciones", response_class=HTMLResponse)
async def comunicaciones(request: Request):
    """Advisor communications page."""
    return await render(
        "advisor_comunicaciones.html",
        request,
        user_initials="AG",
        user_name="Ana García",
        user_role="Asesora Senior",
    )


@router.get("/reportes", response_class=HTMLResponse)
async def reportes(request: Request):
    """Advisor reports page."""
    return await render(
        "advisor_reportes.html",
        request,
        user_initials="AG",
        user_name="Ana García",
        user_role="Asesora Senior",
    )
