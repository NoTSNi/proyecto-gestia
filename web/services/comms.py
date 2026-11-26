"""GESTIA Web - CommsPortal (Fase G).

Capa unificada de comunicaciones: Email (SMTP real + mock local), WhatsApp
(Twilio Sandbox para pruebas gratuitas + mock), Slack (mock) y un hook para
automatizaciones n8n.

Principios del proyecto:
- Sin credenciales reales -> modo MOCK: cada canal "envía" a un log de estado
  y se registra en BD igual que las reales (misma interfaz, misma auditoría).
- Con credenciales reales -> envío real (SMTP / Twilio API).
- n8n: GESTIA puede avisar a workflows externos (POST a un webhook) y puede
  ser llamado (recibir eventos). El webroot del webhook se configura por env.
- Regla: el AGENTE propone, por lo que el envío a clientes siempre requiere
  origen controlado (botón/acción del asesor), nunca automático sin revisión.

Config esperada en entorno (opcional):
  GESTIA_SMTP_HOST/PORT/USER/PASS/FROM  -> Email real
  GESTIA_TWILIO_ACCOUNT_SID/AUTH_TOKEN   -> WhatsApp real (Sandbox)
  GESTIA_TWILIO_WHATSAPP_FROM            -> número sandbox "whatsapp:+14155238886"
  GESTIA_N8N_WEBHOOK_URL                 -> notificar a n8n (automatizaciones)
Sin ninguna -> todos los canales quedan en modo MOCK (seguro por defecto).
"""

from __future__ import annotations

import logging
import os
import smtplib
import time
from dataclasses import dataclass, field
from email.message import EmailMessage

logger = logging.getLogger("gestia.comms")

# Modos por canal: "mock" por defecto, "real" si hay credenciales.
def _mode(*vars_: str) -> str:
    return "real" if all(os.getenv(v) for v in vars_) else "mock"


class ComunicacionStore:
    """Persistir el registro de envío en BD (append-only por tenant)."""

    async def guardar(self, tenant_id: str, canal: str, destino: str, asunto: str,
                      cuerpo: str, estado: str, externo_id: str | None = None,
                      usuario: str | None = None) -> None:
        from web import database
        await database.registrar_comunicacion(
            tenant_id=tenant_id, canal=canal, destino=destino, asunto=asunto,
            cuerpo=cuerpo, estado=estado, externo_id=externo_id, usuario=usuario,
        )


class EmailClient:
    """Email real vía SMTP, o mock local si no hay credenciales."""

    def __init__(self):
        self.host = os.getenv("GESTIA_SMTP_HOST", "")
        self.port = int(os.getenv("GESTIA_SMTP_PORT", "587"))
        self.user = os.getenv("GESTIA_SMTP_USER", "")
        self.pwd = os.getenv("GESTIA_SMTP_PASS", "")
        self.frm = os.getenv("GESTIA_SMTP_FROM", "gestia@localhost")
        self.mode = "real" if (self.host and self.user) else "mock"

    async def enviar(self, destino: str, asunto: str, cuerpo: str) -> dict:
        if self.mode == "mock":
            return {"estado": "mock", "id": f"mock-email-{time.time():.0f}",
                    "info": f"(demo) Email a {destino}: {asunto}"}
        msg = EmailMessage()
        msg["From"] = self.frm
        msg["To"] = destino
        msg["Subject"] = asunto
        msg.set_content(cuerpo)
        try:
            with smtplib.SMTP(self.host, self.port, timeout=15) as s:
                s.starttls()
                s.login(self.user, self.pwd)
                s.send_message(msg)
            return {"estado": "real", "id": f"email-{time.time():.0f}", "info": "Enviado"}
        except Exception as e:  # noqa: BLE001
            return {"estado": "error", "id": "", "info": f"Fallo SMTP: {e}"}


