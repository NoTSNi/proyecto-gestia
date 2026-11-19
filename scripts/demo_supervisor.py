"""GESTIA Demo Supervisor - Test multi-agent orchestration."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from gestia_core.config import get_settings
from gestia_core.database import close_db, init_db
from agents.supervisor import SupervisorAgent
from agents.specialists import (
    MercantilAgent,
    AdministrativoAgent,
    ContableAgent,
    PersonalAgent,
)


async def demo():
    """Run demo of multi-agent system."""
    settings = get_settings()
    print(f"GESTIA Demo - {settings.APP_NAME} v{settings.APP_VERSION}")
    print("=" * 60)

    # Initialize DB
    await init_db()
    print("✓ Database initialized")

    # Create agents
    print("\n🤖 Initializing agents...")

    mercantil = MercantilAgent()
    administrativo = AdministrativoAgent()
    contable = ContableAgent()
    personal = PersonalAgent()

    supervisor = SupervisorAgent(
        specialists={
            "mercantil": mercantil,
            "administrativo": administrativo,
            "contable": contable,
            "personal": personal,
        }
    )

    print("✓ All agents initialized")

    # Demo queries
    demo_queries = [
        {
            "query": "Necesito constituir una SL con 3 socios, capital 3000€, actividad consultoría",
            "tenant_id": "demo-tenant-id",
            "expected_agent": "mercantil",
        },
        {
            "query": "Calcula el modelo 303 del Q1 2025 para mi empresa",
            "tenant_id": "demo-tenant-id",
            "expected_agent": "contable",
        },
        {
            "query": "Prepara la nómina de marzo para el empleado Juan García, salario base 1800€",
            "tenant_id": "demo-tenant-id",
            "expected_agent": "personal",
        },
        {
            "query": "Presenta recurso de reposición contra liquidación de IVA 2024",
            "tenant_id": "demo-tenant-id",
            "expected_agent": "administrativo",
        },
        {
            "query": "¿Cuáles son los plazos fiscales del próximo mes?",
            "tenant_id": "demo-tenant-id",
            "expected_agent": "calendar",
        },
    ]

    print("\n📋 Running demo queries...")
    print("-" * 60)

    for i, demo in enumerate(demo_queries, 1):
        print(f"\n{i}. Query: {demo['query']}")
        print(f"   Expected agent: {demo['expected_agent']}")

        try:
            result = await supervisor.process(
                query=demo["query"],
                tenant_id=demo["tenant_id"],
                user_id="demo-user-id",
            )
            print(f"   ✓ Routed to: {result.get('agent', 'unknown')}")
            print(f"   Response: {result.get('response', 'No response')[:200]}...")
        except Exception as e:
            print(f"   ✗ Error: {e}")

    print("\n" + "=" * 60)
    print("Demo completed!")

    await close_db()


if __name__ == "__main__":
    asyncio.run(demo())