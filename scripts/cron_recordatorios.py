#!/usr/bin/env python3
"""GESTIA - Cron de recordatorios de plazos (Lanzador autónomo).

Envía a cada empresa cliente un email con sus obligaciones próximas
según los umbrales 7/3/1 días. Se lanza desde el Task Scheduler de Windows
(o cualquier cron) para que corra diariamente:

    .venv/Scripts/python.exe scripts/cron_recordatorios.py

Imprimirá un resumen en la salida (para logs) y registrará cada envío en
la tabla `comunicaciones` para auditoría.
"""

from __future__ import annotations

import asyncio
import os
import sys

# Asegurar que podemos importar web/ desde el root del repo
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass


async def main() -> None:
    import datetime
    from web.services.recordatorios import recordatorios_todas
    resumen = await recordatorios_todas(enviar=True)
    print(f"=== GESTIA Cron de recordatorios: {datetime.date.today().isoformat()} ===")
    enviados = 0
    para = 0
    sin_email = 0
    for r in resumen:
        n = r["eventos_enviados"]
        if r["saltados_por_no_email"]:
            sin_email += 1
            print(f"  - {r['empresa']}: {n} plazos pero SIN email de contacto")
        elif n:
            para += 1
            enviados += n
            print(f"  - {r['empresa']}: {n} email(s) -> {r['destino']} (estado {r.get('estado')})")
    print(f"RESUMEN: {enviados} emails enviados a {para} empresa(s). {sin_email} sin email de contacto.")


if __name__ == "__main__":
    asyncio.run(main())