"""GESTIA Agents - Contable Specialist (Enhanced)."""

from __future__ import annotations

from agents.enhanced_specialist_base import EnhancedSpecialistBase, ActionPlan, AgentContext, AgentResponse


class ContableAgent(EnhancedSpecialistBase):
    """Agente especialista en contabilidad y fiscalidad - Enhanced."""

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

    KEYWORDS = {
        "iva_trimestral": ["303", "iva trimestral", "iva q", "modelo 303"],
        "iva_anual": ["390", "iva anual", "resumen anual iva"],
        "is": ["200", "impuesto sociedades", "is ", "modelo 200"],
        "pagos_fracc": ["202", "pagos fraccionados", "pago fraccionado"],
        "irpf_ret": ["111", "retenciones", "irpf retenciones", "modelo 111"],
        "irpf_anual": ["190", "resumen anual", "modelo 190"],
        "terceros": ["347", "operaciones terceros", "declaración informativa"],
        "intracom": ["349", "intracomunitarias", "operaciones intracomunitarias"],
        "cierre": ["cierre", "cierre ejercicio", "cerrar contabilidad"],
        "conciliacion": ["conciliación", "conciliar", "banco", "bancaria"],
        "amortizacion": ["amortización", "amortizaciones"],
        "facturas": ["factura", "facturas", "emitida", "recibida", "rectificativa"],
    }

    def can_handle(self, query: str) -> float:
        import re
        query_lower = query.lower()
        matches = 0
        for cat, kws in self.KEYWORDS.items():
            for kw in kws:
                pattern = r"" + re.escape(kw) + r""
                if re.search(pattern, query_lower):
                    matches += 1
                    break
        return min(0.97, 0.4 + matches * 0.12)

    async def analyze(self, query: str, context: AgentContext) -> dict:
        query_lower = query.lower()
        action_type = "consulta_contable"
        params = {}
        req = []
        prod = []
        
        if any(kw in query_lower for kw in self.KEYWORDS["iva_trimestral"]):
            action_type = "modelo_303_iva"
            req = ["Facturas emitidas trimestre", "Facturas recibidas trimestre", "Régimen IVA", "Deducciones"]
            prod = ["Modelo 303 XML AEAT", "Recibo presentación", "Resumen IVA trimestre"]
            params["periodicidad"] = "trimestral"
        
        elif any(kw in query_lower for kw in self.KEYWORDS["iva_anual"]):
            action_type = "modelo_390_anual"
            req = ["4 modelos 303 presentados", "Totales anuales IVA", "Operaciones exentas"]
            prod = ["Modelo 390", "Validación coherencia 303s"]
        
        elif any(kw in query_lower for kw in self.KEYWORDS["is"]):
            action_type = "modelo_200_is"
            req = ["Cuentas anuales cerradas", "Ajustes extracontables", "Bases negativas", "Deducciones", "Retenciones"]
            prod = ["Modelo 200", "Autoliquidación IS", "Ingreso/Devolución"]
        
        elif any(kw in query_lower for kw in self.KEYWORDS["pagos_fracc"]):
            action_type = "modelo_202_pagos_fraccionados"
            req = ["Cuota íntegra anterior", "Beneficio contable", "Retenciones soportadas"]
            prod = ["Modelo 202 (abr/oct/dic)", "Calendario pagos"]
        
        elif any(kw in query_lower for kw in self.KEYWORDS["irpf_ret"]):
            action_type = "modelo_111_irpf_retenciones"
            req = ["Nóminas periodo", "Facturas con retención", "Arrendamientos", "Premios"]
            prod = ["Modelo 111", "Certificados retención"]
            params["periodicidad"] = "mensual" if "mensual" in query_lower else "trimestral"
        
        elif any(kw in query_lower for kw in self.KEYWORDS["irpf_anual"]):
            action_type = "modelo_190_resumen_anual"
            req = ["Todos modelos 111 año", "Certificaciones empleados", "Totales anuales"]
            prod = ["Modelo 190", "Certificados retenciones anuales"]
        
        elif any(kw in query_lower for kw in self.KEYWORDS["terceros"]):
            action_type = "modelo_347_terceros"
            req = ["Facturas emitidas >3005,06€", "Facturas recibidas >3005,06€", "Agrupación por NIF"]
            prod = ["Modelo 347", "Fichero AEAT"]
        
        elif any(kw in query_lower for kw in self.KEYWORDS["intracom"]):
            action_type = "modelo_349_intracom"
            req = ["Facturas UE emitidas", "Facturas UE recibidas", "NIF-IVA válidos", "Diferencia bienes/servicios"]
            prod = ["Modelo 349", "Fichero AEAT"]
        
        elif any(kw in query_lower for kw in self.KEYWORDS["cierre"]):
            action_type = "cierre_ejercicio"
            req = ["Balanza comprobación", "Facturas pendientes", "Devengados", "Amortizaciones", "Impuestos"]
            prod = ["Asientos regularización", "Asiento cierre", "Apertura nuevo ejercicio", "Cuentas anuales"]
        
        elif any(kw in query_lower for kw in self.KEYWORDS["conciliacion"]):
            action_type = "conciliacion_bancaria"
            req = ["Extractos bancarios", "Contabilidad auxiliar bancos", "Diferencias identificadas"]
            prod = ["Conciliación bancaria", "Asientos ajuste", "Informe diferencias"]
        
        elif any(kw in query_lower for kw in self.KEYWORDS["amortizacion"]):
            action_type = "amortizaciones"
            req = ["Inmovilizado material/intangible", "Tablas amortización", "Vidas útiles", "Valor residual"]
            prod = ["Cuadro amortizaciones", "Asientos mensuales", "Deducciones fiscales"]
        
        elif any(kw in query_lower for kw in self.KEYWORDS["facturas"]):
            action_type = "facturas_emitidas_recibidas"
            req = ["Facturas periodo", "Datos fiscales emisor/receptor", "Bases/IVA", "Num. serie"]
            prod = ["Libro facturas emitidas", "Libro facturas recibidas", "Resumen IVA"]
        
        return ActionPlan(action_type, query, 0.9, params, req, prod).to_dict()

    async def execute(self, analysis: dict, query: str, context: AgentContext) -> AgentResponse:
        action = analysis.get("action_type", "consulta_contable")
        params = analysis.get("parameters", {})
        req = analysis.get("requires_documents", [])
        client_ctx = await self.get_client_context(context.tenant_id)
        empresa = client_ctx.get("cliente_ejemplo", {}).get("empresa", {})
        
        responses = {
            "modelo_303_iva": {
                "summary": f"Preparo modelo 303 (IVA trimestral) para {empresa.get('nombre', 'la empresa')}. Necesito: facturas emitidas/recibidas del trimestre, régimen IVA (general/simplificado), prorrata si aplica, deducciones. Genero XML AEAT y programo presentación (20 días post-trimestre).",
                "next_steps": ["Recopilar facturas emitidas/recibidas trimestre", "Clasificar por tipo IVA (4%/10%/21%)", "Calcular IVA devengado - IVA deducible", "Rellenar casillas 303", "Generar XML y presentar AEAT"],
                "deadlines": [{"description": "Presentación 303", "date": "Días 1-20 mes post-trimestre"}],
                "citations": ["LIVA Art. 96-97", "ORDEN HFP/417/2017"],
            },
            "modelo_390_anual": {
                "summary": "Genero modelo 390 (resumen anual IVA). Agrego los 4 trimestres (303), valido coherencia totales, operaciones exentas, prorrata anual. Presentación: enero siguiente.",
                "next_steps": ["Recuperar 4 modelos 303 presentados", "Sumar bases y cuotas por tipo", "Verificar coherencia con contabilidad", "Generar 390 y presentar"],
                "deadlines": [{"description": "Presentación 390", "date": "Enero ejercicio siguiente (días 1-30)"}],
                "citations": ["LIVA Art. 98", "ORDEN HFP/417/2017"],
            },
            "modelo_200_is": {
                "summary": "Preparo modelo 200 (Impuesto Sociedades). Necesito: cuentas anuales cerradas, ajustes extracontables (gastos no deducibles, libertades amortización), bases imponibles negativas pendientes, deducciones I+D+i, retenciones soportadas. Plazo: 25 jul (o 20 jul si ingreso).",
                "next_steps": ["Cerrar contabilidad y formular cuentas", "Calcular ajustes extracontables", "Aplicar bases negativas y deducciones", "Determinar cuota líquida", "Generar 200 e ingresar/devolver"],
                "deadlines": [{"description": "Presentación 200", "date": "25 jul (20 jul si ingreso)"}],
                "citations": ["LIS Art. 120-124", "ORDEN HFP/1423/2015"],
            },
            "modelo_202_pagos_fraccionados": {
                "summary": "Calculo pagos fraccionados (modelo 202) - abril, octubre, diciembre. Base: cuota íntegra anterior (método 1) o beneficio contable (método 2). Mínimo 18% base. Retenciones soportadas reducen.",
                "next_steps": ["Elegir método cálculo", "Aplicar porcentaje (18%/24%/...)", "Restar retenciones", "Generar 202 y presentar"],
                "deadlines": [{"description": "Abril", "date": "1-20 abril"}, {"description": "Octubre", "date": "1-20 octubre"}, {"description": "Diciembre", "date": "1-20 diciembre"}],
                "citations": ["LIS Art. 40-41", "ORDEN HFP/1423/2015"],
            },
            "modelo_111_irpf_retenciones": {
                "summary": f"Genero modelo 111 (retenciones IRPF {'mensual' if params.get('periodicidad') == 'mensual' else 'trimestral'}) para {empresa.get('nombre', 'la empresa')}. Necesito: nóminas, facturas profesionales con retención, arrendamientos, premios. Genero certificados retención empleados/proveedores.",
                "next_steps": ["Recopilar nóminas y facturas periodo", "Sumar bases y retenciones por tipo", "Rellenar casillas 111", "Generar certificados retención", "Presentar AEAT"],
                "deadlines": [{"description": "Presentación 111", "date": "Días 1-20 mes post-periodo"}],
                "citations": ["LIRPF Art. 75-77", "RGLIRPF Art. 98-100"],
            },
            "modelo_190_resumen_anual": {
                "summary": "Genero modelo 190 (resumen anual retenciones). Agrego todos los 111s del año, valido totales con certificaciones expedidas. Presentación: enero siguiente.",
                "next_steps": ["Recuperar 12/4 modelos 111", "Sumar bases y retenciones", "Cruzar con certificaciones", "Generar 190"],
                "deadlines": [{"description": "Presentación 190", "date": "Enero ejercicio siguiente"}],
                "citations": ["LIRPF Art. 78", "RGLIRPF Art. 101"],
            },
            "modelo_347_terceros": {
                "summary": "Preparo modelo 347 (operaciones con terceros >3.005,06€/año). Filtro facturas emitidas/recibidas, agrupo por NIF, diferencio bienes/servicios/arrendamientos, genero fichero AEAT. Plazo: febrero siguiente.",
                "next_steps": ["Filtrar facturas >3.005,06€", "Agrupar por NIF cliente/proveedor", "Clasificar tipo operación", "Generar fichero TXT AEAT", "Presentar"],
                "deadlines": [{"description": "Presentación 347", "date": "Febrero ejercicio siguiente"}],
                "citations": ["RGLIRPF Art. 69", "ORDEN HAP/2175/2013"],
            },
            "modelo_349_intracom": {
                "summary": "Preparo modelo 349 (operaciones intracomunitarias). Necesito: facturas UE emitidas/recibidas, NIF-IVA validados (VIES), diferencio bienes (entregas/adquisiciones) vs servicios. Presentación mensual/trimestral.",
                "next_steps": ["Validar NIF-IVA en VIES", "Clasificar entregas/adquisiciones bienes", "Clasificar servicios prestados/recibidos", "Generar 349", "Presentar"],
                "deadlines": [{"description": "Presentación 349", "date": "Mensual (días 1-20) o trimestral"}],
                "citations": ["LIVA Art. 62-63", "RGLIVA Art. 78-79"],
            },
            "cierre_ejercicio": {
                "summary": "Ejecuto cierre contable: regularizaciones (devengados, anticipados), amortizaciones, provisiones, impuestos (IS, IVA diferido), apunte de cierre resultado, apertura nuevo ejercicio. Genero cuentas anuales (Balance, PyG, Memoria, ECN, EFE).",
                "next_steps": ["Contabilizar devengados/anticipados", "Calcular amortizaciones ejercicio", "Provisiones y deterioros", "Liquidar IS e IVA diferido", "Apunte cierre PyG", "Apertura ejercicio siguiente", "Formular cuentas anuales"],
                "deadlines": [{"description": "Formulación cuentas", "date": "3 meses post-cierre (31 mar)"}, {"description": "Aprobación junta", "date": "6 meses (30 jun)"}],
                "citations": ["CCom Art. 35-38", "PGC 2007", "LSC Art. 253"],
            },
            "conciliacion_bancaria": {
                "summary": "Realizo conciliación bancaria: importo movimientos banco (formato 43/58/Norma 19), cruzo con auxiliar contable (cuenta 572), identifico diferencias (cheques pendientes, comisiones, errores), genero asientos ajuste.",
                "next_steps": ["Descargar extractos bancarios", "Importar en contabilidad", "Cruzar movimientos", "Identificar diferencias", "Contabilizar ajustes", "Verificar saldo final"],
                "citations": ["CCom Art. 28", "NIC 7"],
            },
            "amortizaciones": {
                "summary": "Calculo amortizaciones: inmovilizado material (tablas oficiales LIS), intangible (vida útil 10 años máx salvo prueba), deducciones fiscales (libertad amortización art. 102 LIS, I+D+i). Genero cuadro anual y asientos mensuales.",
                "next_steps": ["Inventariar inmovilizado", "Asignar vidas útiles tablas", "Calcular cuota anual/mensual", "Aplicar incentivos fiscales", "Generar asientos"],
                "citations": ["LIS Art. 11-12", "PGC 2007", "Tablas amortización oficial"],
            },
            "facturas_emitidas_recibidas": {
                "summary": "Gestiono libros registro facturas emitidas/recibidas (SII si obligado, si no libro IVA). Verifico: num. serie, fecha, NIF, base, tipo IVA, cuota. Genero resumen IVA periodo para 303.",
                "next_steps": ["Verificar numeración correlativa", "Validar datos fiscales", "Clasificar por tipo IVA", "Generar libro IVA", "Resumen para 303"],
                "citations": ["RDFIVA Art. 62-65", "ORDEN HFP/417/2017 (SII)"],
            },
            "consulta_contable": {
                "summary": "Especialista contable/fiscal a tu disposición. Modelos: 303, 390, 200, 202, 111, 190, 347, 349. Contabilidad general, cierres, conciliaciones, amortizaciones, facturas.",
                "next_steps": ["Indica qué modelo o tarea necesitas"],
            },
        }
        
        resp = responses.get(action, responses["consulta_contable"])
        return self.build_response(
            action=action,
            summary=resp["summary"],
            next_steps=resp.get("next_steps", []),
            documents_needed=req,
            deadlines=resp.get("deadlines", []),
            citations=resp.get("citations", []),
            confidence=analysis.get("confidence", 0.9),
        )

__all__ = ["ContableAgent"]