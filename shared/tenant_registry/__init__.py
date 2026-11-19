"""GESTIA Shared - Tenant Registry (Multi-tenant management)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import uuid4

if TYPE_CHECKING:
    from gestia_core.models import Empresa, Usuario
    from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class TenantConfig:
    """Configuration for a new tenant."""
    nif: str
    nombre: str
    nombre_comercial: str | None = None
    regimen_iva: str = "general"
    periodicidad_iva: str = "trimestral"
    epigrafe_iae: str | None = None
    cnae: str | None = None
    direccion: str | None = None
    codigo_postal: str | None = None
    municipio: str | None = None
    provincia: str | None = None
    admin_email: str | None = None
    admin_password: str | None = None


class TenantRegistry:
    """Multi-tenant registry with isolation and onboarding."""

    def __init__(self, db: "AsyncSession"):
        self.db = db

    async def create_tenant(self, config: TenantConfig) -> Empresa:
        """Create new tenant with admin user."""
        from gestia_core.models import Empresa, Usuario
        from gestia_core.security import hash_password
        from gestia_core.utils import validate_nif

        if not validate_nif(config.nif):
            raise ValueError("Invalid NIF/CIF")

        # Check unique
        from sqlalchemy import select
        result = await self.db.execute(select(Empresa).where(Empresa.nif == config.nif.upper()))
        if result.scalar_one_or_none():
            raise ValueError("NIF already registered")

        # Create empresa
        empresa = Empresa(
            nif=config.nif.upper(),
            nombre=config.nombre,
            nombre_comercial=config.nombre_comercial,
            regimen_iva=config.regimen_iva,
            periodicidad_iva=config.periodicidad_iva,
            epigrafe_iae=config.epigrafe_iae,
            cnae=config.cnae,
            direccion=config.direccion,
            codigo_postal=config.codigo_postal,
            municipio=config.municipio,
            provincia=config.provincia,
            estado="activa",
        )
        self.db.add(empresa)
        await self.db.flush()

        # Create admin user if provided
        if config.admin_email:
            admin = Usuario(
                email=config.admin_email,
                password_hash=hash_password(config.admin_password or "changeme123"),
                nombre="Admin",
                apellidos=config.nombre,
                tipo="admin",
                roles=["admin_asesoria"],
                tenant_id=empresa.id,
                email_verificado=True,
                activo=True,
            )
            self.db.add(admin)

        # Initialize tenant-specific data
        await self._initialize_tenant_data(empresa.id)

        await self.db.commit()
        await self.db.refresh(empresa)
        return empresa

    async def _initialize_tenant_data(self, tenant_id: str):
        """Initialize default data for new tenant."""
        from shared.calendar_deadlines import CalendarDeadlines

        # Generate calendar for current and next year
        calendar = CalendarDeadlines(self.db)
        current_year = datetime.now(timezone.utc).year
        for year in [current_year, current_year + 1]:
            events = await calendar.generate_year(tenant_id, year)
            for event in events:
                self.db.add(event)

        # TODO: Create default document folders in MinIO
        # TODO: Initialize default notification templates

    async def get_tenant(self, tenant_id: str) -> Empresa | None:
        from sqlalchemy import select
        from gestia_core.models import Empresa
        result = await self.db.execute(select(Empresa).where(Empresa.id == tenant_id))
        return result.scalar_one_or_none()

    async def get_tenant_by_nif(self, nif: str) -> Empresa | None:
        from sqlalchemy import select
        from gestia_core.models import Empresa
        result = await self.db.execute(select(Empresa).where(Empresa.nif == nif.upper()))
        return result.scalar_one_or_none()

    async def list_tenants(
        self,
        estado: str | None = None,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[Empresa], int]:
        from sqlalchemy import select, func
        from gestia_core.models import Empresa

        query = select(Empresa)
        if estado:
            query = query.where(Empresa.estado == estado)

        # Count
        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query) or 0

        # Paginate
        query = query.offset((page - 1) * per_page).limit(per_page)
        result = await self.db.execute(query)
        return result.scalars().all(), total

    async def update_tenant(self, tenant_id: str, **kwargs) -> Empresa | None:
        from gestia_core.models import Empresa
        empresa = await self.get_tenant(tenant_id)
        if not empresa:
            return None

        for key, value in kwargs.items():
            if hasattr(empresa, key):
                setattr(empresa, key, value)

        await self.db.commit()
        await self.db.refresh(empresa)
        return empresa

    async def deactivate_tenant(self, tenant_id: str) -> bool:
        from datetime import datetime, timezone
        from gestia_core.models import Empresa

        empresa = await self.get_tenant(tenant_id)
        if not empresa:
            return False

        empresa.estado = "baja"
        empresa.fecha_baja = datetime.now(timezone.utc)
        await self.db.commit()
        return True

    async def reactivate_tenant(self, tenant_id: str) -> bool:
        from gestia_core.models import Empresa

        empresa = await self.get_tenant(tenant_id)
        if not empresa:
            return False

        empresa.estado = "activa"
        empresa.fecha_baja = None
        await self.db.commit()
        return True

    async def get_tenant_users(self, tenant_id: str) -> list[Usuario]:
        from sqlalchemy import select
        from gestia_core.models import Usuario
        result = await self.db.execute(
            select(Usuario).where(Usuario.tenant_id == tenant_id)
        )
        return result.scalars().all()

    async def create_user(
        self,
        tenant_id: str,
        email: str,
        password: str,
        nombre: str,
        apellidos: str,
        tipo: str,
        roles: list[str],
    ) -> Usuario:
        from gestia_core.models import Usuario
        from gestia_core.security import hash_password

        user = Usuario(
            email=email,
            password_hash=hash_password(password),
            nombre=nombre,
            apellidos=apellidos,
            tipo=tipo,
            roles=roles,
            tenant_id=tenant_id,
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user