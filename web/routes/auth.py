"""GESTIA Web - Auth routes (login/logout con cookie JWT)."""

from __future__ import annotations

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from web import database
from web.database import verify_password
from web.security import COOKIE_NAME, create_access_token, role_label

router = APIRouter()


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return await request.app.state.render_template(
        "auth/login.html",
        {
            "request": request,
            "error": None,
            "title": "Iniciar Sesión - GESTIA",
        },
    )


@router.post("/login")
async def login_post(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
):
    user = await database.get_usuario_by_email(email.strip().lower())
    if not user or not user.get("activo") or not verify_password(password, user["password_hash"]):
        return await request.app.state.render_template(
            "auth/login.html",
            {
                "request": request,
                "error": "Credenciales incorrectas. Inténtalo de nuevo.",
                "title": "Iniciar Sesión - GESTIA",
            },
        )

    token = create_access_token(user)
    # Redirigir según rol: asesor/admin → advisor, cliente → client
    if user["rol"] in ("superadmin", "admin_asesoria", "asesor_contable", "asesor_mercantil",
                       "asesor_administrativo", "asesor_personal"):
        redirect_url = "/advisor/dashboard"
    else:
        redirect_url = "/client/dashboard"

    response = RedirectResponse(url=redirect_url, status_code=303)
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 8,  # 8 horas
        path="/",
    )
    return response


@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/auth/login", status_code=303)
    response.delete_cookie(COOKIE_NAME, path="/")
    return response
