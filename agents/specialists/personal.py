"""GESTIA Agents - Personal Specialist (Enhanced)."""

from __future__ import annotations

from agents.enhanced_specialist_base import EnhancedSpecialistBase, ActionPlan, AgentContext, AgentResponse


class PersonalAgent(EnhancedSpecialistBase):
    """Agente especialista en laboral y nóminas - Enhanced."""

    name = "personal"
    description = "Especialista en nóminas, contratos, Seguridad Social, absentismo, PRL, IRPF retenciones"
    capabilities = [
        "nomina_mensual",
        "nomina_extraordinaria",
        "finiquito",
        "indemnizacion",
        "contrato_indefinido",
        "contrato_temporal",
        "contrato_formacion",
        "contrato_practicas",
        "tc1_tc2",
        "altas_bajas_ss",
        "variacion_datos_ss",
        "absentismo",
        "it_baja_medica",
        "maternidad_paternidad",
        "prl_evaluacion_riesgos",
        "plan_prevencion",
        "irpf_retenciones_nomina",
        "certificados_empresa",
    ]

    KEYWORDS = {
        "nomina": ["nómina", "nomina", "sueldo", "salario", "paga", "extra", "finiquito"],
        "contratos": ["contrato", "indefinido", "temporal", "formación", "prácticas", "fijo discontinuo"],
        "ss": ["seguridad social", "ss ", "tc1", "tc2", "alta", "baja", "variación", "ccc"],
        "naf": ["naf", "afiliación", "cotización", "base cotización", "grupo cotización"],
        "absentismo": ["absentismo", "baja médica", "it ", "incapacidad", "maternidad", "paternidad"],
        "prl": ["prl", "prevención", "riesgos", "evaluación", "plan prevención"],
        "irpf_nomina": ["irpf nómina", "retención nómina", "tipo retención"],
        "certificados": ["certificado empresa", "certificado retenciones"],
        "empleado": ["empleado", "trabajador", "personal"],
        "convenio": ["convenio", "categoría", "grupo profesional"],
    }

    def can_handle(self, query: str) -> float:
        query_lower = query.lower()
        matches = 0
        for cat, kws in self.KEYWORDS.items():
            matches += sum(1 for kw in kws if kw in query_lower)
        return min(0.97, 0.4 + matches * 0.1)

    async def analyze(self, query: str, context: AgentContext) -> dict:
        query_lower = query.lower()
        action_type = "consulta_personal"
        params = {}
        req = []
        prod = []
        
        if any(kw in query_lower for kw in self.KEYWORDS["nomina"]):
            if "extra" in query_lower or "extraordinaria" in query_lower:
                action_type = "nomina_extraordinaria"
                req = ["Convenio colectivo", "Salario base", "Antigüedad", "Prorrateo sí/no"]
                prod = ["Nómina extraordinaria", "Recibo salarios"]
                params["tipo"] = "extraordinaria"
            elif "finiquito" in query_lower:
                action_type = "finiquito"
                req = ["Fecha extinción", "Salario diario", "Días pendientes", "Vacaciones no disfrutadas", "Pagas extra"]
                prod = ["Finiquito", "Recibo finiquito", "Certificado empresa"]
            else:
                action_type = "nomina_mensual"
                req = ["Datos empleado", "Salario base", "Complementos", "Horas extra", "IRPF", "Base SS", "CCC"]
                prod = ["Recibo nómina", "TC1/TC2", "Transferencias"]
                params["tipo"] = "mensual"
        
        elif any(kw in query_lower for kw in self.KEYWORDS["contratos"]):
            if "indefinido" in query_lower:
                action_type = "contrato_indefinido"
                req = ["Datos empleado", "Categoría/grupo", "Salario", "Jornada", "Convenio", "Centro trabajo"]
                prod = ["Contrato indefinido", "Comunicación SEPE", "Alta SS"]
            elif "temporal" in query_lower or "duración determinada" in query_lower:
                action_type = "contrato_temporal"
                req = ["Causa temporal (obra/servicio/eventual/interinidad)", "Duración", "Datos empleado"]
                prod = ["Contrato temporal", "Comunicación SEPE", "Alta SS"]
            elif "formación" in query_lower or "prácticas" in query_lower:
                action_type = "contrato_formacion"
                req = ["Titulación", "Edad (16-30)", "Tutor", "Plan formativo", "Duración (6m-3a)"]
                prod = ["Contrato formativo/prácticas", "Comunicación SEPE", "Alta SS"]
            else:
                action_type = "contrato_generico"
                req = ["Necesidad empresarial", "Duración estimada"]
                prod = ["Asesoría tipo contrato"]
        
        elif any(kw in query_lower for kw in self.KEYWORDS["ss"]):
            if "tc1" in query_lower or "tc2" in query_lower or "liquidación" in query_lower:
                action_type = "tc1_tc2"
                req = ["Nóminas mes", "Bases cotización", "Tipos aportación", "CCC", "NAF trabajadores"]
                prod = ["TC1 (liquidación)", "TC2 (relación nominal)", "Recibo ingreso SS"]
            else:
                action_type = "altas_bajas_ss"
                req = ["TA.1/TA.2", "Datos trabajador", "CCC", "NAF", "Fecha efectos"]
                prod = ["Alta/Baja/Variación SS", "Comunicación INSS", "Recibo"]
        
        elif any(kw in query_lower for kw in self.KEYWORDS["absentismo"]):
            if "maternidad" in query_lower or "paternidad" in query_lower:
                action_type = "maternidad_paternidad"
                req = ["Fecha parto", "Certificado médico", "Base reguladora", "Tipo jornada"]
                prod = ["Solicitud prestación", "Comunicación empresa", "Certificado retenciones"]
            else:
                action_type = "absentismo"
                req = ["Parte baja/confirmación/alta", "Comunicación INSS", "Base reguladora"]
                prod = ["Gestión IT", "Prestación", "Cotización durante IT"]
        
        elif any(kw in query_lower for kw in self.KEYWORDS["prl"]):
            action_type = "prl_evaluacion_riesgos"
            req = ["Identificación puestos", "Factores riesgo", "Evaluación inicial", "Plan prevención"]
            prod = ["Evaluación riesgos", "Plan prevención", "Planificación actividad preventiva"]
        
        elif any(kw in query_lower for kw in self.KEYWORDS["irpf_nomina"]):
            action_type = "irpf_retenciones_nomina"
            req = ["Situación personal/familiar", "Rendimientos trabajo", "Base retención", "Tipo aplicable"]
            prod = ["Tipo retención calculado", "Modelo 145", "Comunicación trabajador"]
        
        elif any(kw in query_lower for kw in self.KEYWORDS["certificados"]):
            action_type = "certificados_empresa"
            req = ["Datos trabajador", "Periodo", "Retenciones", "Bases SS"]
            prod = ["Certificado empresa", "Certificado retenciones IRPF", "Certificado bases SS"]
        
        return ActionPlan(action_type, query, 0.9, params, req, prod).to_dict()

    async def execute(self, analysis: dict, query: str, context: AgentContext) -> AgentResponse:
        action = analysis.get("action_type", "consulta_personal")
        params = analysis.get("parameters", {})
        req = analysis.get("requires_documents", [])
        client_ctx = await self.get_client_context(context.tenant_id)
        empresa = client_ctx.get("cliente_ejemplo", {}).get("empresa", {})
        empleados = client_ctx.get("cliente_ejemplo", {}).get("empleados", [])
        
        responses = {
            "nomina_mensual": {
                "summary": f"Calculo nómina mensual para {empresa.get('nombre', 'la empresa')}. Necesito: empleado, salario base, complementos (convenio), horas extra, IRPF (modelo 145), base SS (tope máx/mín), CCC. Genero recibo firmado, TC1/TC2 y orden transferencia.",
                "next_steps": ["Recopilar datos variables mes (horas extra, pluses)", "Aplicar convenio colectivo vigente", "Calcular base SS e IRPF", "Generar recibo salarios", "Emitir TC1/TC2 y presentar SS", "Ordenar transferencia"],
                "deadlines": [{"description": "Pago nómina", "date": "Según convenio (habitual 1-5 mes siguiente)"}, {"description": "TC1/TC2", "date": "Último día mes natural siguiente"}],
                "citations": ["ET Art. 29", "RDL 8/2015", "Convenio colectivo aplicable"],
            },
            "nomina_extraordinaria": {
                "summary": f"Preparo nómina extraordinaria (verano/navidad) para {empresa.get('nombre', 'la empresa')}. Base: convenio o acuerdo empresa. Prorrateo: sí/no. Genero recibo y TC1/TC2 correspondientes.",
                "next_steps": ["Verificar convenio: número pagas extra", "Calcular base (salario base + complementos fijos)", "Aplicar prorrateo si procede", "Generar recibo extraordinaria", "Incluir en TC1/TC2 mes correspondiente"],
                "deadlines": [{"description": "Pago paga extra", "date": "Verano (jun-jul) / Navidad (dic)"}],
                "citations": ["ET Art. 31", "Convenio colectivo"],
            },
            "finiquito": {
                "summary": "Calculo finiquito: días salario pendientes + parte proporcional pagas extra + vacaciones no disfrutadas + indemnización si despido. Entrega en acto de conciliación o fin contrato.",
                "next_steps": ["Calcular días trabajados no pagados", "Proporcional pagas extra (devengadas)", "Vacaciones no disfrutadas (2,5 días/mes)", "Indemnización si procede (20/33 días/año)", "Entregar finiquito firmado", "Certificado empresa para paro"],
                "deadlines": [{"description": "Entrega finiquito", "date": "Día extinción contrato"}],
                "citations": ["ET Art. 49", "ET Art. 56"],
            },
            "contrato_indefinido": {
                "summary": f"Redacto contrato indefinido para {empresa.get('nombre', 'la empresa')}: ordinario, apoyo emprendedores (bonificaciones), discapacidad (>33%), >52 años, fijo-discontinuo. Necesito: categoría/grupo profesional, salario, jornada, convenio, centro trabajo.",
                "next_steps": ["Definir tipo indefinido según perfil", "Rellenar modelo oficial SEPE", "Firmar trabajador + empresa", "Comunicar alta SEPE (3 días)", "Dar alta SS (TA.1)", "Entregar copia trabajador"],
                "deadlines": [{"description": "Comunicación SEPE", "date": "10 días (3 días telemático)"}, {"description": "Alta SS", "date": "Antes inicio actividad"}],
                "citations": ["ET Art. 15-16", "RD 2720/1998", "Ley 3/2012 emprendedores"],
            },
            "contrato_temporal": {
                "summary": "Redacto contrato temporal: obra/servicio (causa objetiva), eventual (incremento tareas), interinidad (sustitución), formación. Causa justificada obligatoria. Duración máx: 6m-3a (obra/servicio), 6m-1a (eventual).",
                "next_steps": ["Identificar causa temporal real", "Rellenar modelo oficial (causa + duración)", "Firmar + comunicar SEPE (3 días)", "Alta SS", "Controlar duración máxima"],
                "deadlines": [{"description": "Comunicación SEPE", "date": "10 días (3 días telemático)"}, {"description": "Duración máx obra/servicio", "date": "3 años (prórrogas incl.)"}],
                "citations": ["ET Art. 15", "RD 2720/1998", "Ley 3/2012"],
            },
            "contrato_formacion": {
                "summary": "Redacto contrato formativo/prácticas: formativo (16-30 años, sin titulación, tutor, plan formativo, 6m-3a) o prácticas (titulación <5 años, 6m-2a). Bonificaciones SS significativas.",
                "next_steps": ["Verificar requisitos edad/titulación", "Diseñar plan formativo", "Asignar tutor empresa", "Rellenar modelo SEPE", "Comunicar alta + bonificaciones SS"],
                "deadlines": [{"description": "Duración formativo", "date": "6 meses - 3 años"}, {"description": "Duración prácticas", "date": "6 meses - 2 años"}],
                "citations": ["ET Art. 11", "RD 1529/2012", "Ley 3/2012"],
            },
            "tc1_tc2": {
                "summary": f"Genero TC1 (liquidación cuotas) y TC2 (relación nominal) para {empresa.get('nombre', 'la empresa')}. Envío sistema RED (SILTRA), obtengo recibo ingreso. Plazo: último día mes natural siguiente. Tipos: contingencias comunes 23,60% (empresa) + 4,70% (trab), desempleo 5,50%/1,50%, FOGASA 0,20%, FP 0,60%/0,10%.",
                "next_steps": ["Calcular bases cotización todos trabajadores", "Aplicar tipos cotización vigentes", "Generar fichero TC1/TC2 (SILTRA)", "Enviar sistema RED", "Verificar recibo ingreso", "Conciliar con contabilidad"],
                "deadlines": [{"description": "Presentación TC1/TC2", "date": "Último día mes natural siguiente"}],
                "citations": ["LGSS Art. 108-110", "ORDEN TAS/2024/2023"],
            },
            "altas_bajas_ss": {
                "summary": "Tramito alta/baja/variación en Seguridad Social: TA.1 (alta), TA.2 (baja), variación datos (categoría, jornada, centro trabajo). Comunicación inmediata sistema RED. Plazos: alta (antes inicio), baja (3 días), variación (3 días).",
                "next_steps": ["Rellenar modelo TA.1/TA.2 oficial", "Enviar sistema RED (SILTRA/CRETA)", "Verificar recibo comunicación", "Entregar copia trabajador (baja)"],
                "deadlines": [{"description": "Alta SS", "date": "Antes inicio actividad"}, {"description": "Baja SS", "date": "3 días desde cese"}, {"description": "Variación", "date": "3 días"}],
                "citations": ["LGSS Art. 20-22", "RD 84/1996"],
            },
            "absentismo": {
                "summary": "Gestión IT (incapacidad temporal): parte baja (médico), confirmaciones (7/14 días), alta (médico). Comunicación empresa → INSS (3 días). Prestación: 60% base reguladora (días 4-20), 75% (día 21+). Cotización empresa durante IT (contingencias comunes).",
                "next_steps": ["Recibir parte baja trabajador", "Comunicar INSS (3 días)", "Controlar partes confirmación", "Recibir parte alta", "Calcular prestación + cotización empresa", "Pagar delegado de pago si >365 días"],
                "deadlines": [{"description": "Comunicación INSS", "date": "3 días desde parte baja"}, {"description": "Prestación 60%", "date": "Días 4-20"}, {"description": "Prestación 75%", "date": "Día 21 en adelante"}],
                "citations": ["LGSS Art. 169-177", "RD 625/2014"],
            },
            "maternidad_paternidad": {
                "summary": "Permiso nacimiento/cuidado menor: 16 semanas (6 obligatorias post-parto madre, 10 voluntarias repartidas). Prestación 100% base reguladora. Cotización empresa durante permiso. Paternidad: 16 semanas (6 obligatorias, 10 voluntarias).",
                "next_steps": ["Comunicar embarazo/parto empresa", "Solicitar prestación INSS", "Calcular base reguladora", "Cotizar durante permiso (empresa)", "Planificar reincorporación"],
                "deadlines": [{"description": "Duración total", "date": "16 semanas"}, {"description": "Obligatorias madre", "date": "6 semanas post-parto"}],
                "citations": ["ET Art. 48", "LGSS Art. 177", "RD 1/2019"],
            },
            "prl_evaluacion_riesgos": {
                "summary": "Evaluación riesgos laborales (LPRL 31/1995): identificación peligros, evaluación riesgos (probabilidad x gravedad), planificación prevención (medidas técnicas/organizativas/PPE), vigilancia salud, formación, información. Revisar anualmente o tras cambios.",
                "next_steps": ["Identificar puestos y tareas", "Detectar peligros (físicos, químicos, biológicos, ergonómicos, psicosociales)", "Evaluar riesgos (matriz)", "Definir medidas: eliminar/sustituir/colectivas/individuales", "Redactar plan prevención", "Formar e informar trabajadores", "Programar vigilancia salud"],
                "deadlines": [{"description": "Revisión anual", "date": "Cada 12 meses"}, {"description": "Tras cambios", "date": "Inmediato"}],
                "citations": ["LPRL Art. 16-19", "RD 39/1997", "Guías técnicas INSST"],
            },
            "irpf_retenciones_nomina": {
                "summary": "Cálculo tipo retención IRPF nómina: rendimientos trabajo - reducciones - gastos deducibles = base liquidable. Aplicar escala autonómica + estatal. Modelo 145 (datos personales/familiares) obligatorio. Mínimo retener: tipo resultante o 2% si <14.000€.",
                "next_steps": ["Recoger modelo 145 firmado", "Calcular rendimientos netos trabajo", "Aplicar reducciones (mínimo personal/familiar)", "Determinar base liquidable", "Calcular cuota (estatal + autonómica)", "Tipo retención = cuota / base retención"],
                "citations": ["LIRPF Art. 80-84", "RGLIRPF Art. 80-85", "Modelo 145"],
            },
            "certificados_empresa": {
                "summary": "Emito certificados: empresa (periodos cotizados, bases, contingencias), retenciones IRPF (modelo 190/111), bases SS (INEM). Entrega a trabajador para prestaciones (paro, jubilación, IT).",
                "next_steps": ["Identificar tipo certificado solicitado", "Extraer datos nóminas/TC1/TC2", "Rellenar modelo oficial", "Firmar y sellar", "Entregar trabajador / enviar SEPE/INSS"],
                "citations": ["LGSS Art. 27", "RGLIRPF Art. 101", "RD 1/1994"],
            },
            "consulta_personal": {
                "summary": "Especialista laboral a tu disposición. Nóminas (mensual/extra/finiquito), contratos (indefinido/temporal/formativo), SS (TC1/TC2, altas/bajas), absentismo (IT, maternidad), PRL, IRPF nómina, certificados.",
                "next_steps": ["Indica tu necesidad específica"],
            },
        }
        
        resp = responses.get(action, responses["consulta_personal"])
        return self.build_response(
            action=action,
            summary=resp["summary"],
            next_steps=resp.get("next_steps", []),
            documents_needed=req,
            deadlines=resp.get("deadlines", []),
            citations=resp.get("citations", []),
            confidence=analysis.get("confidence", 0.9),
        )

__all__ = ["PersonalAgent"]