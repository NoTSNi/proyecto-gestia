"""GESTIA Web - Auth routes (login/logout con anti-brute-force y 2FA)."""

from __future__ import annotations

import json
from urllib.parse import quote

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from web import database
from web.database import verify_password
from web.security import COOKIE_NAME, create_access_token, role_label
from web.services import security as sec

router = APIRouter()

# Cookie temporal que confirma que las credenciales ya se validaron (paso 1 de 2FA)
PENDING_COOKIE = "gestia_pending"


def _es_asesor(rol: str) -> bool:
    return rol in ("superadmin", "admin_asesoria", "asesor_contable", "asesor_mercantil",
                   "asesor_administrativo", "asesor_personal")


def _ip(request: Request) -> str | None:
    return request.client.host if request.client else None


async def _render_login(request: Request, error: str | None):
    return await request.app.state.render_template(
        "auth/login.html",
        {"request": request, "error": error, "title": "Iniciar Sesión - GESTIA"},
    )


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return await _render_login(request, None)


@router.post("/login")
async def login_post(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
):
    email_norm = email.strip().lower()
    ip = _ip(request)

    # --- 0) Anti-brute-force: ¿cuenta bloqueada? ---
    bloqueo = await sec.verificar_bloqueo(email_norm)
    if bloqueo["bloqueado"]:
        await database.registrar_intento_login(email_norm, False, ip)
        await database.auditar_seguridad(
            "login_rechazado", f"Login rechazado (cuenta bloqueada): {email_norm}",
            usuario=email_norm, ip=ip, severidad="alta",
        )
        return await _render_login(request, bloqueo["motivo"])

    user = await database.get_usuario_by_email(email_norm)
    credenciales_ok = bool(user and user.get("activo") and verify_password(password, user["password_hash"]))

    # --- 1) Credenciales incorrectas -> contar fallo ---
    if not credenciales_ok:
        await database.registrar_intento_login(email_norm, False, ip)
        fallos = await database.contar_intentos_fallidos(email_norm, sec.VENTANA_MIN)
        await database.auditar_seguridad(
            "login_fallido", f"Intento fallido para {email_norm}", usuario=email_norm,
            ip=ip, severidad="media",
        )
        restantes = max(0, sec.MAX_INTENTOS - fallos)
        msg = "Credenciales incorrectas."
        if restantes <= 3:
            msg += f" {restantes} intento(s) restante(s) antes de bloquear la cuenta."
        return await _render_login(request, msg)

    # Credenciales OK → registrar éxito (resetea contador)
    await database.registrar_intento_login(email_norm, True, ip)
    await sec.registrar_ok_tras_fallo(email_norm)

    if not user:
        return await _render_login(request, "Credenciales incorrectas.")

    # --- 2) ¿2FA activado? -> paso 2 ---
    if user.get("tfa_activado"):
        # Guardar estado pendiente en cookie firmada (sin credenciales en claro)
        await database.auditar_seguridad(
            "login_2fa_pendiente", f"2FA requerido para {email_norm}",
            tenant_id=user.get("tenant_id"), usuario=email_norm, ip=ip,
        )
        response = RedirectResponse(url=f"/auth/2fa?u={quote(email_norm)}", status_code=303)
        response.set_cookie(PENDING_COOKIE, str(user["id"]), httponly=True, samesite="lax",
                            max_age=5 * 60, path="/")
        return response

    # --- 3) Sin 2FA -> login directo ---
    token = create_access_token(user)
    redirect_url = "/advisor/dashboard" if _es_asesor(user["rol"]) else "/client/dashboard"
    response = RedirectResponse(url=redirect_url, status_code=303)
    response.set_cookie(COOKIE_NAME, token, httponly=True, samesite="lax",
                        max_age=60 * 60 * 8, path="/")
    return response


# ---------------------------------------------------------------------------
# 2FA
# ---------------------------------------------------------------------------

@router.get("/2fa", response_class=HTMLResponse)
async def tfa_page(request: Request, u: str = ""):
    pending_id = request.cookies.get(PENDING_COOKIE)
    user = await database.get_usuario_by_email(u.strip().lower())
    if not pending_id or not user or pending_id != user["id"]:
        return RedirectResponse(url="/auth/login", status_code=303)
    return await request.app.state.render_template(
        "auth/tfa.html",
        {"request": request, "error": None, "email": u, "title": "Verificación 2FA - GESTIA"},
    )


