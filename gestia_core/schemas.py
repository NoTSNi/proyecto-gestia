"""GESTIA Schemas - Pydantic models for API validation."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, StringConstraints
from pydantic.config import ConfigDict

# Tipos reutilizables
UUIDStr = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")]
NIFStr = Annotated[str, StringConstraints(pattern=r"^[A-Z0-9]{9}$")]


# --------------------------------------------
# BASE SCHEMAS
# --------------------------------------------

class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class IDSchema(BaseSchema):
    id: UUIDStr


class TimestampSchema(BaseSchema):
    created_at: datetime
    updated_at: datetime


# --------------------------------------------
# TENANT SCHEMAS
# --------------------------------------------

class EmpresaBase(BaseSchema):
    nif: NIFStr
    nombre: str = Field(..., min_length=1, max_length=200)
    nombre_comercial: str | None = Field(None, max_length=200)
    regimen_iva: str = Field(default="general")
    periodicidad_iva: str = Field(default="trimestral")
    epigrafe_iae: str | None = Field(None, max_length=20)
    cnae: str | None = Field(None, max_length=10)
    direccion: str | None = Field(None, max_length=500)
    codigo_postal: str | None = Field(None, max_length=5)
    municipio: str | None = Field(None, max_length=100)
    provincia: str | None = Field(None, max_length=50)


class EmpresaCreate(EmpresaBase):
    pass


class EmpresaUpdate(BaseSchema):
    nombre: str | None = Field(None, min_length=1, max_length=200)
    nombre_comercial: str | None = Field(None, max_length=200)
    regimen_iva: str | None = None
    periodicidad_iva: str | None = None
    epigrafe_iae: str | None = Field(None, max_length=20)
    cnae: str | None = Field(None, max_length=10)
    direccion: str | None = Field(None, max_length=500)
    codigo_postal: str | None = Field(None, max_length=5)
    municipio: str | None = Field(None, max_length=100)
    provincia: str | None = Field(None, max_length=50)
    estado: str | None = None


class EmpresaResponse(EmpresaBase, IDSchema, TimestampSchema):
    estado: str
    fecha_alta: datetime
    fecha_baja: datetime | None
    erp_tipo: str | None
    erp_sync_activo: bool
    metadata_json: dict


# --------------------------------------------
# USER SCHEMAS
# --------------------------------------------

class UsuarioBase(BaseSchema):
    email: EmailStr
    nombre: str = Field(..., min_length=1, max_length=100)
    apellidos: str = Field(..., min_length=1, max_length=150)
    telefono: str | None = Field(None, max_length=20)
    tipo: str = Field(..., pattern=r"^(admin|asesor|cliente|empleado_cliente)$")
    roles: list[str] = Field(default=[])


class UsuarioCreate(UsuarioBase):
    password: str = Field(..., min_length=8, max_length=128)


class UsuarioUpdate(BaseSchema):
    email: EmailStr | None = None
    nombre: str | None = Field(None, min_length=1, max_length=100)
    apellidos: str | None = Field(None, min_length=1, max_length=150)
    telefono: str | None = Field(None, max_length=20)
    tipo: str | None = Field(None, pattern=r"^(admin|asesor|cliente|empleado_cliente)$")
    roles: list[str] | None = None
    activo: bool | None = None
    mfa_enabled: bool | None = None


class UsuarioResponse(UsuarioBase, IDSchema, TimestampSchema):
    tenant_id: UUIDStr
    activo: bool
    mfa_enabled: bool
    email_verificado: bool
    ultimo_acceso: datetime | None


class UsuarioLogin(BaseSchema):
    email: EmailStr
    password: str


class TokenResponse(BaseSchema):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshTokenRequest(BaseSchema):
    refresh_token: str


# --------------------------------------------
# DOCUMENT SCHEMAS
# --------------------------------------------

class DocumentoBase(BaseSchema):
    filename_original: str
    content_type: str
    size_bytes: int
    tipo: str
    fuente: str = "portal"


class DocumentoCreate(DocumentoBase):
    pass


class DocumentoResponse(DocumentoBase, IDSchema, TimestampSchema):
    tenant_id: UUIDStr
    filename_storage: str
    sha256: str
    bucket: str
    object_key: str
    version_id: str | None
    estado: str
    ocr_confidence: float | None
    ocr_engine: str | None
    metadatos_extraidos: dict
    chunks_count: int
    embeddings_model: str | None
    procesado_en: datetime | None
    error_procesamiento: str | None
    correlation_id: str | None


class DocumentoUploadResponse(BaseSchema):
    document_id: UUIDStr
    correlation_id: str
    estado: str
    estimated_processing_seconds: int
    tracking_url: str


# --------------------------------------------
# CALENDAR SCHEMAS
# --------------------------------------------

class CalendarioEventoBase(BaseSchema):
    titulo: str
    descripcion: str | None = None
    categoria: str
    tipo_evento: str
    fecha_inicio: datetime
    fecha_fin: datetime | None = None
    fecha_limite: datetime
    todo_el_dia: bool = False
    es_recurrente: bool = False
    regla_rrule: str | None = None
    anio_fiscal: int
    periodo: str | None = None
    requiere_accion: bool = True
    accion_sugerida: str | None = None


class CalendarioEventoCreate(CalendarioEventoBase):
    pass


class CalendarioEventoUpdate(BaseSchema):
    titulo: str | None = None
    descripcion: str | None = None
    estado: str | None = None
    requiere_accion: bool | None = None
    accion_sugerida: str | None = None


class CalendarioEventoResponse(CalendarioEventoBase, IDSchema, TimestampSchema):
    tenant_id: UUIDStr
    estado: str
    notificado_15d: bool
    notificado_7d: bool
    notificado_1d: bool
    notificado_dia: bool


# --------------------------------------------
# FISCAL SCHEMAS
# --------------------------------------------

class ModeloFiscalBase(BaseSchema):
    codigo_modelo: str
    nombre: str
    descripcion: str | None = None
    anio: int
    periodo: str
    fecha_inicio_periodo: datetime
    fecha_fin_periodo: datetime
    fecha_limite_presentacion: datetime


class ModeloFiscalCreate(ModeloFiscalBase):
    pass


class ModeloFiscalUpdate(BaseSchema):
    estado: str | None = None
    datos_calculados: dict | None = None
    xml_aeat: str | None = None
    presentado_en: datetime | None = None
    numero_justificante: str | None = None
    csv_aeat: str | None = None
    importe_pagar: Decimal | None = None
    pagado: bool | None = None
    fecha_pago: datetime | None = None
    metodo_pago: str | None = None
    errores_validacion: list[dict] | None = None


class ModeloFiscalResponse(ModeloFiscalBase, IDSchema, TimestampSchema):
    tenant_id: UUIDStr
    estado: str
    datos_calculados: dict
    xml_aeat: str | None
    xml_hash: str | None
    presentado_en: datetime | None
    numero_justificante: str | None
    csv_aeat: str | None
    importe_pagar: Decimal | None
    pagado: bool
    fecha_pago: datetime | None
    metodo_pago: str | None
    errores_validacion: list[dict]


# --------------------------------------------
# PAYROLL SCHEMAS
# --------------------------------------------

class NominaBase(BaseSchema):
    empleado_id: UUIDStr
    empleado_nombre: str
    empleado_nif: str
    empleado_naf: str | None = None
    anio: int
    mes: int
    tipo: str = "mensual"
    fecha_devengo_inicio: datetime
    fecha_devengo_fin: datetime
    fecha_pago: datetime | None = None
    datos_nomina: dict = {}


class NominaCreate(NominaBase):
    pass


class NominaUpdate(BaseSchema):
    datos_nomina: dict | None = None
    tc1_generado: bool | None = None
    tc1_datos: dict | None = None
    tc2_generado: bool | None = None
    tc2_datos: dict | None = None
    estado: str | None = None


class NominaResponse(NominaBase, IDSchema, TimestampSchema):
    tenant_id: UUIDStr
    tc1_generado: bool
    tc1_datos: dict | None
    tc2_generado: bool
    tc2_datos: dict | None
    estado: str


class ContratoBase(BaseSchema):
    empleado_id: UUIDStr
    empleado_nombre: str
    empleado_nif: str
    tipo_contrato: str
    codigo_contrato: str
    fecha_inicio: datetime
    fecha_fin: datetime | None = None
    fecha_fin_estimada: datetime | None = None
    jornada_tipo: str = "completa"
    jornada_horas_semana: float | None = None
    salario_base: Decimal
    complementos: dict = {}
    convenio_colectivo: str | None = None
    grupo_cotizacion: int = 1
    centro_trabajo: str | None = None
    ccc: str | None = None


class ContratoCreate(ContratoBase):
    pass


class ContratoUpdate(BaseSchema):
    fecha_fin: datetime | None = None
    jornada_tipo: str | None = None
    jornada_horas_semana: float | None = None
    salario_base: Decimal | None = None
    complementos: dict | None = None
    estado: str | None = None
    causa_baja: str | None = None


class ContratoResponse(ContratoBase, IDSchema, TimestampSchema):
    tenant_id: UUIDStr
    estado: str
    causa_baja: str | None


# --------------------------------------------
# MERCANTIL SCHEMAS
# --------------------------------------------

class LibroMercantilBase(BaseSchema):
    tipo_libro: str
    anio: int
    tomo: int | None = None
    folio_inicio: int | None = None
    folio_fin: int | None = None


class LibroMercantilCreate(LibroMercantilBase):
    pass


class LibroMercantilUpdate(BaseSchema):
    legalizado: bool | None = None
    fecha_legalizacion: datetime | None = None
    registro_mercantil: str | None = None
    numero_legalizacion: str | None = None
    deposito_cuentas: bool | None = None
    fecha_deposito: datetime | None = None
    ejercicio_deposito: int | None = None
    estado: str | None = None


class LibroMercantilResponse(LibroMercantilBase, IDSchema, TimestampSchema):
    tenant_id: UUIDStr
    legalizado: bool
    fecha_legalizacion: datetime | None
    registro_mercantil: str | None
    numero_legalizacion: str | None
    deposito_cuentas: bool
    fecha_deposito: datetime | None
    ejercicio_deposito: int | None
    estado: str


# --------------------------------------------
# ADMINISTRATIVO SCHEMAS
# --------------------------------------------

class EscritoAdministrativoBase(BaseSchema):
    tipo: str
    organo_destinatario: str
    referencia_expediente: str | None = None
    fecha_presentacion: datetime | None = None
    fecha_limite_respuesta: datetime | None = None
    fecha_resolucion: datetime | None = None
    asunto: str
    hechos: str | None = None
    fundamentos_derecho: str | None = None
    suplico: str | None = None


class EscritoAdministrativoCreate(EscritoAdministrativoBase):
    pass


class EscritoAdministrativoUpdate(BaseSchema):
    estado: str | None = None
    resultado: str | None = None
    fecha_resolucion: datetime | None = None
    fecha_presentacion: datetime | None = None


class EscritoAdministrativoResponse(EscritoAdministrativoBase, IDSchema, TimestampSchema):
    tenant_id: UUIDStr
    estado: str
    resultado: str | None
    documento_id: UUIDStr | None


# --------------------------------------------
# COMMON RESPONSE SCHEMAS
# --------------------------------------------

class PaginatedResponse(BaseModel):
    data: list
    meta: dict
    links: dict


class ErrorResponse(BaseModel):
    error: dict