"""GESTIA Shared - Communications Portal (Email, WhatsApp, Notifications)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from gestia_core.models import Notificacion


class CanalNotificacion(str, Enum):
    EMAIL = "email"
    PORTAL = "portal"
    WHATSAPP = "whatsapp"
    SLACK = "slack"
    SMS = "sms"
    PUSH = "push"


@dataclass
class NotificationTemplate:
    template_id: str
    canal: CanalNotificacion
    asunto: str
    cuerpo: str
    cuerpo_html: str | None = None
    variables: list[str] = None


# Plantillas base
TEMPLATES = {
    "documento_recibido": NotificationTemplate(
        template_id="documento_recibido",
        canal=CanalNotificacion.EMAIL,
        asunto="📄 Documento recibido: {filename}",
        cuerpo="Hemos recibido tu documento {filename} ({tipo}). Está en procesamiento.",
        cuerpo_html="<p>Hemos recibido tu documento <strong>{filename}</strong> ({tipo}). Está en procesamiento.</p>",
        variables=["filename", "tipo"],
    ),
    "documento_procesado": NotificationTemplate(
        template_id="documento_procesado",
        canal=CanalNotificacion.EMAIL,
        asunto="✅ Documento procesado: {filename}",
        cuerpo="Tu documento {filename} ha sido clasificado como {tipo} y indexado. {chunks} fragmentos para búsqueda.",
        variables=["filename", "tipo", "chunks"],
    ),
    "deadline_proximo": NotificationTemplate(
        template_id="deadline_proximo",
        canal=CanalNotificacion.EMAIL,
        asunto="⏰ Próximo plazo: {titulo} - {dias} días",
        cuerpo="El plazo {titulo} vence el {fecha_limite}. Acción sugerida: {accion}",
        variables=["titulo", "fecha_limite", "dias", "accion"],
    ),
    "modelo_calculado": NotificationTemplate(
        template_id="modelo_calculado",
        canal=CanalNotificacion.EMAIL,
        asunto="📊 Modelo {codigo} calculado - {periodo}",
        cuerpo="El modelo {codigo} ({periodo}) ha sido calculado. Resultado: {resultado}. ¿Revisamos y presentamos?",
        variables=["codigo", "periodo", "resultado"],
    ),
    "nomina_lista": NotificationTemplate(
        template_id="nomina_lista",
        canal=CanalNotificacion.EMAIL,
        asunto="💰 Nóminas {mes}/{anio} listas para revisión",
        cuerpo="Se han calculado {count} nóminas para {mes}/{anio}. Total a pagar: {total}€. ¿Generamos TC1/TC2?",
        variables=["mes", "anio", "count", "total"],
    ),
    "contrato_por_vencer": NotificationTemplate(
        template_id="contrato_por_vencer",
        canal=CanalNotificacion.EMAIL,
        asunto="📅 Contrato vence en 30 días: {empleado}",
        cuerpo="El contrato de {empleado} ({tipo}) vence el {fecha_fin}. ¿Renovamos, transformamos o finalizamos?",
        variables=["empleado", "tipo", "fecha_fin"],
    ),
    "escrito_plazo": NotificationTemplate(
        template_id="escrito_plazo",
        canal=CanalNotificacion.EMAIL,
        asunto="⚖️ Plazo escrito administrativo: {tipo}",
        cuerpo="El escrito {tipo} para {organo} vence el {fecha_limite}. ¿Presentamos recurso?",
        variables=["tipo", "organo", "fecha_limite"],
    ),
}


class CommsPortal:
    """Multi-channel communications portal."""

    def __init__(self, email_client, whatsapp_client, slack_client, db_session):
        self.email = email_client
        self.whatsapp = whatsapp_client
        self.slack = slack_client
        self.db = db_session

    async def send_notification(
        self,
        tenant_id: str,
        template_id: str,
        variables: dict,
        destinatario_tipo: str,
        destinatario_id: str | None = None,
        canales: list[CanalNotificacion] | None = None,
    ) -> list[str]:
        """Send notification via multiple channels."""
        if canales is None:
            canales = [CanalNotificacion.EMAIL, CanalNotificacion.PORTAL]

        template = TEMPLATES.get(template_id)
        if not template:
            raise ValueError(f"Template {template_id} not found")

        # Render
        asunto = template.asunto.format(**variables)
        cuerpo = template.cuerpo.format(**variables)
        cuerpo_html = template.cuerpo_html.format(**variables) if template.cuerpo_html else None

        notification_ids = []

        for canal in canales:
            notif = await self._create_notification(
                tenant_id=tenant_id,
                canal=canal,
                destinatario_tipo=destinatario_tipo,
                destinatario_id=destinatario_id,
                asunto=asunto,
                cuerpo=cuerpo,
                cuerpo_html=cuerpo_html,
                template_id=template_id,
                template_data=variables,
            )
            notification_ids.append(notif.id)

            # Send via channel
            if canal == CanalNotificacion.EMAIL:
                await self._send_email(notif, variables.get("email"))
            elif canal == CanalNotificacion.WHATSAPP:
                await self._send_whatsapp(notif, variables.get("phone"))
            elif canal == CanalNotificacion.SLACK:
                await self._send_slack(notif, variables.get("slack_channel"))
            elif canal == CanalNotificacion.PORTAL:
                pass  # Already stored in DB

        return notification_ids

    async def _create_notification(
        self,
        tenant_id: str,
        canal: CanalNotificacion,
        destinatario_tipo: str,
        destinatario_id: str | None,
        asunto: str,
        cuerpo: str,
        cuerpo_html: str | None,
        template_id: str,
        template_data: dict,
    ) -> Notificacion:
        from gestia_core.models import Notificacion
        notif = Notificacion(
            tenant_id=tenant_id,
            canal=canal.value,
            destinatario_tipo=destinatario_tipo,
            destinatario_id=destinatario_id,
            asunto=asunto,
            cuerpo=cuerpo,
            cuerpo_html=cuerpo_html,
            template_id=template_id,
            template_data=template_data,
            estado="pendiente",
        )
        self.db.add(notif)
        await self.db.flush()
        return notif

    async def _send_email(self, notif: Notificacion, to_email: str | None):
        if not to_email or not self.email:
            return
        try:
            await self.email.send(to_email, notif.asunto, notif.cuerpo_html or notif.cuerpo)
            notif.estado = "enviado"
            notif.enviado_en = datetime.now(timezone.utc)
        except Exception as e:
            notif.estado = "fallido"
            notif.error = str(e)
        await self.db.flush()

    async def _send_whatsapp(self, notif: Notificacion, to_phone: str | None):
        if not to_phone or not self.whatsapp:
            return
        try:
            await self.whatsapp.send(to_phone, notif.cuerpo)
            notif.estado = "enviado"
            notif.enviado_en = datetime.now(timezone.utc)
        except Exception as e:
            notif.estado = "fallido"
            notif.error = str(e)
        await self.db.flush()

    async def _send_slack(self, notif: Notificacion, channel: str | None):
        if not channel or not self.slack:
            return
        try:
            await self.slack.post(channel, notif.cuerpo)
            notif.estado = "enviado"
            notif.enviado_en = datetime.now(timezone.utc)
        except Exception as e:
            notif.estado = "fallido"
            notif.error = str(e)
        await self.db.flush()

    async def get_notifications(
        self,
        tenant_id: str,
        estado: str | None = None,
        limit: int = 50,
    ) -> list:
        from sqlalchemy import select
        from gestia_core.models import Notificacion

        query = select(Notificacion).where(Notificacion.tenant_id == tenant_id)
        if estado:
            query = query.where(Notificacion.estado == estado)
        query = query.order_by(Notificacion.created_at.desc()).limit(limit)

        result = await self.db.execute(query)
        return result.scalars().all()