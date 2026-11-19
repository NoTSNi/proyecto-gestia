"""GESTIA Agents - Contable Specialist."""

from __future__ import annotations

from agents.specialist_base import SpecialistBase, AgentContext, AgentResponse


class ContableAgent(SpecialistBase):
    """Agente especialista en contabilidad y fiscalidad."""

    name = "contable"
    description = "Especialista en IVA, IS, IRPF, modelos fiscales, contabilidad, cierres anuales"
    capabilities = [
        "modelo_303_iva",
        "modelo_390_anual",
        "modelo_200_is",
        "modelo_202_pagos_fraccionados",
        "modelo_111_irpf_retenciones",
        "modelo_190_resumen_anual",
        "modelo_347_operaciones_terceros",
        "modelo_349_intracomunitarias",
        "contabilidad_general",
        "cierre_ejercicio",
        "conciliacion_bancaria",
        "amortizaciones",
        "facturas_emitidas_recibidas",
    ]

    def can_handle(self, query: str) -> float:
        keywords = [
            "iva", "303", "390", "modelo 303", "modelo 390",
            "is", "impuesto sociedades", "200", "202", "pagos fraccionados",
            "irpf", "111", "190", "retenciones", "modelo 111", "modelo 190",
            "347", "349", "intracomunitarias", "operaciones terceros",
            "contabilidad", "asiento", "mayor", "diario", "balance", "pérdidas ganancias",
            "cierre", "ejercicio", "amortización", "amortizaciones",
            "factura", "facturas", "emitida", "recibida", "rectificativa",
            "conciliación", "banco", "bancaria",
            "trimestre", "trimestral", "anual", "anualidad",
        ]
        query_lower = query.lower()
        matches = sum(1 for kw in keywords if kw in query_lower)
        return min(0.95, 0.4 + matches * 0.1)

    async def process(self, query: str, context: AgentContext) -> AgentResponse:
        query_lower = query.lower()

        if any(kw in query_lower for kw in ["303", "iva trimestral", "iva q", "modelo 303"]):
            action = "modelo_303"
            response = "Preparo modelo 303 (IVA trimestral). Necesito: facturas emitidas/recibidas del trimestre, régimen IVA, deducciones. Genero XML AEAT y programo presentación."
        
        elif any(kw in query_lower for kw in ["390", "iva anual", "resumen anual iva"]):
            action = "modelo_390"
            response = "Genero modelo 390 (resumen anual IVA). Agrego los 4 trimestres, calculo totales, valido coherencia con 303s presentados."
        
        elif any(kw in query_lower for kw in ["200", "impuesto sociedades", "is ", "modelo 200"]):
            action = "modelo_200"
            response = "Preparo modelo 200 (Impuesto Sociedades). Necesito: cuentas anuales cerradas, ajustes extracontables, bases imponibles negativas, deducciones, retenciones."
        
        elif any(kw in query_lower for kw in ["202", "pagos fraccionados", "pago fraccionado"]):
            action = "modelo_202"
            response = "Calculo pagos fraccionados (modelo 202) - abril, octubre, diciembre. Base: cuota íntegra anterior o beneficio contable."
        
        elif any(kw in query_lower for kw in ["111", "retenciones", "irpf retenciones", "modelo 111"]):
            action = "modelo_111"
            response = "Genero modelo 111 (retenciones IRPF mensual/trimestral). Necesito: nóminas, facturas con retención, arrendamientos, premios."
        
        elif any(kw in query_lower for kw in ["190", "resumen anual", "modelo 190"]):
            action = "modelo_190"
            response = "Genero modelo 190 (resumen anual retenciones). Agrego todos los 111s del año, valido totales con certificaciones."
        
        elif any(kw in query_lower for kw in ["347", "operaciones terceros", "declaración informativa"]):
            action = "modelo_347"
            response = "Preparo modelo 347 (operaciones con terceros >3005.06€). Filtro facturas emitidas/recibidas, agrupo por NIF, genero fichero."
        
        elif any(kw in query_lower for kw in ["349", "intracomunitarias", "operaciones intracomunitarias"]):
            action = "modelo_349"
            response = "Preparo modelo 349 (operaciones intracomunitarias). Necesito: facturas UE (emitidas/recibidas), NIF-IVA válidos, diferenciando bienes/servicios."
        
        elif any(kw in query_lower for kw in ["cierre", "cierre ejercicio", "cerrar contabilidad"]):
            action = "cierre_ejercicio"
            response = "Ejecuto cierre contable: regularizaciones, amortizaciones, devengados, impuestos, apunte de cierre, apertura nuevo ejercicio."
        
        elif any(kw in query_lower for kw in ["conciliación", "conciliar", "banco", "bancaria"]):
            action = "conciliacion_bancaria"
            response = "Realizo conciliación bancaria: importo movimientos banco, cruzo con contabilidad, identifico diferencias, genero asientos de ajuste."
        
        else:
            action = "consulta_contable"
            response = "Especialista contable/fiscal a tu disposición. Modelos: 303, 390, 200, 202, 111, 190, 347, 349. Contabilidad, cierres, conciliaciones."

        return AgentResponse(
            agent=self.name,
            success=True,
            response=response,
            data={"action": action, "domain": "contable"},
            actions=[{"type": "info", "action": action}],
        )