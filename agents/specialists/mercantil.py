"""GESTIA Agents - Mercantil Specialist."""

from __future__ import annotations

from agents.specialist_base import SpecialistBase, AgentContext, AgentResponse


class MercantilAgent(SpecialistBase):
    """Agente especialista en derecho mercantil."""

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
    ]

    def can_handle(self, query: str) -> float:
        keywords = [
            "constituir", "constitución", "sl", "s.l.", "sociedad limitada",
            "estatutos", "junta", "juntas", "libro", "libros", "acta",
            "disolver", "disolución", "liquidación", "depósito", "cuentas anuales",
            "capital", "socio", "socios", "administrador", "consejo",
            "transformar", "fusionar", "fusion", "escindir", "escision",
            "denominación", "objeto social", "domicilio social",
        ]
        query_lower = query.lower()
        matches = sum(1 for kw in keywords if kw in query_lower)
        return min(0.9, 0.3 + matches * 0.1)

    async def process(self, query: str, context: AgentContext) -> AgentResponse:
        # TODO: Implement actual logic with LLM + tools
        # For now, return structured response indicating what would be done
        
        query_lower = query.lower()
        
        if any(kw in query_lower for kw in ["constituir", "constitución", "crear sl", "nueva sociedad"]):
            action = "constitucion_sociedad"
            response = "Te ayudo a constituir la sociedad. Necesitaré: denominación (3 opciones), objeto social, capital mínimo 3000€, socios y % participación, administrador(es), domicilio social."
        
        elif any(kw in query_lower for kw in ["estatutos", "modificar estatutos", "cambio estatutos"]):
            action = "modificacion_estatutos"
            response = "Para modificar estatutos: necesitamos acuerdo de junta, escritura pública, inscripción en Registro Mercantil. ¿Qué artículos se modifican?"
        
        elif any(kw in query_lower for kw in ["junta", "acta", "convocar"]):
            action = "juntas_generales"
            response = "Preparo la convocatoria y acta de junta. Necesito: tipo (ordinaria/extraordinaria), orden del día, fecha, quórum."
        
        elif any(kw in query_lower for kw in ["libro", "legalizar", "diario", "mayor", "inventario"]):
            action = "libros_oficiales"
            response = "Gestiono la legalización de libros oficiales (Diario, Mayor, Inventario, Actas). Te preparo el asiento de apertura/cierre y presentación telemática."
        
        elif any(kw in query_lower for kw in ["disolver", "disolución", "liquidar", "liquidación"]):
            action = "disolucion_liquidacion"
            response = "Proceso de disolución: acuerdo de junta, nombramiento liquidadores, período de liquidación, cancelación registral. ¿Causa de disolución?"
        
        elif any(kw in query_lower for kw in ["depósito", "cuentas anuales", "depositar cuentas"]):
            action = "deposito_cuentas"
            response = "Preparo el depósito de cuentas anuales en Registro Mercantil. Necesito: balance, PyG, memoria, informe de gestión (si aplica), propuesta de aplicación de resultado."
        
        else:
            action = "consulta_mercantil"
            response = "Especialista mercantil a tu disposición. ¿En qué te ayudo? Constitución, estatutos, juntas, libros, disolución, depósito de cuentas..."

        return AgentResponse(
            agent=self.name,
            success=True,
            response=response,
            data={"action": action, "domain": "mercantil"},
            actions=[{"type": "info", "action": action}],
        )