"""GESTIA Agents - Administrativo Specialist."""

from __future__ import annotations

from agents.specialist_base import SpecialistBase, AgentContext, AgentResponse


class AdministrativoAgent(SpecialistBase):
    """Agente especialista en derecho administrativo."""

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

    def can_handle(self, query: str) -> float:
        keywords = [
            "licencia", "apertura", "actividad", "obra", "declaración responsable",
            "subvención", "subvencion", "ayuda", "convocatoria", "justificación",
            "recurso", "reposición", "alzada", "económico-administrativa", "tear",
            "contrato público", "licitación", "pliegos", "adjudicación", "ejecución",
            "sanción", "sancion", "multa", "expediente sancionador",
            "escrito", "solicitud", "instancia", "registro", "administración",
            "silencio administrativo", "desestimatorio", "estimatorio",
            "ayuntamiento", "comunidad autónoma", "ministerio", "órgano",
            "expediente", "número expediente", "referencia",
        ]
        query_lower = query.lower()
        matches = sum(1 for kw in keywords if kw in query_lower)
        return min(0.9, 0.3 + matches * 0.1)

    async def process(self, query: str, context: AgentContext) -> AgentResponse:
        query_lower = query.lower()

        if any(kw in query_lower for kw in ["licencia", "apertura", "actividad", "obra", "declaración responsable"]):
            if "apertura" in query_lower or "actividad" in query_lower:
                action = "licencia_apertura"
                response = "Tramito licencia de apertura/actividad: proyecto técnico, plano, memoria, seguro RC, tasas. ¿Ayuntamiento?"
            elif "obra" in query_lower:
                action = "licencia_obra"
                response = "Licencia de obra mayor/menor: proyecto visado, tasas ICIO, garantías. ¿Tipo obra?"
            else:
                action = "declaracion_responsable"
                response = "Declaración responsable: actividades inocuas, inicio inmediato, documentación simplificada. Verifico requisitos."
        
        elif any(kw in query_lower for kw in ["subvención", "subvencion", "ayuda", "convocatoria"]):
            if "justific" in query_lower:
                action = "subvencion_justificacion"
                response = "Justifico subvención: memoria económica, facturas, certificados, cuentas justificativas, plazo."
            else:
                action = "subvencion_solicitud"
                response = "Preparo solicitud subvención: memoria proyecto, presupuesto, documentación administrativa, plazos. ¿Convocatoria?"
        
        elif any(kw in query_lower for kw in ["recurso", "reposición", "alzada", "económico", "tear"]):
            if "reposición" in query_lower:
                action = "recurso_reposicion"
                response = "Redacto recurso de reposición (1 mes): órgano que dictó acto, fundamentos hecho/derecho, suplico."
            elif "alzada" in query_lower:
                action = "recurso_alzada"
                response = "Recurso de alzada (1 mes): órgano superior, misma estructura. ¿Acto recurrido?"
            else:
                action = "reclamacion_economico_administrativa"
                response = "Reclamación económico-administrativa (TEAR): acto tributario, 1 mes, suspensión opcional."
        
        elif any(kw in query_lower for kw in ["contrato público", "licitación", "pliegos", "adjudicación"]):
            action = "contrato_publico"
            response = "Asesoría contratación pública: pliegos, criterios adjudicación, solvencia, clasificación, recursos especiales."
        
        elif any(kw in query_lower for kw in ["sanción", "sancion", "multa", "expediente sancionador"]):
            action = "sancion_recurso"
            response = "Defensa en expediente sancionador: alegaciones, prueba, recurso, prescripción, proporcionalidad."
        
        elif any(kw in query_lower for kw in ["silencio administrativo"]):
            action = "silencio_administrativo"
            response = "Análisis silencio: estimatorio (3 meses general) vs desestimatorio (tributario, sancionador). Estrategia."
        
        else:
            action = "escrito_generico"
            response = "Especialista administrativo: licencias, subvenciones, recursos (reposición/alzada/TEAR), contratos públicos, sanciones, escritos."

        return AgentResponse(
            agent=self.name,
            success=True,
            response=response,
            data={"action": action, "domain": "administrativo"},
            actions=[{"type": "info", "action": action}],
        )