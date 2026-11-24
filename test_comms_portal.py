#!/usr/bin/env python3
"""
Test script for CommsPortal with mock clients using cliente_ejemplo data.
"""
import asyncio
import json
import os
import sys
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from shared.comms_portal.mock_clients import MockCommsPortal, mock_comms
from shared.comms_portal import TEMPLATES, CanalNotificacion


async def test_comms_portal():
    """Test CommsPortal with mock clients using cliente_ejemplo data."""
    print("🧪 TESTEO COMPLETO COMPSPORTAL + MOCK CLIENTS")
    print("=" * 60)
    
    # Cargar metadata del cliente_ejemplo
    with open("cliente_ejemplo/metadata.json") as f:
        metadata = json.load(f)
    
    cliente = metadata["cliente_ejemplo"]
    print(f"\n📋 Cliente: {cliente['empresa']['nombre']} ({cliente['empresa']['nif']})")
    
    # Limpiar mocks
    mock_comms.clear_all()
    
    # Datos de test basados en cliente_ejemplo
    test_cases = [
        {
            "template": "documento_recibido",
            "variables": {
                "filename": "factura_emitida_001.txt",
                "tipo": "factura_emitida",
                "email": "cliente@tech-solutions.es",
            },
            "canales": ["email", "portal"],
        },
        {
            "template": "documento_procesado",
            "variables": {
                "filename": "contrato_laboral_juan_perez.txt",
                "tipo": "contrato_laboral",
                "chunks": 5,
                "email": "asesor@tech-solutions.es",
            },
            "canales": ["email", "portal", "slack"],
        },
        {
            "template": "deadline_proximo",
            "variables": {
                "titulo": "Modelo 303 - IVA Trimestral Q1",
                "fecha_limite": "20/04/2025",
                "dias": 15,
                "accion": "Recopilar facturas, calcular IVA, generar modelo 303",
                "email": "cliente@tech-solutions.es",
            },
            "canales": ["email", "whatsapp", "portal"],
        },
        {
            "template": "modelo_calculado",
            "variables": {
                "codigo": "303",
                "periodo": "Q1-2025",
                "resultado": "A devolver 1.250,00 €",
                "email": "asesor@tech-solutions.es",
            },
            "canales": ["email", "portal"],
        },
        {
            "template": "nomina_lista",
            "variables": {
                "mes": "Enero",
                "anio": "2025",
                "count": 1,
                "total": "1880.00",
                "email": "cliente@tech-solutions.es",
            },
            "canales": ["email", "portal", "slack"],
        },
        {
            "template": "contrato_por_vencer",
            "variables": {
                "empleado": "Juan Pérez García",
                "tipo": "Indefinido",
                "fecha_fin": "31/01/2026",
                "email": "rrhh@tech-solutions.es",
            },
            "canales": ["email", "portal"],
        },
        {
            "template": "escrito_plazo",
            "variables": {
                "tipo": "Recurso de reposición",
                "organo": "Consejería Economía Madrid",
                "fecha_limite": "20/02/2025",
                "email": "asesor@tech-solutions.es",
            },
            "canales": ["email", "portal", "whatsapp"],
        },
    ]
    
    print(f"\n📋 Ejecutando {len(test_cases)} casos de test...\n")
    
    resultados = []
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n🔹 Test {i}: {test['template']}")
        print(f"   Canales: {', '.join(test['canales'])}")
        
        try:
            result = await mock_comms.send_test_notification(
                template_id=test["template"],
                variables=test["variables"],
                canales=test["canales"],
            )
            
            if "error" in result:
                print(f"   ❌ Error: {result['error']}")
                resultados.append({"test": test["template"], "status": "ERROR", "error": result["error"]})
            else:
                canales_ok = list(result["channels"].keys())
                print(f"   ✅ Enviado por: {', '.join(canales_ok)}")
                for canal, info in result["channels"].items():
                    if info.get("status") == "sent":
                        print(f"      {canal}: {info.get('to') or info.get('channel') or 'DB'}")
                resultados.append({"test": test["template"], "status": "OK", "channels": canales_ok})
        
        except Exception as e:
            print(f"   ❌ Excepción: {e}")
            resultados.append({"test": test["template"], "status": "EXCEPTION", "error": str(e)})
        
        await asyncio.sleep(0.1)  # Pequeña pausa
    
    # Resumen
    print(f"\n{'='*60}")
    print("📊 RESUMEN DE RESULTADOS")
    print("="*60)
    
    ok = sum(1 for r in resultados if r["status"] == "OK")
    total = len(resultados)
    
    for r in resultados:
        status_icon = "✅" if r["status"] == "OK" else "❌"
        canales = ", ".join(r.get("channels", []))
        print(f"  {status_icon} {r['test']}: {r['status']} ({canales})")
    
    print(f"\n📈 TOTAL: {ok}/{total} tests OK")
    
    # Stats de mocks
    stats = mock_comms.get_stats()
    print(f"\n📬 ESTADÍSTICAS MOCKS:")
    print(f"   📧 Emails enviados: {stats['email_sent']}")
    print(f"   📱 WhatsApp enviados: {stats['whatsapp_sent']}")
    print(f"   💬 Slack enviados: {stats['slack_sent']}")
    print(f"   📋 Total notificaciones: {stats['total_notifications']}")
    
    # Verificar contenido de algunos mensajes
    print(f"\n🔍 VERIFICACIÓN DE CONTENIDO:")
    last_email = mock_comms.email.get_last_message()
    if last_email:
        print(f"   Último email: {last_email.subject[:60]}...")
        print(f"   Cuerpo: {last_email.body[:80]}...")
    
    last_whatsapp = mock_comms.whatsapp.get_last_message()
    if last_whatsapp:
        print(f"   Último WhatsApp: {last_whatsapp.body[:80]}...")
    
    last_slack = mock_comms.slack.get_last_message()
    if last_slack:
        print(f"   Último Slack: {last_slack.body[:80]}...")
    
    return ok == total


async def main():
    success = await test_comms_portal()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    import sys
    asyncio.run(main())