"""GESTIA Database Layer.

SQLAlchemy 2.0 async engine, session management, and base model.
Multi-tenant ready with RLS (Row Level Security) support.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, declared_attr

from gestia_core.config import get_settings


settings = get_settings()

# --------------------------------------------
# ENGINE & SESSION
# --------------------------------------------

engine: AsyncEngine = create_async_engine(
    str(settings.DATABASE_URL),
    echo=settings.ENVIRONMENT == "development",
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database session."""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """Context manager for scripts/background tasks."""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize database: create extensions, tables."""
    from gestia_core.models import Base  # noqa: F401
    from sqlalchemy import text

    async with engine.begin() as conn:
        # Extensiones necesarias
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pgcrypto"))
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\""))
        # Crear tablas
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Close database connections."""
    await engine.dispose()


# --------------------------------------------
# BASE MODEL (Multi-tenant)
# --------------------------------------------

class Base(DeclarativeBase):
    """Base model with common fields and multi-tenant support."""

    @declared_attr.directive
    def __tablename__(cls) -> str:  # noqa: N805
        return cls.__name__.lower()

    # Sobrescrito en modelos que necesiten tenant_id
    pass


# --------------------------------------------
# MIXINS
# --------------------------------------------

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, String, UUID
from sqlalchemy.orm import Mapped, mapped_column


class TimestampMixin:
    """Created/Updated timestamps with timezone."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class UUIDMixin:
    """UUID primary key."""

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )


class TenantMixin:
    """Multi-tenant isolation via tenant_id + RLS.

    All models inheriting this MUST have tenant_id.
    RLS policies are created via Alembic migrations.
    """

    tenant_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        nullable=False,
        index=True,
        comment="Tenant (empresa) this record belongs to",
    )


# --------------------------------------------
# RLS HELPER (para migraciones Alembic)
# --------------------------------------------

def enable_rls(table_name: str) -> str:
    """Generate SQL to enable RLS on a table."""
    return f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY;"


def create_tenant_policy(
    table_name: str,
    policy_name: str,
    command: str = "ALL",
    using: str = "tenant_id = current_setting('app.current_tenant')::uuid",
) -> str:
    """Generate SQL for tenant isolation policy."""
    return f"""
CREATE POLICY {policy_name} ON {table_name}
    FOR {command}
    USING ({using});
"""


def create_tenant_policies(table_name: str) -> list[str]:
    """Generate standard CRUD policies for tenant isolation."""
    return [
        create_tenant_policy(table_name, f"{table_name}_select", "SELECT"),
        create_tenant_policy(table_name, f"{table_name}_insert", "INSERT"),
        create_tenant_policy(table_name, f"{table_name}_update", "UPDATE"),
        create_tenant_policy(table_name, f"{table_name}_delete", "DELETE"),
    ]


# --------------------------------------------
# EVENT: Set tenant_id on session (RLS context)
# --------------------------------------------

# Nota: AsyncSession no tiene evento 'before_flush'.
# El contexto RLS se establece manualmente en middleware/deps por request.
# Ver gestia_core.database.set_tenant_context()

def set_tenant_context(session, tenant_id: str) -> None:
    """Set app.current_tenant for RLS policies in current transaction.

    Usage: await set_tenant_context(session, tenant_id)
    """
    from sqlalchemy import text
    session.sync_session.execute(text("SET LOCAL app.current_tenant = :tid"), {"tid": tenant_id})