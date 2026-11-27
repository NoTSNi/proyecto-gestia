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
    # Fase F: alertas proactivas de beneficios fiscales por empresa
    from web.services.beneficios import detectar_beneficios_todas
    alertas = await detectar_beneficios_todas(empresas)
    return await request.app.state.render_template(
        "advisor_dashboard.html",
        {
            "request": request, "user": user,
            "user_initials": _initials(user["full_name"]),
            "user_name": user["full_name"], "user_role": _role_label(user["rol"]),
            "empresas": empresas, "usuarios": usuarios, "rol": user["rol"],
            "alertas_beneficios": alertas,
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
    telefono: str = Form(""),
    movil: str = Form(""),
    email_contacto: str = Form(""),
    whatsapp: str = Form(""),
    web: str = Form(""),
    persona_contacto: str = Form(""),
):
    await get_current_user(request)  # requiere auth
    eid = await database.crear_empresa({
        "nif": nif.strip(), "nombre": nombre.strip(),
        "nombre_comercial": nombre_comercial.strip() or None,
        "regimen_iva": regimen_iva, "cnae": cnae.strip() or None,
        "direccion": direccion.strip() or None, "municipio": municipio.strip() or None,
        "provincia": provincia.strip() or None,
        "telefono": telefono.strip() or None, "movil": movil.strip() or None,
        "email_contacto": email_contacto.strip() or None, "whatsapp": whatsapp.strip() or None,
        "web": web.strip() or None, "persona_contacto": persona_contacto.strip() or None,
    })
    # Generar calendario de obligaciones base (303/111/TC1 según régimen)
    await database.generar_obligaciones(eid)
    # Fase G: automatización n8n al dar de alta un cliente
    from web.services.comms import PORTAL
    await PORTAL.notificar_n8n(
        eid, "cliente_nuevo",
        {"nif": nif.strip(), "nombre": nombre.strip(), "cnae": cnae.strip(),
         "tenant_id": eid},
        usuario=request.cookies.get("gestia_token") or "asesor",
    )
    return RedirectResponse(url="/advisor/clientes", status_code=303)


@router.get("/clientes/{tenant_id}/editar", response_class=HTMLResponse)
async def editar_cliente_page(request: Request, tenant_id: str):
    user = await get_current_user(request)
    empresa = await database.get_empresa(tenant_id)
    if not empresa:
        return RedirectResponse(url="/advisor/clientes", status_code=303)
    return await request.app.state.render_template(
        "advisor_empresa_editar.html",
        {
            "request": request, "user": user,
            "user_initials": _initials(user["full_name"]),
            "user_name": user["full_name"], "user_role": _role_label(user["rol"]),
            "empresa": empresa, "rol": user["rol"],
        },
    )


@router.post("/clientes/{tenant_id}/editar")
async def editar_cliente(
    request: Request,
    tenant_id: str,
    nif: str = Form(...),
    nombre: str = Form(...),
    nombre_comercial: str = Form(""),
    regimen_iva: str = Form("general"),
    periodicidad_iva: str = Form("trimestral"),
    cnae: str = Form(""),
    direccion: str = Form(""),
    municipio: str = Form(""),
    provincia: str = Form(""),
    estado: str = Form("activa"),
    telefono: str = Form(""),
    movil: str = Form(""),
    email_contacto: str = Form(""),
    whatsapp: str = Form(""),
    web: str = Form(""),
    persona_contacto: str = Form(""),
):
    await get_current_user(request)
    await database.actualizar_empresa(tenant_id, {
        "nif": nif.strip(), "nombre": nombre.strip(),
        "nombre_comercial": nombre_comercial.strip() or None,
        "regimen_iva": regimen_iva, "periodicidad_iva": periodicidad_iva,
        "cnae": cnae.strip() or None, "direccion": direccion.strip() or None,
        "municipio": municipio.strip() or None, "provincia": provincia.strip() or None,
        "estado": estado,
        "telefono": telefono.strip() or None, "movil": movil.strip() or None,
        "email_contacto": email_contacto.strip() or None, "whatsapp": whatsapp.strip() or None,
        "web": web.strip() or None, "persona_contacto": persona_contacto.strip() or None,
    })
    return RedirectResponse(url="/advisor/clientes", status_code=303)


@router.post("/clientes/{tenant_id}/baja")
async def baja_cliente(request: Request, tenant_id: str):
    """Baja lógica de la empresa (se conserva el histórico)."""
    await get_current_user(request)
    await database.cambiar_estado_empresa(tenant_id, "baja")
    return RedirectResponse(url="/advisor/clientes", status_code=303)


@router.post("/clientes/{tenant_id}/reactivar")
async def reactivar_cliente(request: Request, tenant_id: str):
    await get_current_user(request)
    await database.cambiar_estado_empresa(tenant_id, "activa")
    return RedirectResponse(url="/advisor/clientes", status_code=303)


# ---------------------------------------------------------------------------
# GESTIÓN DE USUARIOS (Fase B)
# ---------------------------------------------------------------------------

@router.get("/usuarios", response_class=HTMLResponse)
async def usuarios(request: Request):
    user = await get_current_user(request)
    lista = await database.list_usuarios()
    empresas = await database.list_empresas()
    # enriquecer con nombre de empresa
    emp_map = {e["id"]: e["nombre"] for e in empresas}
    for u in lista:
        u["empresa_nombre"] = emp_map.get(u.get("tenant_id"), "Asesoría")
    return await request.app.state.render_template(
        "advisor_usuarios.html",
        {
            "request": request, "user": user,
            "user_initials": _initials(user["full_name"]),
            "user_name": user["full_name"], "user_role": _role_label(user["rol"]),
            "usuarios": lista, "empresas": empresas, "rol": user["rol"],
        },
    )


@router.post("/usuarios/nuevo")
async def crear_usuario(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    full_name: str = Form(...),
    rol: str = Form("cliente_titular"),
    tenant_id: str = Form(""),
):
    await get_current_user(request)
    await database.crear_usuario(
        email=email, password=password, full_name=full_name,
        rol=rol, tenant_id=tenant_id or None,
    )
    return RedirectResponse(url="/advisor/usuarios", status_code=303)


@router.post("/usuarios/{usuario_id}/editar")
async def editar_usuario(
    request: Request,
    usuario_id: str,
    full_name: str = Form(...),
    rol: str = Form(...),
):
    await get_current_user(request)
    await database.actualizar_usuario(usuario_id, full_name=full_name, rol=rol)
    return RedirectResponse(url="/advisor/usuarios", status_code=303)


@router.post("/usuarios/{usuario_id}/estado")
async def estado_usuario(request: Request, usuario_id: str, activo: str = Form("1")):
    """Activa/desactiva un usuario (baja lógica)."""
    await get_current_user(request)
    await database.cambiar_estado_usuario(usuario_id, activo == "1")
    return RedirectResponse(url="/advisor/usuarios", status_code=303)


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
    from web.services.comms import PORTAL
    estado = PORTAL.estado()
    registros = await database.list_comunicaciones()
    empresas = await database.list_empresas()
    # destinos disponibles: email de contacto de cada empresa + usuario admin
    return await request.app.state.render_template(
        "advisor_comunicaciones.html",
        {
            "request": request, "user": user,
            "user_initials": _initials(user["full_name"]),
            "user_name": user["full_name"], "user_role": _role_label(user["rol"]),
            "estado_canales": estado, "registros": registros,
            "empresas": empresas, "rol": user["rol"],
        },
    )


@router.post("/comunicaciones/enviar", response_class=HTMLResponse)
async def comunicaciones_enviar(request: Request, canal: str = Form(...),
                                destino: str = Form(...), asunto: str = Form(""),
                                cuerpo: str = Form(...)):
    """Envía una comunicación al canal elegido (email/whatsapp/n8n) y registra."""
    user = await get_current_user(request)
    from web.services.comms import PORTAL
    if canal == "whatsapp":
        res = await PORTAL.enviar_whatsapp("sistema", destino, cuerpo, user["full_name"])
    elif canal == "n8n":
        import json
        try:
            payload = json.loads(cuerpo)
        except Exception:
            payload = {"nota": cuerpo}
        res = await PORTAL.notificar_n8n("sistema", asunto or "evento", payload,
                                         user["full_name"])
    else:  # email por defecto
        res = await PORTAL.enviar_email("sistema", destino, asunto or "GESTIA",
                                        cuerpo, user["full_name"])
    registros = await database.list_comunicaciones()
    empresas = await database.list_empresas()
    estado = PORTAL.estado()
    return await request.app.state.render_template(
        "advisor_comunicaciones.html",
        {
            "request": request, "user": user,
            "user_initials": _initials(user["full_name"]),
            "user_name": user["full_name"], "user_role": _role_label(user["rol"]),
            "estado_canales": estado, "registros": registros,
            "empresas": empresas, "rol": user["rol"],
            "envio_resultado": res, "envio_canal": canal,
        },
    )


@router.get("/recordatorios", response_class=HTMLResponse)
async def recordatorios_page(request: Request):
    """Panel de recordatorios: vista previa (sin enviar) + botón de envío."""
    user = await get_current_user(request)
    from web.services.recordatorios import recordatorios_todas
    # Vista previa: calcular sin enviar (muestra qué tocaría)
    resumen = await recordatorios_todas(enviar=False)
    return await request.app.state.render_template(
        "advisor_recordatorios.html",
        {
            "request": request, "user": user,
            "user_initials": _initials(user["full_name"]),
            "user_name": user["full_name"], "user_role": _role_label(user["rol"]),
            "resumen": resumen, "rol": user["rol"], "ejecutado": False,
        },
    )


@router.post("/recordatorios/enviar", response_class=HTMLResponse)
async def recordatorios_enviar(request: Request):
    """Ejecuta los recordatorios por email a todas las empresas."""
    user = await get_current_user(request)
    from web.services.recordatorios import recordatorios_todas
    resumen = await recordatorios_todas(enviar=True)
    return await request.app.state.render_template(
        "advisor_recordatorios.html",
        {
            "request": request, "user": user,
            "user_initials": _initials(user["full_name"]),
            "user_name": user["full_name"], "user_role": _role_label(user["rol"]),
            "resumen": resumen, "rol": user["rol"], "ejecutado": True,
        },
    )


@router.get("/reportes", response_class=HTMLResponse)
async def reportes(request: Request):
    user = await get_current_user(request)
    return await _simple_render(request, user, "advisor_reportes.html")


# ---------------------------------------------------------------------------
# SEGURIDAD (Fase E)
# ---------------------------------------------------------------------------

@router.get("/seguridad", response_class=HTMLResponse)
async def seguridad_panel(request: Request):
    """Panel de seguridad: audit log + lanzar monitor."""
    user = await get_current_user(request)
    from web.services.monitor_seguridad import monitor_seguridad
    registros = await database.list_audit_seguridad(limit=200)
    informe = await monitor_seguridad(dias=1, persistence=False)
    return await request.app.state.render_template(
        "advisor_seguridad.html",
        {
            "request": request, "user": user,
            "user_initials": _initials(user["full_name"]),
            "user_name": user["full_name"], "user_role": _role_label(user["rol"]),
            "rol": user["rol"],
            "informe": informe,
            "registros": registros,
        },
    )


@router.post("/seguridad/escanear")
async def seguridad_escanear(request: Request):
    """Lanza un barrido de seguridad y guarda el resultado en el audit log."""
    user = await get_current_user(request)
    from web.services.monitor_seguridad import monitor_seguridad
    informe = await monitor_seguridad(dias=1, persistence=True, ip=request.client.host if request.client else None)
    return RedirectResponse(url="/advisor/seguridad", status_code=303)


@router.post("/usuarios/{usuario_id}/desbloquear")
async def desbloquear_usuario(request: Request, usuario_id: str):
    """Desbloquea una cuenta (deshace el bloqueo por anti-brute-force)."""
    user = await get_current_user(request)
    await database.bloquear_usuario(usuario_id, bloquear=False)
    await database.auditar_seguridad(
        "usuario_desbloqueado", f"Cuenta desbloqueada por {user['email']}",
        usuario=user["email"], ip=request.client.host if request.client else None, severidad="media",
    )
    return RedirectResponse(url="/advisor/usuarios", status_code=303)


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
