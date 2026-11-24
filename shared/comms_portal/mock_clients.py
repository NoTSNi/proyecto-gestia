#!/usr/bin/env python3
"""
Mock clients for testing CommsPortal without real external services.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional
from datetime import datetime


@dataclass
class MockMessage:
    """Mock message sent."""
    to: str
    subject: str
    body: str
    html: str | None = None
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict = field(default_factory=dict)


class MockEmailClient:
    """Mock SMTP client for testing."""
    
    def __init__(self):
        self.sent_messages: list[MockMessage] = []
        self.fail_next = False
        self.delay = 0.0
    
    async def send(self, to: str, subject: str, body: str, html: str | None = None) -> bool:
        """Simulate sending email."""
        if self.delay:
            import asyncio
            await asyncio.sleep(self.delay)
        
        if self.fail_next:
            self.fail_next = False
            raise Exception("Mock SMTP error")
        
        msg = MockMessage(to=to, subject=subject, body=body, html=html)
        self.sent_messages.append(msg)
        print(f"📧 [MOCK EMAIL] To: {to} | Subject: {subject}")
        return True
    
    def get_sent_count(self) -> int:
        return len(self.sent_messages)
    
    def get_last_message(self) -> MockMessage | None:
        return self.sent_messages[-1] if self.sent_messages else None
    
    def clear(self):
        self.sent_messages.clear()


class MockWhatsAppClient:
    """Mock WhatsApp Business API client for testing."""
    
    def __init__(self):
        self.sent_messages: list[MockMessage] = []
        self.fail_next = False
        self.delay = 0.0
    
    async def send(self, to: str, body: str) -> bool:
        """Simulate sending WhatsApp message."""
        if self.delay:
            import asyncio
            await asyncio.sleep(self.delay)
        
        if self.fail_next:
            self.fail_next = False
            raise Exception("Mock WhatsApp API error")
        
        msg = MockMessage(to=to, subject="WhatsApp", body=body)
        self.sent_messages.append(msg)
        print(f"📱 [MOCK WHATSAPP] To: {to} | Body: {body[:50]}...")
        return True
    
    def get_sent_count(self) -> int:
        return len(self.sent_messages)
    
    def get_last_message(self) -> MockMessage | None:
        return self.sent_messages[-1] if self.sent_messages else None
    
    def clear(self):
        self.sent_messages.clear()


class MockSlackClient:
    """Mock Slack client for testing."""
    
    def __init__(self):
        self.sent_messages: list[MockMessage] = []
        self.fail_next = False
        self.delay = 0.0
    
    async def post(self, channel: str, body: str) -> bool:
        """Simulate posting to Slack."""
        if self.delay:
            import asyncio
            await asyncio.sleep(self.delay)
        
        if self.fail_next:
            self.fail_next = False
            raise Exception("Mock Slack API error")
        
        msg = MockMessage(to=channel, subject="Slack", body=body)
        self.sent_messages.append(msg)
        print(f"💬 [MOCK SLACK] Channel: {channel} | Body: {body[:50]}...")
        return True
    
    def get_sent_count(self) -> int:
        return len(self.sent_messages)
    
    def get_last_message(self) -> MockMessage | None:
        return self.sent_messages[-1] if self.sent_messages else None
    
    def clear(self):
        self.sent_messages.clear()


class MockCommsPortal:
    """High-level mock for testing full notification flows."""
    
    def __init__(self):
        self.email = MockEmailClient()
        self.whatsapp = MockWhatsAppClient()
        self.slack = MockSlackClient()
        self.notifications_sent: list[dict] = []
    
    async def send_test_notification(
        self,
        template_id: str,
        variables: dict,
        canales: Optional[list[str]] = None,
    ) -> dict:
        """Simulate full notification flow for testing."""
        from shared.comms_portal import CommsPortal, CanalNotificacion, TEMPLATES
        from datetime import datetime
        
        if canales is None:
            canales = ["email", "portal"]
        
        template = TEMPLATES.get(template_id)
        if not template:
            return {"error": f"Template {template_id} not found"}
        
        # Render
        asunto = template.asunto.format(**variables)
        cuerpo = template.cuerpo.format(**variables)
        cuerpo_html = template.cuerpo_html.format(**variables) if template.cuerpo_html else None
        
        results = {"template": template_id, "channels": {}}
        
        for canal_name in canales:
            canal = CanalNotificacion(canal_name)
            
            if canal == CanalNotificacion.EMAIL:
                to_email = variables.get("email", "test@example.com")
                last_msg = self.email.get_last_message()
                html_content = last_msg.html if last_msg else None
                await self.email.send(to_email, asunto, cuerpo, html_content)
                results["channels"][canal_name] = {"status": "sent", "to": to_email}
            
            elif canal == CanalNotificacion.WHATSAPP:
                to_phone = variables.get("phone", "+34600000000")
                await self.whatsapp.send(to_phone, cuerpo)
                results["channels"][canal_name] = {"status": "sent", "to": to_phone}
            
            elif canal == CanalNotificacion.SLACK:
                channel = variables.get("slack_channel", "#general")
                await self.slack.post(channel, cuerpo)
                results["channels"][canal_name] = {"status": "sent", "channel": channel}
            
            elif canal == CanalNotificacion.PORTAL:
                results["channels"][canal_name] = {"status": "stored", "note": "Stored in DB"}
        
        self.notifications_sent.append({
            "template_id": template_id,
            "variables": variables,
            "timestamp": datetime.now(),
            "results": results
        })
        
        return results
    
    def get_stats(self) -> dict:
        return {
            "email_sent": self.email.get_sent_count(),
            "whatsapp_sent": self.whatsapp.get_sent_count(),
            "slack_sent": self.slack.get_sent_count(),
            "total_notifications": len(self.notifications_sent)
        }
    
    def clear_all(self):
        self.email.clear()
        self.whatsapp.clear()
        self.slack.clear()
        self.notifications_sent.clear()


# Singleton for easy testing
mock_comms = MockCommsPortal()