#!/usr/bin/env python3
"""
GESTIA Web - Main entry point for web UI.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse
import uvicorn
import jinja2

from web.routes import client, advisor, api


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title="GESTIA Web",
    description="Interfaz web para GESTIA - Gestoría Inteligente",
    version="0.1.0",
    lifespan=lifespan,
)

# Static files
app.mount("/static", StaticFiles(directory="web/static"), name="static")

# Jinja2 environment - no cache to avoid bug
env = jinja2.Environment(
    loader=jinja2.FileSystemLoader("web/templates"),
    auto_reload=True,
    enable_async=True,
)
# Disable cache completely
env.cache = None


async def render_template(template_name: str, context: dict) -> HTMLResponse:
    """Render template directly using Jinja2 environment."""
    template = env.get_template(template_name)
    content = await template.render_async(context)
    return HTMLResponse(content=content)


# Include routers
app.include_router(client.router, prefix="/client", tags=["client"])
app.include_router(advisor.router, prefix="/advisor", tags=["advisor"])
app.include_router(api.router, prefix="/api", tags=["api"])


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return RedirectResponse(url="/client/dashboard")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "gestia-web"}


# Export for routes
app.state.env = env
app.state.render_template = render_template


if __name__ == "__main__":
    uvicorn.run("web.main:app", host="0.0.0.0", port=8080, reload=True)