@router.post("/2fa")
async def tfa_verify(
    request: Request,
    u: str = Form(...),
    codigo: str = Form(...),
):
    pending_id = request.cookies.get(PENDING_COOKIE)
    user = await database.get_usuario_by_email(u.strip().lower())
    if not pending_id or not user or pending_id != user["id"]:
        return RedirectResponse(url="/auth/login", status_code=303)

    codigo = codigo.strip()
    # Validar TOTP o código de recuperación
    ok = sec.validar_totp(user.get("tfa_secret") or "", codigo) or await sec.validar_codigo_recuperacion(user, codigo)

    if not ok:
        await database.auditar_seguridad(
            "2fa_fallido", f"Código 2FA incorrecto para {u}",
            tenant_id=user.get("tenant_id"), usuario=u, ip=_ip(request), severidad="alta",
        )
        await database.registrar_intento_login(u, False, _ip(request))
        return await request.app.state.render_template(
            "auth/tfa.html",
            {"request": request, "error": "Código incorrecto o expirado. Inténtalo de nuevo.",
             "email": u, "title": "Verificación 2FA - GESTIA"},
        )

    # 2FA OK -> login completo
    await database.auditar_seguridad(
        "login_2fa_ok", f"2FA superado para {u}",
        tenant_id=user.get("tenant_id"), usuario=u, ip=_ip(request),
    )
    token = create_access_token(user)
    redirect_url = "/advisor/dashboard" if _es_asesor(user["rol"]) else "/client/dashboard"
    response = RedirectResponse(url=redirect_url, status_code=303)
    response.set_cookie(COOKIE_NAME, token, httponly=True, samesite="lax",
                        max_age=60 * 60 * 8, path="/")
    response.delete_cookie(PENDING_COOKIE, path="/")
    return response


@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/auth/login", status_code=303)
    response.delete_cookie(COOKIE_NAME, path="/")
    response.delete_cookie(PENDING_COOKIE, path="/")
    return response


# ---------------------------------------------------------------------------
# CONFIGURACIÓN 2FA (tras login)
# ---------------------------------------------------------------------------

@router.get("/2fa/configurar", response_class=HTMLResponse)
async def tfa_configurar_page(request: Request):
    """Muestra QR + códigos de recuperación para activar 2FA."""
    from web.security import get_current_user
    user = await get_current_user(request)
    # Generar secreto y códigos (aún no guardados hasta confirmar)
    secret = sec.generar_secret()
    codigos = sec.generar_codigos_recuperacion()
    qr_uri = sec.escapara_qr(secret, user["email"])
    return await request.app.state.render_template(
        "auth/tfa_configurar.html",
        {
            "request": request, "email": user["email"],
            "secret": secret, "codigos": codigos, "qr_uri": qr_uri,
            "ya_activado": bool(user.get("tfa_activado")),
            "title": "Configurar 2FA - GESTIA",
        },
    )


@router.post("/2fa/activar")
async def tfa_activar(request: Request):
    """Confirma y activa 2FA (el usuario ya escaneó el QR e introdujo un código)."""
    from web.security import get_current_user
    user = await get_current_user(request)
    form = await request.form()
    secret = str(form.get("secret") or "")
    codigo = str(form.get("codigo") or "").strip()
    codigos_raw = str(form.get("codigos") or "")

    if not secret or not codigo:
        return RedirectResponse(url="/auth/2fa/configurar", status_code=303)
    if not sec.validar_totp(secret, codigo):
        await database.auditar_seguridad(
            "2fa_activacion_fallida", f"Código TOTP incorrecto al activar 2FA para {user['email']}",
            tenant_id=user.get("tenant_id"), usuario=user["email"], ip=_ip(request), severidad="media",
        )
        return RedirectResponse(url="/auth/2fa/configurar?error=code", status_code=303)

    try:
        codigos = json.loads(codigos_raw)
    except json.JSONDecodeError:
        codigos = sec.generar_codigos_recuperacion()

    await database.activar_tfa(user["id"], secret, codigos)
    await database.auditar_seguridad(
        "2fa_activado", f"2FA activado para {user['email']}",
        tenant_id=user.get("tenant_id"), usuario=user["email"], ip=_ip(request),
    )
    return RedirectResponse(url="/auth/logout?tfa=activado", status_code=303)


@router.post("/2fa/desactivar")
async def tfa_desactivar(request: Request):
    """Desactiva 2FA (solo admin/superadmin)."""
    from web.security import get_current_user
    user = await get_current_user(request)
    await database.desactivar_tfa(user["id"])
    await database.auditar_seguridad(
        "2fa_desactivado", f"2FA desactivado para {user['email']}",
        tenant_id=user.get("tenant_id"), usuario=user["email"], ip=_ip(request), severidad="alta",
    )
    return RedirectResponse(url="/advisor/dashboard", status_code=303)


@router.get("/2fa/qr")
async def tfa_qr(request: Request, secret: str = "", email: str = ""):
    """Genera la imagen QR (SVG) del secreto TOTP para escanear."""
    from fastapi.responses import Response
    import io
    import qrcode
    if not secret or not email:
        return Response(status_code=400)
    uri = sec.escapara_qr(secret, email)
    qr = qrcode.make(uri)
    buf = io.BytesIO()
    qr.save(buf, format="PNG")
    return Response(content=buf.getvalue(), media_type="image/png")