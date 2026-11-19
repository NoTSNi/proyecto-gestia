"""GESTIA Shared - Calendar Deadlines (Fiscal, Laboral, Mercantil)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from gestia_core.models import CalendarioEvento


@dataclass
class DeadlineRule:
    tipo_evento: str
    categoria: str
    nombre: str
    descripcion: str
    periodicidad: str
    dia_mes: int | None = None
    dia_semana: int | None = None
    mes_fijo: int | None = None
    offset_dias: int = 0
    requiere_accion: bool = True
    accion_sugerida: str | None = None


FISCAL_RULES_2025 = [
    DeadlineRule("iva_303", "fiscal", "Modelo 303 - IVA Trimestral",
                 "Autoliquidación IVA trimestral", "trimestral",
                 dia_mes=20, accion_sugerida="Recopilar facturas, calcular IVA, generar modelo 303"),
    DeadlineRule("iva_390", "fiscal", "Modelo 390 - IVA Anual",
                 "Resumen anual IVA", "anual",
                 mes_fijo=1, dia_mes=30,
                 accion_sugerida="Consolidar 4 trimestres, validar, presentar 390"),
    DeadlineRule("irpf_111", "fiscal", "Modelo 111 - IRPF Retenciones",
                 "Retenciones trabajo/capital/arrendamientos", "mensual",
                 dia_mes=20,
                 accion_sugerida="Recopilar nóminas/facturas con retención, generar 111"),
    DeadlineRule("irpf_190", "fiscal", "Modelo 190 - Resumen Anual IRPF",
                 "Resumen anual retenciones", "anual",
                 mes_fijo=1, dia_mes=20,
                 accion_sugerida="Consolidar 111s, validar certificaciones, presentar 190"),
    DeadlineRule("is_200", "fiscal", "Modelo 200 - Impuesto Sociedades",
                 "Autoliquidación IS", "anual",
                 mes_fijo=7, dia_mes=25,
                 accion_sugerida="Cerrar contabilidad, ajustes, calcular IS, generar 200"),
    DeadlineRule("is_202_1", "fiscal", "Modelo 202 - Pago Fraccionado 1",
                 "1er pago fraccionado IS", "anual",
                 mes_fijo=4, dia_mes=20,
                 accion_sugerida="Calcular base, generar 202"),
    DeadlineRule("is_202_2", "fiscal", "Modelo 202 - Pago Fraccionado 2",
                 "2do pago fraccionado IS", "anual",
                 mes_fijo=10, dia_mes=20,
                 accion_sugerida="Calcular base, generar 202"),
    DeadlineRule("is_202_3", "fiscal", "Modelo 202 - Pago Fraccionado 3",
                 "3er pago fraccionado IS", "anual",
                 mes_fijo=12, dia_mes=20,
                 accion_sugerida="Calcular base, generar 202"),
    DeadlineRule("inf_347", "fiscal", "Modelo 347 - Operaciones Terceros",
                 "Declaración informativa >3005€", "anual",
                 mes_fijo=2, dia_mes=28,
                 accion_sugerida="Filtrar facturas >3005€, agrupar por NIF, generar 347"),
    DeadlineRule("inf_349", "fiscal", "Modelo 349 - Intracomunitarias",
                 "Operaciones intracomunitarias", "mensual",
                 dia_mes=20,
                 accion_sugerida="Recopilar facturas UE, validar NIF-IVA, generar 349"),
]

LABORAL_RULES_2025 = [
    DeadlineRule("tc1_tc2", "laboral", "TC1/TC2 - Liquidación Cuotas",
                 "Liquidación cuotas Seguridad Social", "mensual",
                 dia_mes=20,
                 accion_sugerida="Calcular bases, generar TC1/TC2, enviar RED"),
    DeadlineRule("altas_bajas", "laboral", "Altas/Bajas/Variaciones SS",
                 "Comunicación variaciones plantilla", "event_driven",
                 accion_sugerida="Comunicar en plazo (3 días) via sistema RED"),
]

MERCANTIL_RULES_2025 = [
    DeadlineRule("libros_legalizar", "mercantil", "Legalización Libros Oficiales",
                 "Legalizar Diario, Mayor, Inventario, Actas", "anual",
                 mes_fijo=4, dia_mes=30,
                 accion_sugerida="Generar asientos cierre, legalizar telemáticamente"),
    DeadlineRule("deposito_cuentas", "mercantil", "Depósito Cuentas Anuales",
                 "Depósito cuentas en Registro Mercantil", "anual",
                 mes_fijo=7, dia_mes=31,
                 accion_sugerida="Preparar balance, PyG, memoria, informe, depositar"),
]

ADMINISTRATIVO_RULES_2025 = [
    DeadlineRule("recurso_reposicion", "administrativo", "Recurso Reposición",
                 "Plazo 1 mes desde notificación", "event_driven",
                 accion_sugerida="Redactar y presentar recurso de reposición"),
    DeadlineRule("recurso_alzada", "administrativo", "Recurso Alzada",
                 "Plazo 1 mes desde resolución/desestimación", "event_driven",
                 accion_sugerida="Redactar y presentar recurso de alzada"),
]


def last_business_day(year: int, month: int) -> int:
    import calendar
    from datetime import date, timedelta
    last_day = calendar.monthrange(year, month)[1]
    d = date(year, month, last_day)
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d.day


class CalendarDeadlines:
    def __init__(self, db_session):
        self.db = db_session

    async def generate_year(self, tenant_id: str, year: int) -> list:
        events = []
        for rule in FISCAL_RULES_2025:
            events.extend(self._expand_rule(tenant_id, rule, year))
        for rule in LABORAL_RULES_2025:
            events.extend(self._expand_rule(tenant_id, rule, year))
        for rule in MERCANTIL_RULES_2025:
            events.extend(self._expand_rule(tenant_id, rule, year))
        for rule in ADMINISTRATIVO_RULES_2025:
            events.extend(self._expand_rule(tenant_id, rule, year))
        return events

    def _expand_rule(self, tenant_id: str, rule: DeadlineRule, year: int) -> list:
        from gestia_core.models import CalendarioEvento
        events = []

        if rule.periodicidad == "mensual":
            for month in range(1, 13):
                dia = rule.dia_mes or 20
                if rule.dia_mes == last_business_day:
                    dia = last_business_day(year, month)
                fecha_limite = datetime(year, month, dia, 23, 59, 59, tzinfo=timezone.utc)
                events.append(CalendarioEvento(
                    tenant_id=tenant_id,
                    titulo=rule.nombre,
                    descripcion=rule.descripcion,
                    categoria=rule.categoria,
                    tipo_evento=rule.tipo_evento,
                    fecha_limite=fecha_limite,
                    fecha_inicio=fecha_limite,
                    anio_fiscal=year,
                    periodo=f"M{month:02d}",
                    requiere_accion=rule.requiere_accion,
                    accion_sugerida=rule.accion_sugerida,
                ))

        elif rule.periodicidad == "trimestral":
            for q in range(1, 5):
                month = q * 3
                dia = rule.dia_mes or 20
                fecha_limite = datetime(year, month, dia, 23, 59, 59, tzinfo=timezone.utc)
                events.append(CalendarioEvento(
                    tenant_id=tenant_id,
                    titulo=f"{rule.nombre} Q{q}",
                    descripcion=rule.descripcion,
                    categoria=rule.categoria,
                    tipo_evento=rule.tipo_evento,
                    fecha_limite=fecha_limite,
                    fecha_inicio=fecha_limite,
                    anio_fiscal=year,
                    periodo=f"Q{q}",
                    requiere_accion=rule.requiere_accion,
                    accion_sugerida=rule.accion_sugerida,
                ))

        elif rule.periodicidad == "anual":
            month = rule.mes_fijo or 1
            dia = rule.dia_mes or 1
            fecha_limite = datetime(year, month, dia, 23, 59, 59, tzinfo=timezone.utc)
            events.append(CalendarioEvento(
                tenant_id=tenant_id,
                titulo=rule.nombre,
                descripcion=rule.descripcion,
                categoria=rule.categoria,
                tipo_evento=rule.tipo_evento,
                fecha_limite=fecha_limite,
                fecha_inicio=fecha_limite,
                anio_fiscal=year,
                periodo="ANUAL",
                requiere_accion=rule.requiere_accion,
                accion_sugerida=rule.accion_sugerida,
            ))

        return events

    async def sync_from_external(self, tenant_id: str, year: int) -> dict:
        return {"synced": 0, "source": "external"}

    async def get_upcoming(self, tenant_id: str, days: int = 30) -> list:
        from datetime import datetime, timezone, timedelta
        from sqlalchemy import select
        from gestia_core.models import CalendarioEvento

        now = datetime.now(timezone.utc)
        limit = now + timedelta(days=days)

        result = await self.db.execute(
            select(CalendarioEvento)
            .where(
                CalendarioEvento.tenant_id == tenant_id,
                CalendarioEvento.fecha_limite >= now,
                CalendarioEvento.fecha_limite <= limit,
                CalendarioEvento.estado == "pendiente",
            )
            .order_by(CalendarioEvento.fecha_limite.asc())
        )
        return result.scalars().all()