#!/usr/bin/env python3
"""
GESTIA Web - Client routes.
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
    """Client dashboard."""
    return await render(
        "client_dashboard.html",
        request,
        user_initials="TS",
        user_name="Tech Solutions SL",
        user_role="Cliente - Administrador",
    )


@router.get("/documentos", response_class=HTMLResponse)
async def documentos(request: Request):
    """Client documents page."""
    return await render(
        "client_documentos.html",
        request,
        user_initials="TS",
        user_name="Tech Solutions SL",
        user_role="Cliente - Administrador",
    )


@router.get("/facturas", response_class=HTMLResponse)
async def facturas(request: Request):
    """Client invoices page."""
    return await render(
        "client_facturas.html",
        request,
        user_initials="TS",
        user_name="Tech Solutions SL",
        user_role="Cliente - Administrador",
    )


@router.get("/impuestos", response_class=HTMLResponse)
async def impuestos(request: Request):
    """Client taxes page."""
    return await render(
        "client_impuestos.html",
        request,
        user_initials="TS",
        user_name="Tech Solutions SL",
        user_role="Cliente - Administrador",
    )


@router.get("/nominas", response_class=HTMLResponse)
async def nominas(request: Request):
    """Client payroll page."""
    return await render(
        "client_nominas.html",
        request,
        user_initials="TS",
        user_name="Tech Solutions SL",
        user_role="Cliente - Administrador",
    )


@router.get("/calendario", response_class=HTMLResponse)
async def calendario(request: Request):
    """Client calendar page."""
    return await render(
        "client_calendario.html",
        request,
        user_initials="TS",
        user_name="Tech Solutions SL",
        user_role="Cliente - Administrador",
    )


@router.get("/mensajes", response_class=HTMLResponse)
async def mensajes(request: Request):
    """Client messages page."""
    return await render(
        "client_mensajes.html",
        request,
        user_initials="TS",
        user_name="Tech Solutions SL",
        user_role="Cliente - Administrador",
    )
