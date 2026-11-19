"""GESTIA Agents - Base Agent Class."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4


@dataclass
class AgentContext:
    """Context passed to agent for processing."""
    tenant_id: str
    user_id: str
    correlation_id: str = field(default_factory=lambda: str(uuid4()))
    metadata: dict = field(default_factory=dict)


@dataclass
class AgentResponse:
    """Standard agent response."""
    agent: str
    success: bool
    response: str
    data: dict = field(default_factory=dict)
    actions: list[dict] = field(default_factory=list)
    error: str | None = None
    tokens_used: int = 0


class BaseAgent(ABC):
    """Base class for all GESTIA agents."""

    name: str = "base"
    description: str = "Base agent"
    capabilities: list[str] = field(default_factory=list)

    def __init__(self, **kwargs):
        self.config = kwargs

    @abstractmethod
    async def process(self, query: str, context: AgentContext) -> AgentResponse:
        """Process a query and return response."""
        pass

    async def validate_context(self, context: AgentContext) -> bool:
        """Validate context before processing."""
        return bool(context.tenant_id and context.user_id)

    def get_capabilities(self) -> list[str]:
        """Return list of agent capabilities."""
        return self.capabilities

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name={self.name})>"