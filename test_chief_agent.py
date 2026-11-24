#!/usr/bin/env python3
"""
Test script for ChiefAgent with cliente_ejemplo data.
"""
import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents.chief import ChiefAgent
from agents.base_agent import AgentContext


async def test_chief_agent():
    """Test ChiefAgent with cliente_ejemplo queries."""
    print("🧪 TESTEO CHIEF AGENT")
    print("=" * 60)
    
    # Cargar metadata
    with open("cliente_ejemplo/metadata.json") as f:
        metadata = json.load(f)
    
    cliente = metadata["cliente_ejemplo"]
    print(f"\n📋 Cliente: {cliente['empresa']['nombre']} ({cliente['empresa']['nif']})")
    
    # Instanciar ChiefAgent
    chief = ChiefAgent()
    
    # Queries de test basadas en cliente_ejemplo
    test_queries = [
        {
            "name": "Simple - Factura",
            "query": "He recibido una factura de Telefónica por 118€, ¿cómo la contabilizo?",
            "expected_specialist": "contable",
            "complexity": "simple",
        },
        {
            "name": "Simple - Contrato",
            "query": "Necesito un contrato indefinido para un nuevo técnico contable",
            "expected_specialist": "personal",
            "complexity": "simple",
        },
        {
            "name": "Simple - Mercantil",
            "query": "Quiero constituir una SL con 10000€ de capital",
            "expected_specialist": "mercantil",
            "complexity": "simple",
        },
        {
            "name": "Complejo - Multi-dominio",
            "query": "He recibido una factura de proveedor por 118€ con IVA, necesito contabilizarla, verificar si el proveedor tiene contrato vigente, y verificar si hay algún plazo administrativo para presentar el modelo 303 este trimestre",
            "expected_specialist": "multi",
            "complexity": "complex",
        },
        {
            "name": "Escalación - Urgente",
            "query": "URGENTE: He recibido una notificación de inspección de Hacienda para la próxima semana, necesito preparar toda la documentación fiscal y mercantil urgente",
            "expected_specialist": "escalation",
            "complexity": "escalation",
            "expect_success": False,
        },
        {
            "name": "Complejo - Nóminas + Fiscal",
            "query": "Necesito calcular las nóminas de enero para 5 empleados, generar los TC1/TC2, preparar el modelo 111 de retenciones IRPF y el modelo 303 de IVA del primer trimestre",
            "expected_specialist": "multi",
            "complexity": "complex",
        },
    ]
    
    print(f"\n📋 Ejecutando {len(test_queries)} consultas de test...\n")
    
    results = []
    
    for i, test in enumerate(test_queries, 1):
        print(f"\n🔹 Test {i}: {test['name']}")
        print(f"   Query: {test['query'][:80]}...")
        
        try:
            context = AgentContext(
                user_id="test_user",
                tenant_id="tech-solutions-sl",
                metadata={"test_case": test["name"]},
            )
            
            chief = ChiefAgent()
            response = await chief.process(test["query"], AgentContext(user_id="test", tenant_id="tech-solutions-sl"))
            
            # Check expected success
            expected_success = test.get("expect_success", True)
            if response.success != expected_success:
                print(f"   ❌ Expected success={expected_success}, got {response.success}")
                results.append({"test": test["name"], "success": False, "error": f"Expected success={expected_success}"})
                continue
            
            # Analyze response
            routed_to = response.data.get("chief_metadata", {}).get("routed_to", "unknown")
            quality = response.data.get("chief_metadata", {}).get("quality_score", "N/A")
            
            print(f"   ✅ Respuesta: {response.success}")
            print(f"   📍 Routed to: {response.agent}")
            print(f"   📊 Quality: {quality}")
            
            if "chief_metadata" in response.data:
                print(f"   📋 Metadata: {json.dumps(response.data['chief_metadata'], indent=6)[:200]}")
            
            results.append({
                "test": test["name"],
                "success": response.success,
                "agent": response.agent,
                "query_type": test["complexity"],
            })
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            import traceback
            traceback.print_exc()
            results.append({"test": test["name"], "success": False, "error": str(e)})
    
    # Summary
    print(f"\n{'='*60}")
    print("📊 RESUMEN CHIEF AGENT")
    print("="*60)
    
    ok = sum(1 for r in results if r.get("success", False))
    total = len(results)
    
    for r in results:
        expected = test_queries[results.index(r)].get("expect_success", True)
        actual = r.get("success", False)
        icon = "✅" if actual == expected else "❌"
        agent = r.get("agent", "N/A")
        qtype = r.get("query_type", "N/A")
        print(f"  {icon} {r['test']}: {actual} (expected {expected}) | Agent: {agent} | Type: {qtype}")
    
    print(f"\n📈 TOTAL: {ok}/{total} tests OK")
    
    return all(r.get("success", False) == test_queries[results.index(r)].get("expect_success", True) for r in results)


async def main():
    success = await test_chief_agent()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())