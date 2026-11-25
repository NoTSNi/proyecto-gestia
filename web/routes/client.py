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
    anio = request.query_params.get("anio")
    mes = request.query_params.get("mes")
    query = (request.query_params.get("q") or "").strip()
    if query:
        archivos = await database.buscar_archivos(empresa["id"], query)
    else:
        archivos = await database.list_archivos(empresa["id"], anio=anio, mes=mes)
    docs = await database.list_documentos(empresa["id"])
    grupos = await database.list_anios_meses(empresa["id"])
    return await request.app.state.render_template(
        "client_documentos.html",
        {
            "request": request, "user": user, "empresa": empresa,
            "user_initials": _initials(empresa["nombre"]),
            "user_name": empresa["nombre"], "user_role": _role_label(user["rol"]),
            "documentos": docs, "archivos": archivos, "grupos": grupos,
            "anio": anio, "mes": mes, "query": query, "rol": user["rol"],
        },
    )


@router.post("/documentos/subir")
async def subir_documento(request: Request):
    """Sube un documento: cuarentena + extracción + indexado (Fase D)."""
    from web.services.vault import ArchivoRechazado, ingestar_archivo

    user, empresa = await _get_tenant_or_401(request)
    form = await request.form()
    archivo = form.get("archivo")
    if archivo is None or not getattr(archivo, "filename", ""):
        return RedirectResponse(url="/client/documentos?error=sinarchivo", status_code=303)

    contenido = await archivo.read()
    try:
        await ingestar_archivo(
            tenant_id=empresa["id"],
            nombre_original=archivo.filename,
            contenido=contenido,
            subido_por=user["email"],
        )
        return RedirectResponse(url="/client/documentos?ok=subido", status_code=303)
    except ArchivoRechazado as e:
        return RedirectResponse(url=f"/client/documentos?error={e}", status_code=303)


@router.get("/facturas", response_class=HTMLResponse)
async def facturas(request: Request):
    user, empresa = await _get_tenant_or_401(request)
    docs = await database.list_documentos(empresa["id"])
    facturas_old = [d for d in docs if d["tipo"] in ("factura_recibida", "factura_emitida")]
    pendientes = await database.list_facturas(empresa["id"], estado="pendiente_validacion")
    validadas = await database.list_facturas(empresa["id"], estado="validada")
    log = await database.list_log_validaciones(empresa["id"])
    return await request.app.state.render_template(
        "client_facturas.html",
        {
            "request": request, "user": user, "empresa": empresa,
            "user_initials": _initials(empresa["nombre"]),
            "user_name": empresa["nombre"], "user_role": _role_label(user["rol"]),
            "facturas": facturas_old, "pendientes": pendientes, "validadas": validadas,
            "log": log, "rol": user["rol"],
        },
    )


@router.post("/facturas/subir")
async def subir_factura(request: Request):
    """Sube una factura manualmente (datos a validar por el cliente)."""
    user, empresa = await _get_tenant_or_401(request)
    form = await request.form()
    datos = {
        "emisor": str(form.get("emisor") or "").strip(),
        "nif_emisor": str(form.get("nif_emisor") or "").strip(),
        "fecha_factura": str(form.get("fecha_factura") or "").strip(),
        "numero": str(form.get("numero") or "").strip(),
        "concepto": str(form.get("concepto") or "").strip(),
        "base": str(form.get("base") or "").strip(),
        "iva": str(form.get("iva") or "").strip(),
        "total": str(form.get("total") or "").strip(),
    }
    if not datos.get("emisor") and not datos.get("concepto"):
        return RedirectResponse(url="/client/facturas?error=vacio", status_code=303)
    await database.crear_factura(
        empresa["id"], datos, creado_por=user["email"],
        archivo_original=str(form.get("archivo_nombre") or "").strip() or None,
    )
    return RedirectResponse(url="/client/facturas", status_code=303)


@router.post("/facturas/{factura_id}/validar")
async def validar_factura_route(request: Request, factura_id: str):
    """El cliente valida (o corrige y valida) una factura pendiente."""
    user, empresa = await _get_tenant_or_401(request)
    form = await request.form()
    # Campos que el cliente puede corregir antes de validar
    cambios = {}
    for campo in ("emisor", "nif_emisor", "fecha_factura", "numero", "concepto", "base", "iva", "total"):
        val = str(form.get(campo) or "").strip()
        if val:
            cambios[campo] = val
    await database.validar_factura(factura_id, empresa["id"], user["email"], cambios=cambios or None)
    return RedirectResponse(url="/client/facturas", status_code=303)


@router.get("/facturas/descargar")
async def descargar_excel(request: Request):
    """Descarga el Excel de la empresa (facturas + log)."""
    from fastapi.responses import Response
    user, empresa = await _get_tenant_or_401(request)
    contenido = await database.exportar_excel_empresa(empresa["id"])
    nombre = f"GESTIA_{empresa['nif']}.xlsx"
    return Response(
        content=contenido,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
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