class WhatsAppClient:
    """WhatsApp real vía Twilio (Sandbox gratis para pruebas) o mock."""

    def __init__(self):
        self.sid = os.getenv("GESTIA_TWILIO_ACCOUNT_SID", "")
        self.token = os.getenv("GESTIA_TWILIO_AUTH_TOKEN", "")
        self.frm = os.getenv("GESTIA_TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")
        self.mode = "real" if (self.sid and self.token) else "mock"

    async def enviar(self, destino: str, cuerpo: str) -> dict:
        if self.mode == "mock":
            return {"estado": "mock", "id": f"mock-wa-{time.time():.0f}",
                    "info": f"(demo) WhatsApp a {destino}: {cuerpo[:60]}"}
        import urllib.request
        import urllib.parse
        import base64
        url = (f"https://api.twilio.com/2010-04-01/Accounts/{self.sid}/Messages.json")
        data = urllib.parse.urlencode({
            "To": f"whatsapp:{destino}",
            "From": self.frm,
            "Body": cuerpo,
        }).encode()
        req = urllib.request.Request(url, data=data)
        req.add_header("Authorization", "Basic " + base64.b64encode(
            f"{self.sid}:{self.token}".encode()).decode())
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                body = r.read().decode()
            import re
            m = re.search(r'"sid":\s*"([^"]+)"', body)
            return {"estado": "real", "id": m.group(1) if m else "wa",
                    "info": "Enviado (Twilio)"}
        except Exception as e:  # noqa: BLE001
            return {"estado": "error", "id": "", "info": f"Fallo Twilio: {e}"}


class N8nHook:
    """Hook de automatizaciones n8n: GESTIA notifica eventos a un webhook n8n.

    El webhook n8n puede a su vez llamar de vuelta a la API de GESTIA. De esta
    forma n8n orquesta (email encadenado, recordatorios, distribución) y
    GESTIA sigue siendo el sistema de verdad con sus datos.
    """

    def __init__(self):
        self.url = os.getenv("GESTIA_N8N_WEBHOOK_URL", "")
        self.mode = "real" if self.url else "mock"

    async def disparar(self, evento: str, payload: dict) -> dict:
        if self.mode == "mock":
            return {"estado": "mock", "id": f"mock-n8n-{time.time():.0f}",
                    "info": f"(demo) n8n hook '{evento}' recibiría {len(payload)} claves"}
        import urllib.request
        import json
        req = urllib.request.Request(
            self.url, data=json.dumps({"evento": evento, **payload}).encode(),
            headers={"Content-Type": "application/json"}, method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return {"estado": "real", "id": f"n8n-{time.time():.0f}",
                        "info": f"n8n {r.status}"}
        except Exception as e:  # noqa: BLE001
            return {"estado": "error", "id": "", "info": f"Fallo n8n: {e}"}


@dataclass
class CommsPortal:
    """Orquestador unificado. Expone estado (para el panel) y envíos."""

    email: EmailClient = field(default_factory=EmailClient)
    whatsapp: WhatsAppClient = field(default_factory=WhatsAppClient)
    n8n: N8nHook = field(default_factory=N8nHook)
    store: ComunicacionStore = field(default_factory=ComunicacionStore)

    def estado(self) -> dict:
        return {
            "email": self.email.mode,
            "whatsapp": self.whatsapp.mode,
            "n8n": self.n8n.mode,
        }

    async def enviar_email(self, tenant_id: str, destino: str, asunto: str,
                           cuerpo: str, usuario: str | None = None) -> dict:
        res = await self.email.enviar(destino, asunto, cuerpo)
        await self.store.guardar(tenant_id, "email", destino, asunto, cuerpo,
                                 res["estado"], res.get("id"), usuario)
        return res

    async def enviar_whatsapp(self, tenant_id: str, destino: str, cuerpo: str,
                              usuario: str | None = None) -> dict:
        res = await self.whatsapp.enviar(destino, cuerpo)
        await self.store.guardar(tenant_id, "whatsapp", destino, "WhatsApp",
                                 cuerpo, res["estado"], res.get("id"), usuario)
        return res

    async def notificar_n8n(self, tenant_id: str, evento: str, payload: dict,
                            usuario: str | None = None) -> dict:
        res = await self.n8n.disparar(evento, payload)
        await self.store.guardar(tenant_id, "n8n", evento, f"n8n:{evento}",
                                 str(payload), res["estado"], res.get("id"), usuario)
        return res


# Instancia global (cada request nuevo la crea para leer config actual; esta
# sirve de referencia y para tests).
PORTAL = CommsPortal()