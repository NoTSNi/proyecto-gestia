"""GESTIA Web - API auxiliar (JSON) para partials / datos de la web."""

from __future__ import annotations

from fastapi import APIRouter, Request

from web import database

router = APIRouter()


@router.get("/empresas")
async def api_empresas(request: Request):
    rows = await database.list_empresas()
    return [
        {
            "id": r["id"], "nif": r["nif"], "nombre": r["nombre"],
            "nombre_comercial": r.get("nombre_comercial"), "cnae": r.get("cnae"),
            "estado": r.get("estado"), "municipio": r.get("municipio"),
            "provincia": r.get("provincia"),
        }
        for r in rows
    ]


@router.get("/empresas/{tenant_id}/documentos")
async def api_documentos(request: Request, tenant_id: str):
    rows = await database.list_documentos(tenant_id)
    return [
        {
            "id": r["id"], "nombre": r["nombre"], "tipo": r["tipo"],
            "estado": r["estado"], "monto": r.get("monto"),
        }
        for r in rows
    ]


@router.get("/empresas/{tenant_id}/eventos")
async def api_eventos(request: Request, tenant_id: str):
    rows = await database.list_eventos(tenant_id)
    return [dict(r) for r in rows]


@router.get("/empresas/{tenant_id}/notificaciones")
async def api_notificaciones(request: Request, tenant_id: str):
    rows = await database.list_notificaciones(tenant_id)
    return [dict(r) for r in rows]
