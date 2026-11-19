"""GESTIA Database Setup Script.

Usage:
    python scripts/setup_db.py           # Create tables
    python scripts/setup_db.py --seed    # Create tables + seed data
    python scripts/setup_db.py --reset   # Drop all tables and recreate
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from gestia_core.config import get_settings
from gestia_core.database import close_db, engine, init_db
from gestia_core.models import Base
from gestia_core.security import hash_password
from gestia_core.models import Empresa, Usuario
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def create_tables() -> None:
    """Create all tables."""
    print("Creating tables...")
    await init_db()
    print("Tables created successfully.")


async def drop_tables() -> None:
    """Drop all tables."""
    print("Dropping all tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    print("Tables dropped.")


async def seed_data() -> None:
    """Seed initial data."""
    print("Seeding initial data...")

    async with AsyncSession(engine) as session:
        # Create demo empresa
        empresa = Empresa(
            nif="B12345678",
            nombre="GESTIA Demo SL",
            nombre_comercial="GESTIA Demo",
            regimen_iva="general",
            periodicidad_iva="trimestral",
            epigrafe_iae="8411",
            cnae="6920",
            direccion="Calle Demo 123",
            codigo_postal="28001",
            municipio="Madrid",
            provincia="Madrid",
            estado="activa",
        )
        session.add(empresa)
        await session.flush()

        # Create admin user
        admin = Usuario(
            email="admin@gestia.app",
            password_hash=hash_password("admin123"),
            nombre="Admin",
            apellidos="GESTIA",
            tipo="admin",
            roles=["superadmin"],
            tenant_id=empresa.id,
            email_verificado=True,
            activo=True,
        )
        session.add(admin)

        # Create demo asesor
        asesor = Usuario(
            email="asesor@gestia.app",
            password_hash=hash_password("asesor123"),
            nombre="Juan",
            apellidos="Pérez Asesor",
            tipo="asesor",
            roles=["asesor_contable", "asesor_fiscal"],
            tenant_id=empresa.id,
            email_verificado=True,
            activo=True,
        )
        session.add(asesor)

        # Create demo cliente
        cliente = Usuario(
            email="cliente@demo.com",
            password_hash=hash_password("cliente123"),
            nombre="María",
            apellidos="García Cliente",
            tipo="cliente",
            roles=["cliente_titular"],
            tenant_id=empresa.id,
            email_verificado=True,
            activo=True,
        )
        session.add(cliente)

        await session.commit()

    print("Seed data created:")
    print(f"  Empresa: {empresa.nombre} (NIF: {empresa.nif})")
    print(f"  Admin: admin@gestia.app / admin123")
    print(f"  Asesor: asesor@gestia.app / asesor123")
    print(f"  Cliente: cliente@demo.com / cliente123")


async def reset_db() -> None:
    """Full reset: drop and recreate."""
    await drop_tables()
    await create_tables()
    await seed_data()


async def main():
    parser = argparse.ArgumentParser(description="GESTIA Database Setup")
    parser.add_argument("--seed", action="store_true", help="Seed initial data after creating tables")
    parser.add_argument("--reset", action="store_true", help="Drop all tables and recreate")
    parser.add_argument("--drop-only", action="store_true", help="Only drop tables")

    args = parser.parse_args()

    settings = get_settings()
    print(f"Environment: {settings.ENVIRONMENT}")
    print(f"Database: {settings.DATABASE_URL}")

    try:
        if args.drop_only:
            await drop_tables()
        elif args.reset:
            await reset_db()
        else:
            await create_tables()
            if args.seed:
                await seed_data()
    finally:
        await close_db()


if __name__ == "__main__":
    asyncio.run(main())