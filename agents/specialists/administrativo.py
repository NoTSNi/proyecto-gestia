"""GESTIA Agents - Administrativo Specialist (Enhanced)."""

from __future__ import annotations

from agents.enhanced_specialist_base import EnhancedSpecialistBase, ActionPlan, AgentContext, AgentResponse


class AdministrativoAgent(EnhancedSpecialistBase):
    """Agente especialista en derecho administrativo - Enhanced."""

    name = "administrativo"
    description = "Especialista en licencias, subvenciones, recursos, contratos públicos, sanciones, escritos"
    capabilities = [
        "licencia_apertura",
        "licencia_actividad",
        "licencia_obra",
        "declaracion_responsable",
        "subvencion_solicitud",
        "subvencion_justificacion",
        "recurso_reposicion",
        "recurso_alzada",
        "reclamacion_economico_administrativa",
        "contrato_publico_licitacion",
        "contrato_publico_ejecucion",
        "sancion_recurso",
        "escrito_generico",
        "expediente_administrativo",
        "silencio_administrativo",
    ]

    KEYWORDS = {
        "licencias": ["licencia", "apertura", "actividad", "obra", "declaración responsable"],
        "subvenciones": ["subvención", "subvencion", "ayuda", "convocatoria", "justificación"],
        "recursos": ["recurso", "reposición", "alzada", "económico-administrativa", "tear"],
        "contratos": ["contrato público", "licitación", "pliegos", "adjudicación", "ejecución"],
        "sanciones": ["sanción", "sancion", "multa", "expediente sancionador"],
        "escritos": ["escrito", "solicitud", "instancia", "registro", "administración"],
        "silencio": ["silencio administrativo", "desestimatorio", "estimatorio"],
    }

    def can_handle(self, query: str) -> float:
        query_lower = query.lower()
        matches = 0
        for cat, kws in self.KEYWORDS.items():
            matches += sum(1 for kw in kws if kw in query_lower)
        return min(0.95, 0.3 + matches * 0.12)

    async def analyze(self, query: str, context: AgentContext) -> dict:
        query_lower = query.lower()
        action_type = "escrito_generico"
        params = {}
        req = []
        prod = []
        
        if any(kw in query_lower for kw in self.KEYWORDS["licencias"]):
            if "apertura" in query_lower or "actividad" in query_lower:
                action_type = "licencia_apertura"
                req = ["Proyecto técnico visado", "Planos", "Memoria", "Seguro RC", "Tasas"]
                prod = ["Licencia apertura/actividad", "Comunicación previa si aplica"]
            elif "obra" in query_lower:
                action_type = "licencia_obra"
                req = ["Proyecto visado", "Tasas ICIO", "Garantías", "Seguro decenal"]
                prod = ["Licencia obra mayor/menor", "Acta replanteo"]
                params["tipo"] = "mayor" if "mayor" in query_lower else "menor"
            else:
                action_type = "declaracion_responsable"
                req = ["Declaración responsable firmada", "Documentación simplificada"]
                prod = ["Comunicación previa", "Inicio inmediato actividad"]
        
        elif any(kw in query_lower for kw in self.KEYWORDS["subvenciones"]):
            if "justific" in query_lower:
                action_type = "subvencion_justificacion"
                req = ["Memoria económica", "Facturas", "Certificados", "Cuentas justificativas"]
                prod = ["Informe justificación", "Certificado técnico"]
            else:
                action_type = "subvencion_solicitud"
                req = ["Memoria proyecto", "Presupuesto", "Doc. administrativa", "Plazos"]
                prod = ["Solicitud subvención", "Anexo documentación"]
        
        elif any(kw in query_lower for kw in self.KEYWORDS["recursos"]):
            if "reposición" in query_lower:
                action_type = "recurso_reposicion"
                req = ["Acto recurrido", "Fundamentos hecho/derecho", "Poderes si procede"]
                prod = ["Recurso reposición", "Recibo presentación"]
            elif "alzada" in query_lower:
                action_type = "recurso_alzada"
                req = ["Acto recurrido", "Resolución recurso anterior", "Órgano superior"]
                prod = ["Recurso alzada", "Recibo presentación"]
            else:
                action_type = "reclamacion_economico_administrativa"
                req = ["Acto tributario", "Fundamentos", "Suspensión opcional"]
                prod = ["Reclamación TEAR", "Recibo presentación"]
        
        elif any(kw in query_lower for kw in self.KEYWORDS["contratos"]):
            action_type = "contrato_publico"
            req = ["Pliegos", "Criterios adjudicación", "Solvencia", "Clasificación"]
            prod = ["Oferta licitación", "Documentación contrato"]
        
        elif any(kw in query_lower for kw in self.KEYWORDS["sanciones"]):
            action_type = "sancion_recurso"
            req = ["Pliego cargos", "Alegaciones", "Prueba", "Recurso"]
            prod = ["Escrito alegaciones", "Recurso reposición/alzada"]
        
        elif any(kw in query_lower for kw in self.KEYWORDS["silencio"]):
            action_type = "silencio_administrativo"
            req = ["Solicitud original", "Justificante presentación", "Plazos"]
            prod = ["Informe silencio", "Estrategia actuación"]
        
        return ActionPlan(action_type, query, 0.85, params, req, prod).to_dict()

    async def execute(self, analysis: dict, query: str, context: AgentContext) -> AgentResponse:
        action = analysis.get("action_type", "escrito_generico")
        params = analysis.get("parameters", {})
        req = analysis.get("requires_documents", [])
        client_ctx = await self.get_client_context(context.tenant_id)
        empresa = client_ctx.get("cliente_ejemplo", {}).get("empresa", {})
        
        responses = {
            "licencia_apertura": {
                "summary": f"Tramito licencia apertura/actividad para {empresa.get('nombre', 'la empresa')}. Requiere: proyecto técnico visado, planos, memoria descriptiva, seguro RC, tasas municipales. Plazo resolución: 3-6 meses según ayuntamiento.",
                "next_steps": ["Encargar proyecto técnico a ingeniero/arquitecto", "Contratar seguro RC", "Presentar solicitud + doc. en ayuntamiento", "Pagar tasas", "Esperar resolución / silencio positivo"],
                "deadlines": [{"description": "Plazo máximo resolución", "date": "3-6 meses (según ordenanza)"}],
                "citations": ["LBRL Art. 25", "Ley 12/2012 urgente", "Ordenanzas municipales"],
            },
            "licencia_obra": {
                "summary": f"Licencia obra {'mayor' if params.get('tipo') == 'mayor' else 'menor'}: proyecto visado por colegio profesional, tasas ICIO (4% presupuesto), garantías, seguro decenal (obra mayor).",
                "next_steps": ["Visar proyecto en colegio profesional", "Calcular y pagar ICIO", "Aportar garantías (5-10%)", "Seguro decenal si obra mayor", "Presentar en ayuntamiento"],
                "deadlines": [{"description": "Plazo resolución", "date": "2-4 meses"}],
                "citations": ["LOE Art. 15", "TRLRHL Art. 160", "Ordenanzas ICIO"],
            },
            "declaracion_responsable": {
                "summary": "Declaración responsable: actividades inocuas/menos impacto. Inicio inmediato tras presentación. Documentación simplificada. Ayuntamiento verifica a posteriori.",
                "next_steps": ["Verificar actividad en catálogo declaración responsable", "Rellenar formulario oficial", "Presentar en registro ayuntamiento", "Iniciar actividad"],
                "deadlines": [{"description": "Efectos inmediatos", "date": "Desde presentación"}],
                "citations": ["Ley 12/2012 Art. 5", "LBRL Art. 25.3"],
            },
            "subvencion_solicitud": {
                "summary": "Preparo solicitud subvención: memoria técnica/económica, presupuesto desglosado, documentación administrativa (CIF, censal, cuentas), cumplimiento requisitos convocatoria. Plazos estrictos.",
                "next_steps": ["Leer bases convocatoria", "Preparar memoria proyecto", "Elaborar presupuesto", "Reunir doc. administrativa", "Presentar antes plazo"],
                "deadlines": [{"description": "Plazo presentación", "date": "Según convocatoria (estricto)"}],
                "citations": ["LGS Art. 22-25", "Bases convocatoria"],
            },
            "subvencion_justificacion": {
                "summary": "Justifico subvención concedida: memoria económica ejecutada, facturas originales, certificados técnicos, cuentas justificativas, certificación gastos. Plazo: según bases (habitual 3-6 meses post-ejecución).",
                "next_steps": ["Recopilar facturas y justificantes", "Elaborar memoria económica", "Certificar ejecución técnica", "Presentar cuenta justificativa", "Conservar originales 5 años"],
                "deadlines": [{"description": "Plazo justificación", "date": "3-6 meses post-ejecución"}],
                "citations": ["LGS Art. 30-33", "Bases convocatoria"],
            },
            "recurso_reposicion": {
                "summary": "Recurso de reposición (potestativo, previo a contencioso): 1 mes desde notificación. Órgano que dictó acto. Fundamentos hecho + derecho. Suspensión no automática.",
                "next_steps": ["Analizar acto recurrido", "Redactar escrito (hechos, fundamentos, suplico)", "Presentar en registro órgano", "Esperar resolución (3 meses = desestimado)"],
                "deadlines": [{"description": "Plazo interposición", "date": "1 mes desde notificación"}, {"description": "Plazo resolución", "date": "3 meses (silencio desestimatorio)"}],
                "citations": ["LPACAP Art. 123-124", "LJCA Art. 8"],
            },
            "recurso_alzada": {
                "summary": "Recurso de alzada: 1 mes desde notificación resolución reposición (o acto directo si no cabe reposición). Órgano superior jerárquico. Misma estructura.",
                "next_steps": ["Verificar que cabe alzada", "Redactar recurso", "Presentar en órgano superior", "Esperar resolución"],
                "deadlines": [{"description": "Plazo interposición", "date": "1 mes"}, {"description": "Plazo resolución", "date": "3 meses"}],
                "citations": ["LPACAP Art. 121-122"],
            },
            "reclamacion_economico_administrativa": {
                "summary": "Reclamación económico-administrativa (TEAR): actos tributarios. 1 mes. Suspensión automática si garantía. Órgano: TEAR autonómico/estatal.",
                "next_steps": ["Identificar acto tributario", "Redactar reclamación", "Presentar en TEAR", "Solicitar suspensión si procede"],
                "deadlines": [{"description": "Plazo", "date": "1 mes desde notificación"}],
                "citations": ["LGT Art. 241-245", "RD 520/2005"],
            },
            "contrato_publico": {
                "summary": "Asesoría contratación pública (LCSP): pliegos, criterios adjudicación, solvencia técnica/económica, clasificación empresarios, recursos especiales.",
                "next_steps": ["Analizar pliegos", "Preparar documentación solvencia", "Presentar oferta", "Esperar adjudicación", "Formalizar contrato"],
                "citations": ["LCSP 9/2017", "Pliegos tipo"],
            },
            "sancion_recurso": {
                "summary": "Defensa expediente sancionador: fase alegaciones (15 días), prueba, propuesta resolución, recurso reposición/alzada. Principios: tipicidad, proporcionalidad, prescripción (1-3 años).",
                "next_steps": ["Analizar pliego cargos", "Presentar alegaciones + prueba", "Esperar resolución", "Recurrir si procede"],
                "deadlines": [{"description": "Alegaciones", "date": "15 días"}, {"description": "Prescripción leve", "date": "1 año"}, {"description": "Prescripción grave", "date": "3 años"}],
                "citations": ["LPACAP Art. 132-136", "LGS Art. 60-63"],
            },
            "silencio_administrativo": {
                "summary": "Análisis silencio: estimatorio (3 meses general, arts. 24.1 LPACAP) vs desestimatorio (tributario, sancionador, arts. 24.3). Estrategia: certificado silencio + actuación.",
                "next_steps": ["Identificar tipo procedimiento", "Verificar plazo transcurrido", "Solicitar certificado silencio", "Actuar según tipo silencio"],
                "citations": ["LPACAP Art. 24", "LGT Art. 105"],
            },
            "escrito_generico": {
                "summary": "Especialista administrativo: licencias (apertura/actividad/obra), subvenciones (solicitud/justificación), recursos (reposición/alzada/TEAR), contratos públicos, sanciones, escritos genéricos, expedientes, silencio administrativo.",
                "next_steps": ["Indica tu necesidad específica"],
            },
        }
        
        resp = responses.get(action, responses["escrito_generico"])
        return self.build_response(
            action=action,
            summary=resp["summary"],
            next_steps=resp.get("next_steps", []),
            documents_needed=req,
            deadlines=resp.get("deadlines", []),
            citations=resp.get("citations", []),
            confidence=analysis.get("confidence", 0.85),
        )

__all__ = ["AdministrativoAgent"]