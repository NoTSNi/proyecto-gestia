#!/usr/bin/env python3
"""
Test individual para cada especialista mejorado.
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents.specialists.mercantil import MercantilAgent
from agents.specialists.administrativo import AdministrativoAgent
from agents.specialists.contable import ContableAgent
from agents.specialists.personal import PersonalAgent
from agents.base_agent import AgentContext


async def test_specialist(name: str, agent, queries: list[str]):
    """Test a specialist with multiple queries."""
    print(f"\n{'='*60}")
    print(f"🧪 TEST {name.upper()}")
    print("="*60)
    
    context = AgentContext(user_id="test", tenant_id="tech-solutions-sl")
    results = []
    
    for i, query in enumerate(queries, 1):
        print(f"\n🔹 Query {i}: {query[:70]}...")
        try:
            response = await agent.process(query, context)
            success = response.success
            action = response.data.get("action", "unknown")
            confidence = response.data.get("confidence", "N/A")
            has_next_steps = len(response.data.get("next_steps", [])) > 0
            has_docs = len(response.data.get("documents_needed", [])) > 0
            has_deadlines = len(response.data.get("deadlines", [])) > 0
            has_citations = len(response.data.get("citations", [])) > 0
            
            print(f"   ✅ Success: {success}")
            print(f"   📋 Action: {action}")
            print(f"   📊 Confidence: {confidence}")
            print(f"   📝 Next steps: {'Sí' if has_next_steps else 'No'}")
            print(f"   📄 Docs needed: {'Sí' if has_docs else 'No'}")
            print(f"   ⏰ Deadlines: {'Sí' if has_deadlines else 'No'}")
            print(f"   📚 Citations: {'Sí' if has_citations else 'No'}")
            
            # Show first 200 chars of response
            preview = response.response[:200].replace('\n', ' ')
            print(f"   💬 Preview: {preview}...")
            
            results.append({
                "query": query[:50],
                "success": success,
                "action": action,
                "structured": has_next_steps and has_docs,
            })
        except Exception as e:
            print(f"   ❌ Error: {e}")
            import traceback
            traceback.print_exc()
            results.append({"query": query[:50], "success": False, "error": str(e)})
    
    return results


async def main():
    print("🧪 TESTEO ESPECIALISTAS MEJORADOS")
    print("="*60)
    
    # Initialize agents
    mercantil = MercantilAgent()
    administrativo = AdministrativoAgent()
    contable = ContableAgent()
    personal = PersonalAgent()
    
    all_results = {}
    
    # Test Mercantil
    merc_queries = [
        "Quiero constituir una SL con 10000€ de capital",
        "Necesito modificar los estatutos de mi sociedad",
        "Cómo convoco una junta general ordinaria",
        "Cuándo debo legalizar los libros oficiales",
        "Proceso para disolver y liquidar la sociedad",
        "Cómo presento el depósito de cuentas anuales",
        "Quiero ampliar capital social en 50000€",
        "Necesito otorgar un poder notarial a mi gestor",
    ]
    all_results["mercantil"] = await test_specialist("mercantil", mercantil, merc_queries)
    
    # Test Administrativo
    admin_queries = [
        "Necesito licencia de apertura para mi oficina",
        "Quiero solicitar una subvención para digitalización",
        "He recibido una notificación de Hacienda, quiero recurrir",
        "Cómo preparo un recurso de reposición",
        "Me han abierto un expediente sancionador",
        "Qué es el silencio administrativo estimatorio",
        "Necesito licitar un contrato público",
    ]
    all_results["administrativo"] = await test_specialist("administrativo", administrativo, admin_queries)
    
    # Test Contable
    cont_queries = [
        "Cómo presento el modelo 303 de IVA este trimestre",
        "Necesito hacer el modelo 390 resumen anual",
        "Preparar modelo 200 Impuesto Sociedades",
        "Calcular pagos fraccionados modelo 202",
        "Generar modelo 111 retenciones IRPF",
        "Modelo 190 resumen anual retenciones",
        "Declaración informativa modelo 347",
        "Operaciones intracomunitarias modelo 349",
        "Cierre contable ejercicio 2024",
        "Conciliación bancaria mensual",
        "Calcular amortizaciones ejercicio",
        "Gestionar facturas emitidas y recibidas",
    ]
    all_results["contable"] = await test_specialist("contable", contable, cont_queries)
    
    # Test Personal
    pers_queries = [
        "Calcular nómina mensual para empleado",
        "Preparar nómina extraordinaria verano",
        "Calcular finiquito por despido",
        "Redactar contrato indefinido ordinario",
        "Contrato temporal por obra y servicio",
        "Contrato formativo para joven",
        "Generar TC1 y TC2 mensuales",
        "Dar de alta trabajador en SS",
        "Gestionar baja médica IT",
        "Permiso maternidad 16 semanas",
        "Evaluación riesgos laborales PRL",
        "Calcular tipo retención IRPF nómina",
        "Emitir certificado empresa para paro",
    ]
    all_results["personal"] = await test_specialist("personal", personal, pers_queries)
    
    # Summary
    print(f"\n{'='*60}")
    print("📊 RESUMEN GENERAL")
    print("="*60)
    
    total_ok = 0
    total_tests = 0
    
    for specialist, results in all_results.items():
        ok = sum(1 for r in results if r.get("success"))
        total = len(results)
        structured = sum(1 for r in results if r.get("structured"))
        total_ok += ok
        total_tests += total
        print(f"  {specialist.upper():15} {ok}/{total} OK | {structured}/{total} estructuradas")
    
    print(f"\n  TOTAL: {total_ok}/{total_tests} tests exitosos")
    print(f"  Estructuradas: {sum(sum(1 for r in v if r.get('structured')) for v in all_results.values())}/{total_tests}")
    
    return total_ok == total_tests


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)