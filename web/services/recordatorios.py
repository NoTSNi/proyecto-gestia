"""GESTIA Web - Recordatorios de plazos (Fase G, cron).

Envía a cada empresa cliente un email con sus obligaciones próximas
(modelos 303/111/TC1, etc.) según su calendario. Umbrales: 7 días, 3 días y
1 día antes del vencimiento.

Regla del sistema: el AGENTE propone, la asesoría decide. Este recordatorio
es informativo (no ejecuta nada) y se audita en la tabla `comunicaciones`.

Uso manual: `async enviar_recordatorios(vista=7)` desde un cron/endpoint.
"""

from __future__ import annotations

import datetime as _dt

from web.services.comms import PORTAL


def _escapa_plazos(fecha: str, hoy: _dt.date) -> str | None:
    """Devuelve la etiqueta del umbral ('hoy','1','3','7') o None si no toca."""
    try:
        f = _dt.date.fromisoformat(str(fecha)[:10])
    except (ValueError, TypeError):
        return None
    diff = (f - hoy).days
    if diff < 0:
        return None  # vencido, no recordamos
    if diff == 0:
        return "hoy"
    if diff <= 1:
        return "1"
    if diff <= 3:
        return "3"
    if diff <= 7:
        return "7"
    return None


async def recordatorios_empresa(empresa: dict, hoy: _dt.date | None = None,
                                enviar: bool = True) -> dict:
    """Genera y (opcionalmente) envía los recordatorios de una empresa.

    Devuelve {eventos_enviados, total_eventos, destino, saltados_por_no_email}.
    """
    from web import database
    hoy = hoy or _dt.date.today()
    destino = (empresa.get("email_contacto") or "").strip()
    eventos = await database.list_eventos(empresa["id"])

    por_vista: dict[str, list] = {}
    for ev in eventos:
        etiqueta = _escapa_plazos(ev.get("fecha", ""), hoy)
        if etiqueta:
            por_vista.setdefault(etiqueta, []).append(ev)

    if not por_vista:
        return {"eventos_enviados": 0, "total_eventos": len(eventos),
                "destino": destino, "saltados_por_no_email": False}

    if not destino:
        return {"eventos_enviados": 0, "total_eventos": len(eventos),
                "destino": destino, "saltados_por_no_email": True}

    cuerpo = _redacta_cuerpo(empresa, por_vista)
    res = await PORTAL.enviar_email(
        empresa["id"], destino,
        f"📅 Recordatorio de plazos - {empresa['nombre']}",
        cuerpo, usuario="cron"
    )
    enviados = sum(len(v) for v in por_vista.values())
    return {"eventos_enviados": enviados, "total_eventos": len(eventos),
            "destino": destino, "saltados_por_no_email": False,
            "estado": res["estado"], "id": res["id"]}


def _redacta_cuerpo(empresa: dict, por_vista: dict) -> str:
    etiquetas = {"hoy": "vencen HOY", "1": "vencen en 1 día",
                 "3": "vencen en pocos días", "7": "vienen próximamente"}
    lineas = [
        f"Hola, {empresa['nombre']}:",
        "",
        "Te recordamos estas obligaciones de tu calendario fiscal/laboral:",
        "",
    ]
    for etiqueta in ("hoy", "1", "3", "7"):
        if etiqueta not in por_vista:
            continue
        lineas.append(f"▪ {etiquetas[etiqueta]}:")
        for ev in por_vista[etiqueta]:
            lineas.append(f"  - {ev['titulo']} (fecha límite: {ev['fecha'][:10]})")
        lineas.append("")
    lineas += [
        "Para cualquier duda, contacta con tu asesoría.",
        "",
        "— GESTIA",
    ]
    return "\n".join(lineas)


async def recordatorios_todas(enviar: bool = True) -> list[dict]:
    """Genera los recordatorios de todas las empresas (para el cron)."""
    from web import database
    empresas = await database.list_empresas()
    resumen = []
    for emp in empresas:
        r = await recordatorios_empresa(emp, enviar=enviar)
        r["empresa"] = emp["nombre"]
        resumen.append(r)
    return resumen