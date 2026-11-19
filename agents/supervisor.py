"""GESTIA Agents - Supervisor (Router + Orchestrator)."""

from __future__ import annotations

from agents.base_agent import BaseAgent, AgentContext, AgentResponse
from agents.specialists import (
    MercantilAgent,
    AdministrativoAgent,
    ContableAgent,
    PersonalAgent,
)


class SupervisorAgent(BaseAgent):
    """Supervisor agent that routes queries to appropriate specialists."""

    name = "supervisor"
    description = "Orquestador multi-agente: clasifica intenciones, delega a especialistas, consolida respuestas"
    capabilities = [
        "intent_classification",
        "agent_routing",
        "response_consolidation",
        "multi_agent_coordination",
        "workflow_management",
    ]

    def __init__(self, specialists: dict[str, BaseAgent] | None = None, **kwargs):
        super().__init__(**kwargs)
        self.specialists = specialists or {
            "mercantil": MercantilAgent(),
            "administrativo": AdministrativoAgent(),
            "contable": ContableAgent(),
            "personal": PersonalAgent(),
        }

    def register_specialist(self, name: str, agent: BaseAgent) -> None:
        """Register a new specialist agent."""
        self.specialists[name] = agent

    async def classify_intent(self, query: str) -> dict[str, float]:
        """Classify query intent by scoring against all specialists."""
        scores = {}
        for name, agent in self.specialists.items():
            scores[name] = await agent.can_handle(query)
        return scores

    async def route_query(self, query: str, context: AgentContext) -> AgentResponse:
        """Route query to best specialist."""
        scores = await self.classify_intent(query)
        
        # Get best match
        best_agent_name = max(scores, key=scores.get)
        best_score = scores[best_agent_name]

        if best_score < 0.3:
            return AgentResponse(
                agent=self.name,
                success=False,
                response="No estoy seguro de qué especialista necesita. ¿Podrías reformular tu consulta?",
                data={"scores": scores},
                error="low_confidence",
            )

        specialist = self.specialists[best_agent_name]
        return await specialist.process(query, context)

    async def process(self, query: str, context: AgentContext) -> AgentResponse:
        """Main entry point: classify, route, and return response."""
        # Log routing decision
        scores = await self.classify_intent(query)
        best_agent = max(scores, key=scores.get)

        # Route to specialist
        result = await self.route_query(query, context)
        
        # Add routing metadata
        result.data["routing"] = {
            "scores": scores,
            "selected_agent": best_agent,
            "confidence": scores[best_agent],
        }
        result.data["supervisor"] = self.name

        return result

    async def process_multi_agent(self, query: str, context: AgentContext) -> list[AgentResponse]:
        """Process query with multiple relevant agents (for complex queries)."""
        scores = await self.classify_intent(query)
        
        # Select agents above threshold
        threshold = 0.4
        selected = [(name, agent) for name, agent in self.specialists.items() if scores[name] >= threshold]
        
        if not selected:
            selected = [(max(scores, key=scores.get), self.specialists[max(scores, key=scores.get)])]

        results = []
        for name, agent in selected:
            result = await agent.process(query, context)
            results.append(result)

        return results