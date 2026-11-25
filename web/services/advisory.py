"""GESTIA Web - Servicio de consulta a los agentes (Fase A).

Puente entre la web y el ChiefAgent: carga los datos reales del tenant desde
la BD, construye un ChiefAgent fresco (sin estado compartido entre requests),
ejecuta la consulta y devuelve la respuesta estructurada.
"""

from __future__ import annotations

from typing import Optional

from agents.base_agent import AgentContext
from agents.chief import ChiefAgent

from web import database as database
from web.database import registrar_consulta as database_registrar_consulta


async def cargar_client_data(tenant_id: str) -> dict:
    """Compone el contexto real del cliente desde la BD."""
    from web import database

    empresa = await database.get_empresa(tenant_id)
    if not empresa:
        return {}

    documentos = await database.list_documentos(tenant_id)
    notificaciones = await database.list_notificaciones(tenant_id)
    eventos = await database.list_eventos(tenant_id)
    usuarios = await database.list_usuarios(tenant_id)

    return {
        "empresa": {
            "id": empresa["id"],
            "nif": empresa["nif"],
            "nombre": empresa["nombre"],
            "nombre_comercial": empresa.get("nombre_comercial"),
            "regimen_iva": empresa.get("regimen_iva"),
            "periodicidad_iva": empresa.get("periodicidad_iva"),
            "cnae": empresa.get("cnae"),
            "estado": empresa.get("estado"),
            "direccion": empresa.get("direccion"),
            "municipio": empresa.get("municipio"),
            "provincia": empresa.get("provincia"),
        },
        "documentos": documentos,
        "notificaciones": notificaciones,
        "calendario": eventos,
        "usuarios": [
            {"full_name": u.get("full_name"), "email": u.get("email"), "rol": u.get("rol")}
            for u in usuarios
        ],
    }


async def consultar_gestia(
    query: str,
    tenant_id: str,
    user_id: str,
) -> dict:
    """Ejecuta una consulta contra el ChiefAgent con los datos reales del tenant.

    Devuelve un dict serilizable con la respuesta estructurada.
    """
    client_data = await cargar_client_data(tenant_id)

    # ChiefAgent fresco por consulta: sin estado compartido entre requests
    chief = ChiefAgent(client_data=client_data or None)

    context = AgentContext(
        tenant_id=tenant_id,
        user_id=user_id,
    )
    # Pasar datos reales también en el contexto (redundancia a prueba de impactos)
    context.metadata["client_data"] = client_data

    result = await chief.process(query, context)

    # Registrar la consulta y su respuesta (auditoría por tenant)
    await database_registrar_consulta(
        tenant_id=tenant_id,
        user_id=user_id,
        query=query,
        respuesta=result.response,
        agente=result.agent,
        strategy=None,
        success=result.success,
    )

    response = {
        "query": query,
        "agent": result.agent,
        "success": result.success,
        "response": result.response,
        "data": result.data,
        "error": result.error,
        "specialists_consulted": [],
    }

    # Metadatos del Chief (routing, calidad, especialistas)
    chief_md = result.data.get("chief_metadata", {}) if result.data else {}
    response["routing_confidence"] = chief_md.get("routing_confidence")
    response["quality_score"] = chief_md.get("quality_score")
    response["strategy"] = chief_md.get("strategy", "route")
    response["specialists_consulted"] = (
        result.data.get("specialists_consulted", [])
        if result.data else []
    )

    return response