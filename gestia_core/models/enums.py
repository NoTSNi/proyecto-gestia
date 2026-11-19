"""GESTIA Enums - All enumerations used across models."""

from enum import Enum as PyEnum


class TipoDocumento(str, PyEnum):
    FACTURA_EMITIDA = "factura_emitida"
    FACTURA_RECIBIDA = "factura_recibida"
    CONTRATO_LABORAL = "contrato_laboral"
    CONTRATO_MERCANTIL = "contrato_mercantil"
    CONTRATO_ARRENDAMIENTO = "contrato_arrendamiento"
    ESCRITURA_PUBLICA = "escritura_publica"
    ACTA_JUNTA = "acta_junta"
    LIBRO_DIARIO = "libro_diario"
    LIBRO_MAYOR = "libro_mayor"
    LIBRO_INVENTARIO = "libro_inventario"
    MODELO_303 = "modelo_303"
    MODELO_200 = "modelo_200"
    MODELO_111 = "modelo_111"
    MODELO_190 = "modelo_190"
    MODELO_347 = "modelo_347"
    MODELO_349 = "modelo_349"
    MODELO_390 = "modelo_390"
    NOMINA = "nomina"
    TC1_TC2 = "tc1_tc2"
    ESCRITO_ADMIN = "escrito_admin"
    LICENCIA = "licencia"
    SUBVENCION = "subvencion"
    RECURSO = "recurso"
    OTRO = "otro"


class EstadoDocumento(str, PyEnum):
    CUARENTENA = "cuarentena"
    PROCESANDO = "procesando"
    CLASIFICADO = "clasificado"
    INDEXADO = "indexado"
    ERROR = "error"
    ARCHIVADO = "archivado"


class TipoUsuario(str, PyEnum):
    ADMIN = "admin"
    ASESOR = "asesor"
    CLIENTE = "cliente"
    EMPLEADO_CLIENTE = "empleado_cliente"


class RolSistema(str, PyEnum):
    SUPERADMIN = "superadmin"
    ADMIN_ASESORIA = "admin_asesoria"
    ASESOR_MERCANTIL = "asesor_mercantil"
    ASESOR_ADMINISTRATIVO = "asesor_administrativo"
    ASESOR_CONTABLE = "asesor_contable"
    ASESOR_PERSONAL = "asesor_personal"
    CLIENTE_TITULAR = "cliente_titular"
    CLIENTE_EMPLEADO = "cliente_empleado"


class EstadoEmpresa(str, PyEnum):
    ACTIVA = "activa"
    INACTIVA = "inactiva"
    BAJA = "baja"
    EN_CONSTITUCION = "en_constitucion"
    EN_DISOLUCION = "en_disolucion"


class RegimenIVA(str, PyEnum):
    GENERAL = "general"
    SIMPLIFICADO = "simplificado"
    AGRICULTURA = "agricultura"
    RECARGO_EQUIVALENCIA = "recargo_equivalencia"
    EXENTO = "exento"


class PeriodicidadFiscal(str, PyEnum):
    MENSUAL = "mensual"
    TRIMESTRAL = "trimestral"
    ANUAL = "anual"


class EstadoModeloFiscal(str, PyEnum):
    BORRADOR = "borrador"
    VALIDADO = "validado"
    PRESENTADO = "presentado"
    PAGADO = "pagado"
    ERRORES = "errores"
    ANULADO = "anulado"


class TipoNomina(str, PyEnum):
    MENSUAL = "mensual"
    EXTRAORDINARIA = "extraordinaria"
    FINIQUITO = "finiquito"
    INDEMNIZACION = "indemnizacion"


class CanalNotificacion(str, PyEnum):
    EMAIL = "email"
    PORTAL = "portal"
    WHATSAPP = "whatsapp"
    SLACK = "slack"
    SMS = "sms"
    PUSH = "push"