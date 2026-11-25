"""GESTIA Web - Rutas del Portal Cliente (multi-tenant)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from web import database
from web.security import get_current_user, require_roles

router = APIRouter()

# Roles de cliente (y asesor con acceso a los portales de sus clientes)
CLIENT_ROLES = ("cliente_titular", "cliente_empleado", "superadmin", "admin_asesoria",
                "asesor_contable", "asesor_mercantil", "asesor_administrativo", "asesor_personal")


def _initials(name: str) -> str:
    parts = [p for p in name.split() if p]
    if not parts:
        return "??"
    return "".join(p[0].upper() for p in parts[:2])


def _role_label(rol: str) -> str:
    from web.security import role_label
    return role_label(rol)


async def _get_tenant_or_401(request: Request):
    """Carga la empresa del usuario autenticado."""
    user = await get_current_user(request)
    tenant_id = user.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=404, detail="Usuario sin empresa asignada")
    empresa = await database.get_empresa(tenant_id)
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    return user, empresa


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    user, empresa = await _get_tenant_or_401(request)
    docs = await database.list_documentos(empresa["id"])
    notifs = await database.list_notificaciones(empresa["id"])
    return await request.app.state.render_template(
        "client_dashboard.html",
        {
            "request": request,
            "user": user,
            "empresa": empresa,
            "user_initials": _initials(empresa["nombre"]),
            "user_name": empresa["nombre"],
            "user_role": _role_label(user["rol"]),
            "documentos": docs,
            "notificaciones": notifs,
            "rol": user["rol"],
        },
    )


@router.get("/documentos", response_class=HTMLResponse)
async def documentos(request: Request):
    user, empresa = await _get_tenant_or_401(request)
    docs = await database.list_documentos(empresa["id"])
    return await request.app.state.render_template(
        "client_documentos.html",
        {
            "request": request, "user": user, "empresa": empresa,
            "user_initials": _initials(empresa["nombre"]),
            "user_name": empresa["nombre"], "user_role": _role_label(user["rol"]),
            "documentos": docs, "rol": user["rol"],
        },
    )


@router.get("/facturas", response_class=HTMLResponse)
async def facturas(request: Request):
    user, empresa = await _get_tenant_or_401(request)
    docs = await database.list_documentos(empresa["id"])
    facturas = [d for d in docs if d["tipo"] in ("factura_recibida", "factura_emitida")]
    return await request.app.state.render_template(
        "client_facturas.html",
        {
            "request": request, "user": user, "empresa": empresa,
            "user_initials": _initials(empresa["nombre"]),
            "user_name": empresa["nombre"], "user_role": _role_label(user["rol"]),
            "facturas": facturas, "rol": user["rol"],
        },
    )


@router.get("/impuestos", response_class=HTMLResponse)
async def impuestos(request: Request):
    user, empresa = await _get_tenant_or_401(request)
    docs = await database.list_documentos(empresa["id"])
    imp = [d for d in docs if d["tipo"].startswith("modelo_")]
    return await request.app.state.render_template(
        "client_impuestos.html",
        {
            "request": request, "user": user, "empresa": empresa,
            "user_initials": _initials(empresa["nombre"]),
            "user_name": empresa["nombre"], "user_role": _role_label(user["rol"]),
            "impuestos": imp, "rol": user["rol"],
        },
    )


@router.get("/nominas", response_class=HTMLResponse)
async def nominas(request: Request):
    user, empresa = await _get_tenant_or_401(request)
    docs = await database.list_documentos(empresa["id"])
    nom = [d for d in docs if d["tipo"] in ("nomina", "tc1_tc2", "contrato_laboral")]
    return await request.app.state.render_template(
        "client_nominas.html",
        {
            "request": request, "user": user, "empresa": empresa,
            "user_initials": _initials(empresa["nombre"]),
            "user_name": empresa["nombre"], "user_role": _role_label(user["rol"]),
            "nominas": nom, "rol": user["rol"],
        },
    )


@router.get("/calendario", response_class=HTMLResponse)
async def calendario(request: Request):
    user, empresa = await _get_tenant_or_401(request)
    eventos = await database.list_eventos(empresa["id"])
    return await request.app.state.render_template(
        "client_calendario.html",
        {
            "request": request, "user": user, "empresa": empresa,
            "user_initials": _initials(empresa["nombre"]),
            "user_name": empresa["nombre"], "user_role": _role_label(user["rol"]),
            "eventos": eventos, "rol": user["rol"],
        },
    )


@router.get("/mensajes", response_class=HTMLResponse)
async def mensajes(request: Request):
    user, empresa = await _get_tenant_or_401(request)
    notifs = await database.list_notificaciones(empresa["id"])
    return await request.app.state.render_template(
        "client_mensajes.html",
        {
            "request": request, "user": user, "empresa": empresa,
            "user_initials": _initials(empresa["nombre"]),
            "user_name": empresa["nombre"], "user_role": _role_label(user["rol"]),
            "notificaciones": notifs, "rol": user["rol"],
        },
    )
