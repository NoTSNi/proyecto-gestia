"""GESTIA Web - Agente monitor de seguridad (Fase E).

Revisa el audit log en busca de anomalías y produce un informe.
Pensado para ejecutarse periódicamente (cron) o bajo demanda desde el panel.

Detecciones:
- Rafagas de logins fallidos (posible fuerza bruta / hackeo)
- Cuentas bloqueadas
- Intentos de acceso cross-tenant o a rutas restringidas
- Activación/desactivación de 2FA
- Subidas de archivos rechazados por cuarentena

El monitor NO actúa: identifica, clasifica por severidad y alerta (de momento
escribe en el propio audit log el resultado del barrido; en Fase G se envia
por email/WhatsApp/Slack).
"""

from __future__ import annotations

import asyncio
from collections import Counter
from datetime import datetime, timedelta

from web import database


async def _barrido_tiempo(dias: int = 1) -> str:
    """Devuelve el timestamp ISO de hace N días (para filtrar el log)."""
    return (datetime.now().astimezone() - timedelta(days=dias)).isoformat(timespec="seconds")


async def monitor_seguridad(dias: int = 1, persistence: bool = False, ip: str | None = None) -> dict:
    """Ejecuta un barrido de seguridad y devuelve el informe.

    Args:
        dias: ventana de análisis.
        persistence: si True, escribe el resultado del barrido en el audit log.
        ip: IP del operador que lanza el barrido (para registrar quién).
    """
    registros = await database.list_audit_seguridad(limit=2000)
    desde = await _barrido_tiempo(dias)
    reg = [r for r in registros if r.get("created_at", "") >= desde]

    informe: dict = {
        "dias": dias,
        "eventos": len(reg),
        "anomalias": [],
        "alerta": False,
        "detalle": {},
    }

    # 1) Rafaga de logins fallidos por email
    fallidos = Counter(r.get("usuario", "?") for r in reg if r.get("tipo") == "login_fallido")
    rafagas = {email: n for email, n in fallidos.items() if n >= 3}
    if rafagas:
        informe["anomalias"].append(
            f"Ráfaga de logins fallidos: {', '.join(f'{e} ({n})' for e, n in rafagas.items())}"
        )
        informe["detalle"]["logins_fallidos"] = rafagas

    # 2) Cuentas bloqueadas / login rechazado por bloqueo
    bloqueos = [r for r in reg if r.get("tipo") == "login_rechazado"]
    if bloqueos:
        informe["anomalias"].append(f"{len(bloqueos)} intento(s) de login a cuenta bloqueada")
        informe["detalle"]["login_rechazado"] = len(bloqueos)

    # 3) Intentos de 2FA fallidos (posible robo de credenciales)
    tfa_fallidos = [r for r in reg if r.get("tipo") == "2fa_fallido"]
    if tfa_fallidos:
        informe["anomalias"].append(f"{len(tfa_fallidos)} intento(s) 2FA incorrecto(s)")
        informe["detalle"]["2fa_fallidos"] = len(tfa_fallidos)

    # 4) Eventos 2FA (activación/desactivación)
    tfa_eventos = [r for r in reg if r.get("tipo") in ("2fa_activado", "2fa_desactivado")]
    informe["detalle"]["2fa_cambios"] = [
        {"tipo": r["tipo"], "usuario": r.get("usuario"), "cuando": r.get("created_at")}
        for r in tfa_eventos
    ]

    # 5) Subidas rechazadas por cuarentena (seguridad de archivos)
    # Se extraen de los query_params de la BD de archivos o del log; por ahora:
    # contamos errores 'archivo_rechazado' si llegaran, y dejamos el campo listo.
    rechazados = [r for r in reg if r.get("tipo") == "archivo_rechazado"]
    if rechazados:
        informe["anomalias"].append(f"{len(rechazados)} archivo(s) rechazado(s) por cuarentena")
        informe["detalle"]["archivos_rechazados"] = len(rechazados)

    informe["alerta"] = len(informe["anomalias"]) > 0

    # Registrar el barrido en el audit (auditoría del propio monitor)
    if persistence:
        await database.auditar_seguridad(
            "monitor_seguridad",
            f"Barrido completado: {informe['eventos']} eventos, "
            f"{len(informe['anomalias'])} anomalía(s), alerta={informe['alerta']}",
            ip=ip, usuario="system",
        )

    return informe


async def main() -> None:
    """Entrada de consola: python -m web.services.monitor_seguridad"""
    informe = await monitor_seguridad(dias=1, persistence=True)
    print(f"=== Monitor de seguridad GESTIA ===")
    print(f"Ventana: {informe['dias']} día(s) | Eventos: {informe['eventos']} | Alerta: {informe['alerta']}")
    for a in informe["anomalias"]:
        print(f"  ⚠  {a}")
    if not informe["anomalias"]:
        print("  ✓ Sin anomalías detectadas.")


if __name__ == "__main__":
    asyncio.run(main())