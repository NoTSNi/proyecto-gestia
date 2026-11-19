"""GESTIA Agents - Personal Specialist."""

from __future__ import annotations

from agents.specialist_base import SpecialistBase, AgentContext, AgentResponse


class PersonalAgent(SpecialistBase):
    """Agente especialista en laboral y nóminas."""

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

    def can_handle(self, query: str) -> float:
        keywords = [
            "nómina", "nomina", "sueldo", "salario", "paga", "extra", "finiquito",
            "contrato", "indefinido", "temporal", "formación", "prácticas", "fijo discontinuo",
            "seguridad social", "ss ", "tc1", "tc2", "alta", "baja", "variación", "ccc",
            "naf", "afiliación", "cotización", "base cotización", "grupo cotización",
            "absentismo", "baja médica", "it ", "incapacidad", "maternidad", "paternidad",
            "prl", "prevención", "riesgos", "evaluación", "plan prevención",
            "irpf nómina", "retención nómina", "tipo retención",
            "certificado empresa", "certificado retenciones",
            "empleado", "trabajador", "personal",
            "convenio", "categoría", "grupo profesional",
        ]
        query_lower = query.lower()
        matches = sum(1 for kw in keywords if kw in query_lower)
        return min(0.95, 0.4 + matches * 0.1)

    async def process(self, query: str, context: AgentContext) -> AgentResponse:
        query_lower = query.lower()

        if any(kw in query_lower for kw in ["nómina", "nomina", "calcular nómina", "preparar nómina"]):
            if "extra" in query_lower or "extraordinaria" in query_lower:
                action = "nomina_extraordinaria"
                response = "Preparo nómina extraordinaria (verano/navidad). Base: convenio o acuerdo. ¿Incluye prorrateo?"
            else:
                action = "nomina_mensual"
                response = "Calculo nómina mensual. Necesito: empleado, salario base, complementos, horas extra, IRPF, base SS. Genero recibo, TC1/TC2."
        
        elif any(kw in query_lower for kw in ["finiquito", "finalizar contrato", "extinción"]):
            action = "finiquito"
            response = "Calculo finiquito: días pendientes, parte proporcional pagas extra, vacaciones no disfrutadas, indemnización si procede."
        
        elif any(kw in query_lower for kw in ["indemniz", "despido", "extinción contrato"]):
            action = "indemnizacion"
            response = "Calculo indemnización: tipo despido (objetivo/disciplinario/nulo), antigüedad, salario diario, tope legal."
        
        elif any(kw in query_lower for kw in ["contrato", "contratar", "nuevo empleado"]):
            if "indefinido" in query_lower:
                action = "contrato_indefinido"
                response = "Redacto contrato indefinido: ordinario, apoyo emprendedores, discapacidad, >52 años. Necesito: categoría, salario, jornada, convenio."
            elif "temporal" in query_lower or "duración determinada" in query_lower:
                action = "contrato_temporal"
                response = "Redacto contrato temporal: obra/servicio, eventual, interinidad, formación. Causa justificada obligatoria."
            elif "formación" in query_lower or "prácticas" in query_lower:
                action = "contrato_formacion"
                response = "Redacto contrato formativo/prácticas: requisitos edad, titulación, tutor, plan formativo, duración."
            else:
                action = "contrato_generico"
                response = "Asesoría sobre tipo de contrato según necesidad. Indefinido (ordinario, emprendedores), temporal (obra, eventual, interinidad), formativo."
        
        elif any(kw in query_lower for kw in ["tc1", "tc2", "liquidación", "cotización"]):
            action = "tc1_tc2"
            response = "Genero TC1 (liquidación cuotas) y TC2 (relación nominal). Envío sistema RED, obtengo recibo."
        
        elif any(kw in query_lower for kw in ["alta", "baja", "variación", "ccc", "naf"]):
            action = "altas_bajas_ss"
            response = "Tramito alta/baja/variación en Seguridad Social: TA.1, TA.2, modelos oficiales. Comunicación inmediata."
        
        elif any(kw in query_lower for kw in ["absentismo", "baja médica", "it ", "incapacidad temporal"]):
            action = "absentismo"
            response = "Gestión IT: parte de baja/confirmación/alta, comunicación empresa/INSS, prestación, cotización durante IT."
        
        elif any(kw in query_lower for kw in ["maternidad", "paternidad", "permiso"]):
            action = "maternidad_paternidad"
            response = "Permiso nacimiento/cuidado: 16 semanas (6 obligatorias), prestación 100% base reguladora, cotización empresa."
        
        elif any(kw in query_lower for kw in ["prl", "prevención", "riesgos", "evaluación"]):
            action = "prl"
            response = "Evaluación riesgos: identificación, valoración, plan prevención, vigilancia salud, formación, equipos protección."
        
        else:
            action = "consulta_personal"
            response = "Especialista laboral a tu disposición. Nóminas, contratos, SS, absentismo, PRL, IRPF nóminas, certificados."

        return AgentResponse(
            agent=self.name,
            success=True,
            response=response,
            data={"action": action, "domain": "personal"},
            actions=[{"type": "info", "action": action}],
        )