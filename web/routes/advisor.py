"""GESTIA Web - Rutas del Panel Asesor/Superadmin (multi-tenant)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from web import database
from web.security import get_current_user, require_roles

ADVISOR_ROLES = ("superadmin", "admin_asesoria", "asesor_contable", "asesor_mercantil",
                 "asesor_administrativo", "asesor_personal")

require_asesor = require_roles(*ADVISOR_ROLES)

router = APIRouter(dependencies=[Depends(require_asesor)])


def _initials(name: str) -> str:
    parts = [p for p in name.split() if p]
    if not parts:
        return "??"
    return "".join(p[0].upper() for p in parts[:2])


def _role_label(rol: str) -> str:
    from web.security import role_label
    return role_label(rol)


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    user = await get_current_user(request)
    empresas = await database.list_empresas()
    usuarios = await database.list_usuarios()
    return await request.app.state.render_template(
        "advisor_dashboard.html",
        {
            "request": request, "user": user,
            "user_initials": _initials(user["full_name"]),
            "user_name": user["full_name"], "user_role": _role_label(user["rol"]),
            "empresas": empresas, "usuarios": usuarios, "rol": user["rol"],
            "onboarding": True,
        },
    )


@router.get("/clientes", response_class=HTMLResponse)
async def clientes(request: Request):
    user = await get_current_user(request)
    empresas = await database.list_empresas()
    usuarios = await database.list_usuarios()
    # nº de documentos/usuarios por empresa para la tabla
    conteo = {}
    for emp in empresas:
        emp_id = emp["id"]
        conteo[emp_id] = {
            "usuarios": sum(1 for u in usuarios if u.get("tenant_id") == emp_id),
            "documentos": len(await database.list_documentos(emp_id)),
        }
    return await request.app.state.render_template(
        "advisor_clientes.html",
        {
            "request": request, "user": user,
            "user_initials": _initials(user["full_name"]),
            "user_name": user["full_name"], "user_role": _role_label(user["rol"]),
            "empresas": empresas, "conteo": conteo, "usuarios": usuarios, "rol": user["rol"],
        },
    )


@router.post("/clientes/nuevo")
async def crear_cliente(
    request: Request,
    nif: str = Form(...),
    nombre: str = Form(...),
    nombre_comercial: str = Form(""),
    regimen_iva: str = Form("general"),
    cnae: str = Form(""),
    direccion: str = Form(""),
    municipio: str = Form(""),
    provincia: str = Form(""),
):
    await get_current_user(request)  # requiere auth
    await database.crear_empresa({
        "nif": nif.strip(), "nombre": nombre.strip(),
        "nombre_comercial": nombre_comercial.strip() or None,
        "regimen_iva": regimen_iva, "cnae": cnae.strip() or None,
        "direccion": direccion.strip() or None, "municipio": municipio.strip() or None,
        "provincia": provincia.strip() or None,
    })
    return RedirectResponse(url="/advisor/clientes", status_code=303)


@router.get("/tareas", response_class=HTMLResponse)
async def tareas(request: Request):
    user = await get_current_user(request)
    return await _simple_render(request, user, "advisor_tareas.html")


@router.get("/documentos", response_class=HTMLResponse)
async def documentos(request: Request):
    user = await get_current_user(request)
    empresas = await database.list_empresas()
    docs_todas = []
    for emp in empresas:
        for d in await database.list_documentos(emp["id"]):
            docs_todas.append({**d, "empresa_nombre": emp["nombre"]})
    return await request.app.state.render_template(
        "advisor_documentos.html",
        {
            "request": request, "user": user,
            "user_initials": _initials(user["full_name"]),
            "user_name": user["full_name"], "user_role": _role_label(user["rol"]),
            "documentos": docs_todas, "rol": user["rol"],
        },
    )


@router.get("/calendario", response_class=HTMLResponse)
async def calendario(request: Request):
    user = await get_current_user(request)
    empresas = await database.list_empresas()
    eventos = []
    for emp in empresas:
        for e in await database.list_eventos(emp["id"]):
            eventos.append({**e, "empresa_nombre": emp["nombre"]})
    return await request.app.state.render_template(
        "advisor_calendario.html",
        {
            "request": request, "user": user,
            "user_initials": _initials(user["full_name"]),
            "user_name": user["full_name"], "user_role": _role_label(user["rol"]),
            "eventos": eventos, "rol": user["rol"],
        },
    )


@router.get("/comunicaciones", response_class=HTMLResponse)
async def comunicaciones(request: Request):
    user = await get_current_user(request)
    return await _simple_render(request, user, "advisor_comunicaciones.html")


@router.get("/reportes", response_class=HTMLResponse)
async def reportes(request: Request):
    user = await get_current_user(request)
    return await _simple_render(request, user, "advisor_reportes.html")


async def _simple_render(request: Request, user: dict, template_name: str):
    return await request.app.state.render_template(
        template_name,
        {
            "request": request, "user": user,
            "user_initials": _initials(user["full_name"]),
            "user_name": user["full_name"], "user_role": _role_label(user["rol"]),
            "rol": user["rol"],
        },
    )
