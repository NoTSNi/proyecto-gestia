"""GESTIA Base Model - SQLAlchemy 2.0 declarative base with mixins."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import DateTime, String, UUID, event
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class Base(DeclarativeBase):
    """Base model with common configuration."""

    @declared_attr.directive
    def __tablename__(cls) -> str:  # noqa: N805
        return cls.__name__.lower()


class UUIDMixin:
    """UUID primary key."""

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )


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
# RLS HELPERS (para migraciones Alembic)
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
# EVENT: Set tenant context for RLS
# --------------------------------------------

def set_tenant_context(session: "AsyncSession", tenant_id: str) -> None:
    """Set app.current_tenant for RLS policies in current transaction.

    Usage: await set_tenant_context(session, tenant_id)
    """
    from sqlalchemy import text
    session.sync_session.execute(text("SET LOCAL app.current_tenant = :tid"), {"tid": tenant_id})