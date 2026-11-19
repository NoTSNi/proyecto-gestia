"""GESTIA Agents - Specialist Base Class."""

from __future__ import annotations

from agents.base_agent import BaseAgent, AgentContext, AgentResponse


class SpecialistBase(BaseAgent):
    """Base class for domain specialist agents."""

    domain: str = "general"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.domain = self.__class__.__name__.replace("Agent", "").lower()

    async def process(self, query: str, context: AgentContext) -> AgentResponse:
        """Process query - override in subclasses."""
        return AgentResponse(
            agent=self.name,
            success=True,
            response=f"[{self.name}] Processing: {query}",
            data={"domain": self.domain},
        )

    def can_handle(self, query: str) -> float:
        """Return confidence score (0-1) for handling this query."""
        return 0.5