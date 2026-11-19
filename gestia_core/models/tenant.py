"""GESTIA Tenant Models - Empresa, Usuario, RefreshToken."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, JSON
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from gestia_core.models.base import Base, TimestampMixin, UUIDMixin, TenantMixin
from gestia_core.models.enums import EstadoEmpresa, RolSistema, TipoUsuario, RegimenIVA, PeriodicidadFiscal

if TYPE_CHECKING:
    from gestia_core.models.document import Documento
    from gestia_core.models.calendar import CalendarioEvento
    from gestia_core.models.notifications import Notificacion
    from gestia_core.models.fiscal import ModeloFiscal
    from gestia_core.models.payroll import Nomina, Contrato
    from gestia_core.models.mercantil import LibroMercantil
    from gestia_core.models.administrativo import EscritoAdministrativo


class Empresa(Base, UUIDMixin, TimestampMixin):
    """Empresa cliente (tenant)."""

    __tablename__ = "empresas"

    # Identificación fiscal
    nif: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    nombre_comercial: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # Datos fiscales
    regimen_iva: Mapped[str] = mapped_column(String(30), default=RegimenIVA.GENERAL, nullable=False)
    periodicidad_iva: Mapped[str] = mapped_column(String(20), default=PeriodicidadFiscal.TRIMESTRAL, nullable=False)
    epigrafe_iae: Mapped[str | None] = mapped_column(String(20), nullable=True)
    cnae: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # Domicilio
    direccion: Mapped[str | None] = mapped_column(String(500), nullable=True)
    codigo_postal: Mapped[str | None] = mapped_column(String(5), nullable=True)
    municipio: Mapped[str | None] = mapped_column(String(100), nullable=True)
    provincia: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Configuración
    estado: Mapped[str] = mapped_column(String(30), default=EstadoEmpresa.ACTIVA, nullable=False)
    fecha_alta: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    fecha_baja: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Certificados digitales
    certificado_fnmt_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    certificado_fnmt_password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    certificado_aeat_path: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Integraciones externas
    erp_tipo: Mapped[str | None] = mapped_column(String(50), nullable=True)
    erp_api_key_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    erp_sync_activo: Mapped[bool] = mapped_column(Boolean, default=False)

    # Metadatos
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Relaciones
    usuarios: Mapped[list[Usuario]] = relationship(
        "Usuario",
        back_populates="empresa",
        lazy="selectin",
        primaryjoin="Empresa.id==Usuario.tenant_id",
    )
    documentos: Mapped[list[Documento]] = relationship(
        "Documento",
        back_populates="empresa",
        lazy="selectin",
        primaryjoin="Empresa.id==Documento.tenant_id",
    )
    eventos_calendario: Mapped[list[CalendarioEvento]] = relationship(
        "CalendarioEvento",
        back_populates="empresa",
        lazy="selectin",
        primaryjoin="Empresa.id==CalendarioEvento.tenant_id",
    )
    notificaciones: Mapped[list[Notificacion]] = relationship(
        "Notificacion",
        back_populates="empresa",
        lazy="selectin",
        primaryjoin="Empresa.id==Notificacion.tenant_id",
    )
    modelos_fiscales: Mapped[list[ModeloFiscal]] = relationship(
        "ModeloFiscal",
        back_populates="empresa",
        lazy="selectin",
        primaryjoin="Empresa.id==ModeloFiscal.tenant_id",
    )
    nominas: Mapped[list[Nomina]] = relationship(
        "Nomina",
        back_populates="empresa",
        lazy="selectin",
        primaryjoin="Empresa.id==Nomina.tenant_id",
    )
    contratos: Mapped[list[Contrato]] = relationship(
        "Contrato",
        back_populates="empresa",
        lazy="selectin",
        primaryjoin="Empresa.id==Contrato.tenant_id",
    )
    libros_mercantiles: Mapped[list[LibroMercantil]] = relationship(
        "LibroMercantil",
        back_populates="empresa",
        lazy="selectin",
        primaryjoin="Empresa.id==LibroMercantil.tenant_id",
    )
    escritos_admin: Mapped[list[EscritoAdministrativo]] = relationship(
        "EscritoAdministrativo",
        back_populates="empresa",
        lazy="selectin",
        primaryjoin="Empresa.id==EscritoAdministrativo.tenant_id",
    )

    __table_args__ = (
        Index("ix_empresas_nif_estado", "nif", "estado"),
    )


class Usuario(Base, UUIDMixin, TimestampMixin, TenantMixin):
    """Usuario del sistema (asesor, cliente, empleado)."""

    __tablename__ = "usuarios"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    apellidos: Mapped[str] = mapped_column(String(150), nullable=False)
    telefono: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Rol y permisos
    tipo: Mapped[str] = mapped_column(String(30), nullable=False)
    roles: Mapped[list[str]] = mapped_column(JSONB, default=list)

    # MFA / Passkeys
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    mfa_secret: Mapped[str | None] = mapped_column(String(255), nullable=True)
    webauthn_credentials: Mapped[list[dict]] = mapped_column(JSONB, default=list)

    # Estado
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    ultimo_acceso: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    email_verificado: Mapped[bool] = mapped_column(Boolean, default=False)
    email_verificado_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relaciones
    empresa: Mapped[Empresa] = relationship(
        "Empresa",
        back_populates="usuarios",
        lazy="selectin",
        primaryjoin="Usuario.tenant_id==Empresa.id",
    )

    __table_args__ = (
        Index("ix_usuarios_empresa_activo", "tenant_id", "activo"),
        Index("ix_usuarios_email_activo", "email", "activo"),
    )

    @property
    def nombre_completo(self) -> str:
        return f"{self.nombre} {self.apellidos}"

    def tiene_rol(self, rol: str) -> bool:
        return rol in self.roles


class RefreshToken(Base, UUIDMixin, TimestampMixin):
    """Refresh tokens rotativos para JWT."""

    __tablename__ = "refresh_tokens"

    token_hash: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    usuario_id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=False), ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False
    )
    expira_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revocado: Mapped[bool] = mapped_column(Boolean, default=False)
    revocado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ip: Mapped[str | None] = mapped_column(String(45), nullable=True)

    __table_args__ = (
        Index("ix_refresh_tokens_usuario_expira", "usuario_id", "expira_en"),
    )