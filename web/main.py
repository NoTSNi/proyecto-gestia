#!/usr/bin/env python3
"""GESTIA Web - Main entry point."""

from __future__ import annotations

from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from web import database
from web.routes import advisor, api, auth, client
from web.security import COOKIE_NAME, decode_token


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Inicializar BD SQLite + seed demo (idempotente)
    await database.init_db()
    app.state.db_ready = True
    yield


app = FastAPI(
    title="GESTIA Web",
    description="Interfaz web para GESTIA - Gestoría Inteligente (multi-tenant)",
    version="0.2.0",
    lifespan=lifespan,
)

# Static files
app.mount("/static", StaticFiles(directory="web/static"), name="static")


# ---------------------------------------------------------------------------
# Jinja2 (sin cache para evitar el bug de Jinja2 3.x)
# ---------------------------------------------------------------------------
import jinja2
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="web/templates")
try:
    templates.env.cache = None
except Exception:
    pass


async def render_template(template_name: str, context: dict) -> HTMLResponse:
    """Renderiza una plantilla Jinja2 (síncrono, compatible con el entorno)."""
    template = templates.get_template(template_name)
    content = template.render(context)
    return HTMLResponse(content=content)


app.state.render_template = render_template


# ---------------------------------------------------------------------------
# Rutas
# ---------------------------------------------------------------------------
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(client.router, prefix="/client", tags=["client"])
app.include_router(advisor.router, prefix="/advisor", tags=["advisor"])
app.include_router(api.router, prefix="/api", tags=["api"])


def _authed_user(request: Request) -> dict | None:
    token = request.cookies.get(COOKIE_NAME)
    return decode_token(token) if token else None


def _route_by_role(rol: str) -> str:
    if rol in ("superadmin", "admin_asesoria", "asesor_contable", "asesor_mercantil",
               "asesor_administrativo", "asesor_personal"):
        return "/advisor/dashboard"
    return "/client/dashboard"


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    user = _authed_user(request)
    if user:
        return RedirectResponse(_route_by_role(user.get("rol", "cliente")))
    return RedirectResponse(url="/auth/login")


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "gestia-web",
        "db": getattr(app.state, "db_ready", False),
        "version": app.version,
    }


if __name__ == "__main__":
    uvicorn.run("web.main:app", host="0.0.0.0", port=8080, reload=True)
