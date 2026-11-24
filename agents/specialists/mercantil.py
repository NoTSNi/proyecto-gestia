"""GESTIA Agents - Mercantil Specialist (Enhanced)."""

from __future__ import annotations

from typing import Any

from agents.enhanced_specialist_base import EnhancedSpecialistBase, ActionPlan, AgentContext, AgentResponse


class MercantilAgent(EnhancedSpecialistBase):
    """Agente especialista en derecho mercantil - Enhanced with infrastructure."""

    name = "mercantil"
    description = "Especialista en constitución, modificación, disolución de sociedades, libros oficiales, juntas, estatutos"
    capabilities = [
        "constitucion_sociedad",
        "modificacion_estatutos",
        "disolucion_liquidacion",
        "libros_oficiales",
        "juntas_generales",
        "deposito_cuentas",
        "cambio_denominacion",
        "ampliacion_reduccion_capital",
        "transformacion_sociedad",
        "fusion_escision",
        "poderes_apoderamiento",
        "certificaciones_registrales",
    ]

    # Keywords for intent classification
    KEYWORDS = {
        "constitucion": ["constituir", "constitución", "crear sl", "nueva sociedad", "constituir sociedad", "escritura constitución"],
        "estatutos": ["estatutos", "modificar estatutos", "cambio estatutos", "modificación estatutos"],
        "juntas": ["junta", "juntas", "acta", "convocar", "convocatoria", "ordinaria", "extraordinaria"],
        "libros": ["libro", "legalizar", "diario", "mayor", "inventario", "actas", "libros oficiales"],
        "disolucion": ["disolver", "disolución", "liquidar", "liquidación", "extinguir"],
        "deposito": ["depósito", "depositar", "cuentas anuales", "depósito cuentas"],
        "denominacion": ["denominación", "cambio nombre", "nueva denominación"],
        "capital": ["ampliación capital", "reducción capital", "aumentar capital", "reducir capital"],
        "transformacion": ["transformar", "transformación", "cambio tipo sociedad"],
        "fusion": ["fusionar", "fusión", "escindir", "escision", "segregación"],
        "poderes": ["poder", "apoderamiento", "apoderar", "representación"],
    }

    def can_handle(self, query: str) -> float:
        query_lower = query.lower()
        matches = 0
        for category, keywords in self.KEYWORDS.items():
            matches += sum(1 for kw in keywords if kw in query_lower)
        return min(0.95, 0.3 + matches * 0.12)

    async def analyze(self, query: str, context: AgentContext) -> dict:
        """Analyze query and determine action plan."""
        query_lower = query.lower()
        
        # Determine action type
        action_type = "consulta_mercantil"
        parameters = {}
        requires_docs = []
        produces_docs = []
        
        if any(kw in query_lower for kw in self.KEYWORDS["constitucion"]):
            action_type = "constitucion_sociedad"
            requires_docs = [
                "Certificación negativa denominación (3 opciones)",
                "DNI/NIE socios y administradores",
                "Justificante aportación capital (mín. 3.000€)",
                "Estatutos sociales firmados",
            ]
            produces_docs = ["Escritura constitución", "Estatutos inscritos", "NIF provisional", "Libro socios"]
            parameters = {"capital_minimo": 3000, "socios_min": 1}
        
        elif any(kw in query_lower for kw in self.KEYWORDS["estatutos"]):
            action_type = "modificacion_estatutos"
            requires_docs = ["Escritura modificación estatutos", "Certificación acuerdo junta", "Estatutos modificados"]
            produces_docs = ["Escritura pública modificación", "Estatutos actualizados inscritos"]
        
        elif any(kw in query_lower for kw in self.KEYWORDS["juntas"]):
            action_type = "juntas_generales"
            requires_docs = ["Convocatoria", "Orden del día", "Poderes/representación", "Acta anterior"]
            produces_docs = ["Acta de junta", "Certificaciones acuerdos", "Listado asistentes"]
            if "ordinaria" in query_lower:
                parameters["tipo"] = "ordinaria"
            elif "extraordinaria" in query_lower:
                parameters["tipo"] = "extraordinaria"
        
        elif any(kw in query_lower for kw in self.KEYWORDS["libros"]):
            action_type = "libros_oficiales"
            requires_docs = ["Libro Diario", "Libro Mayor", "Libro Inventario", "Libro Actas"]
            produces_docs = ["Libros legalizados", "Asiento apertura/cierre", "Presentación telemática"]
        
        elif any(kw in query_lower for kw in self.KEYWORDS["disolucion"]):
            action_type = "disolucion_liquidacion"
            requires_docs = ["Acuerdo junta disolución", "Nombramiento liquidadores", "Balance final liquidación"]
            produces_docs = ["Escritura disolución", "Cancelación registral", "Certificado extinción"]
            parameters["fase"] = "disolucion" if "disol" in query_lower else "liquidacion"
        
        elif any(kw in query_lower for kw in self.KEYWORDS["deposito"]):
            action_type = "deposito_cuentas"
            requires_docs = ["Balance situación", "Cuenta pérdidas/ganancias", "Memoria", "Informe gestión", "Propuesta aplicación resultado"]
            produces_docs = ["Depósito telemático RM", "Recibo presentación", "Cuentas publicadas"]
        
        elif any(kw in query_lower for kw in self.KEYWORDS["capital"]):
            action_type = "ampliacion_reduccion_capital"
            requires_docs = ["Acuerdo junta", "Informe administradores", "Informe expertos (si >50%)", "Escritura"]
            produces_docs = ["Escritura ampliación/reducción", "Estatutos actualizados", "Inscripción RM"]
            if "ampli" in query_lower:
                parameters["operacion"] = "ampliacion"
            else:
                parameters["operacion"] = "reduccion"
        
        elif any(kw in query_lower for kw in self.KEYWORDS["poderes"]):
            action_type = "poderes_apoderamiento"
            requires_docs = ["Escritura poder", "DNI apoderado", "Acuerdo órgano administración"]
            produces_docs = ["Escritura poder notarial", "Inscripción RM (si general)"]
        
        return ActionPlan(
            action_type=action_type,
            query=query,
            confidence=0.85,
            parameters=parameters,
            requires_documents=requires_docs,
            produces_documents=produces_docs,
        ).to_dict()

    async def execute(self, analysis: dict, query: str, context: AgentContext) -> AgentResponse:
        """Execute the mercantil action plan."""
        action_type = analysis.get("action_type", "consulta_mercantil")
        params = analysis.get("parameters", {})
        req_docs = analysis.get("requires_documents", [])
        prod_docs = analysis.get("produces_documents", [])
        
        # Get client context for personalized response
        client_ctx = await self.get_client_context(context.tenant_id)
        empresa = client_ctx.get("cliente_ejemplo", {}).get("empresa", {})
        
        responses = {
            "constitucion_sociedad": {
                "summary": f"Te ayudo a constituir {empresa.get('nombre', 'la sociedad')}. Proceso: 1) Certificación denominación (3 opciones en RM), 2) Apertura cuenta bancaria + aportación capital (mín. 3.000€), 3) Escritura pública notaría, 4) Impuesto AJD (exento), 5) Inscripción RM (≈15 días), 6) NIF definitivo, 7) Libro socios + actas.",
                "next_steps": [
                    "Solicitar certificación negativa denominación (3 opciones)",
                    "Abrir cuenta bancaria y aportar capital social",
                    "Firmar escritura constitución ante notario",
                    "Presentar modelo 600 (exento) e inscribir en RM",
                    "Obtener NIF definitivo y legalizar libros",
                ],
                "deadlines": [
                    {"description": "Inscripción Registro Mercantil", "date": "15 días hábiles desde escritura"},
                    {"description": "Declaración censal Hacienda (036/037)", "date": "Antes de iniciar actividad"},
                ],
                "citations": ["LSC Art. 4-23", "RRM Art. 15-40", "Ley 14/2013 emprendedores"],
            },
            "modificacion_estatutos": {
                "summary": "Modificación de estatutos: requiere acuerdo de junta general (mayoría reforzada si afecta derechos básicos), escritura pública, inscripción RM. Plazo: 30 días desde acuerdo.",
                "next_steps": [
                    "Convocar junta con orden del día específico",
                    "Aprobar modificación (mayoría 2/3 si derechos básicos)",
                    "Firmar escritura pública notaría",
                    "Inscribir en Registro Mercantil",
                ],
                "deadlines": [{"description": "Inscripción RM", "date": "30 días desde acuerdo junta"}],
                "citations": ["LSC Art. 285-292", "RRM Art. 171-180"],
            },
            "juntas_generales": {
                "summary": f"Preparo convocatoria y acta de junta {'ordinaria' if params.get('tipo') == 'ordinaria' else 'extraordinaria'}. Quórum: 25% capital (1ª) / cualquier % (2ª). Mayorías: ordinaria 1/3, reforzada 2/3.",
                "next_steps": [
                    "Redactar convocatoria (15 días antelación min.)",
                    "Incluir orden del día completo",
                    "Enviar a socios (certificado/burofax/email)",
                    "Celebrar junta y levantar acta",
                    "Certificar acuerdos para RM si procede",
                ],
                "deadlines": [
                    {"description": "Convocatoria min. 15 días antes", "date": "Según estatutos"},
                    {"description": "Inscripción acuerdos RM", "date": "30 días desde junta"},
                ],
                "citations": ["LSC Art. 159-200", "RRM Art. 102-112"],
            },
            "libros_oficiales": {
                "summary": "Legalización libros oficiales (Diario, Mayor, Inventario, Actas): presentación telemática en RM antes de 4 meses post-cierre. Asiento de apertura y cierre obligatorios.",
                "next_steps": [
                    "Cerrar contabilidad ejercicio",
                    "Generar asiento de cierre",
                    "Preparar libros en formato legal",
                    "Presentar telemáticamente en RM",
                    "Guardar justificante presentación",
                ],
                "deadlines": [{"description": "Legalización libros", "date": "4 meses post-cierre ejercicio"}],
                "citations": ["CCom Art. 25-33", "RRM Art. 270-280"],
            },
            "disolucion_liquidacion": {
                "summary": f"Proceso {'disolución' if params.get('fase') == 'disolucion' else 'liquidación'}: 1) Acuerdo junta (mayoría 2/3), 2) Nombramiento liquidadores, 3) Período liquidación (cobro deudas, pago acreedores), 4) Balance final, 5) Cuota liquidación socios, 6) Cancelación RM.",
                "next_steps": [
                    "Convocar junta disolución (causa legal: Art. 360 LSC)",
                    "Nombrar liquidadores (suelen ser administradores)",
                    "Publicar anuncio BORME + web",
                    "Realizar operaciones liquidación",
                    "Aprobar balance final y cuotas",
                    "Escritura cancelación e inscripción RM",
                ],
                "deadlines": [
                    {"description": "Publicación BORME", "date": "Inmediato tras acuerdo"},
                    {"description": "Cancelación RM", "date": "Tras aprobación balance final"},
                ],
                "citations": ["LSC Art. 360-394", "RRM Art. 200-215"],
            },
            "deposito_cuentas": {
                "summary": "Depósito cuentas anuales en RM: Balance, PyG, Memoria, Informe gestión (si aplica), Propuesta aplicación resultado. Formato XBRL obligatorio. Plazo: 1 mes post-aprobación junta (máx. 30 jul).",
                "next_steps": [
                    "Cerrar contabilidad y formular cuentas",
                    "Aprobar cuentas en junta ordinaria (≤30 jun)",
                    "Generar fichero XBRL",
                    "Presentar telemáticamente RM",
                    "Conservar recibo presentación",
                ],
                "deadlines": [
                    {"description": "Formulación cuentas", "date": "3 meses post-cierre (31 mar)"},
                    {"description": "Aprobación junta", "date": "6 meses post-cierre (30 jun)"},
                    {"description": "Depósito RM", "date": "1 mes post-aprobación"},
                ],
                "citations": ["LSC Art. 253-279", "RD 1/2010", "ORDEN EHA/3362/2010"],
            },
            "ampliacion_reduccion_capital": {
                "summary": f"{'Ampliación' if params.get('operacion') == 'ampliacion' else 'Reducción'} de capital: acuerdo junta, derecho suscripción preferente (ampliación), acreedores (reducción), escritura, inscripción RM.",
                "next_steps": [
                    "Informe administradores + expertos (si >50%)",
                    "Convocar junta general",
                    "Ejecutar {'ampliación' if params.get('operacion') == 'ampliacion' else 'reducción'}",
                    "Escritura pública e inscripción RM",
                    "Actualizar estatutos y libro socios",
                ],
                "deadlines": [
                    {"description": "Derecho suscripción preferente", "date": "Mín. 1 mes (ampliación)"},
                    {"description": "Oposición acreedores", "date": "1 mes publicación BORME (reducción)"},
                ],
                "citations": ["LSC Art. 295-310 (ampliación)", "LSC Art. 311-319 (reducción)"],
            },
            "poderes_apoderamiento": {
                "summary": "Otorgamiento de poderes: general (todos actos) vs especial (actos concretos). Inscripción RM solo si poder general. Revocación en cualquier momento.",
                "next_steps": [
                    "Definir alcance poder (general/especial)",
                    "Acuerdo órgano administración",
                    "Escritura notarial poder",
                    "Inscribir en RM (solo general)",
                    "Comunicar a terceros afectados",
                ],
                "citations": ["LSC Art. 234-237", "Código Civil Art. 1709-1739"],
            },
            "consulta_mercantil": {
                "summary": "Especialista mercantil a tu disposición. Áreas: constitución SL/SA, estatutos, juntas, libros oficiales, disolución/liquidación, depósito cuentas, ampliación/reducción capital, transformación, fusión/escisión, poderes.",
                "next_steps": ["Indica tu necesidad específica para guiarte paso a paso"],
            },
        }
        
        resp = responses.get(action_type, responses["consulta_mercantil"])
        
        return self.build_response(
            action=action_type,
            summary=resp["summary"],
            next_steps=resp.get("next_steps", []),
            documents_needed=req_docs,
            deadlines=resp.get("deadlines", []),
            citations=resp.get("citations", []),
            confidence=analysis.get("confidence", 0.85),
        )


# Export
__all__ = ["MercantilAgent"]