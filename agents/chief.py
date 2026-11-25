#!/usr/bin/env python3
"""
GESTIA Agents - Chief Agent (Enhanced Supervisor with Executive Authority).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

from agents.base_agent import BaseAgent, AgentContext, AgentResponse
from agents.specialists import (
    MercantilAgent,
    AdministrativoAgent,
    ContableAgent,
    PersonalAgent,
)

from pydantic import BaseModel


class Priority(str, Enum):
    """Priority levels for tasks."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"
    CRITICAL = "critical"


class TaskStatus(str, Enum):
    """Task execution status."""
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"
    ESCALATED = "escalated"


@dataclass
class SubTask:
    """A decomposed sub-task for a specialist."""
    specialist: str
    description: str
    id: str = field(default_factory=lambda: str(uuid4())[:8])
    priority: Priority = Priority.NORMAL
    status: TaskStatus = TaskStatus.PENDING
    assigned_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[AgentResponse] = None
    dependencies: list[str] = field(default_factory=list)  # SubTask IDs
    metadata: dict = field(default_factory=dict)


@dataclass
class ChiefDecision:
    """Record of a Chief Agent decision."""
    query: str
    decision_type: str  # "route", "decompose", "escalate", "approve", "reject", "policy"
    rationale: str
    affected_specialists: list[str]
    outcome: str
    confidence: float
    id: str = field(default_factory=lambda: str(uuid4())[:8])
    timestamp: datetime = field(default_factory=datetime.now)


class ChiefAgent(BaseAgent):
    """
    Chief Agent - Executive coordinator with real authority.
    
    Capabilities beyond basic routing:
    - Task decomposition for complex multi-specialist queries
    - Quality control of specialist responses
    - Escalation management for critical issues
    - Policy enforcement and compliance checking
    - Contextual memory across conversations
    - Executive decision logging
    - Escalation management for critical/legal issues
    - Policy enforcement and compliance
    - Proactive monitoring and alerts
    """

    name = "chief"
    description = "Chief Agent: Executive coordinator with decision authority, task decomposition, quality control, and policy enforcement"
    capabilities = [
        "intent_classification",
        "agent_routing",
        "response_consolidation",
        "multi_agent_coordination",
        "task_decomposition",
        "quality_control",
        "escalation_management",
        "policy_enforcement",
        "contextual_memory",
        "executive_decision_making",
        "compliance_checking",
        "crisis_management",
        "proactive_monitoring",
    ]

    def __init__(
        self,
        specialists: dict[str, BaseAgent] | None = None,
        policies: ChiefPolicies | None = None,
        memory: ChiefMemory | None = None,
        client_data: dict | None = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        
        # Specialists
        self.specialists = specialists or {
            "mercantil": MercantilAgent(),
            "administrativo": AdministrativoAgent(),
            "contable": ContableAgent(),
            "personal": PersonalAgent(),
        }
        # Datos reales del tenant inyectados desde la web (BD)
        if client_data:
            for agent in self.specialists.values():
                if hasattr(agent, "bind_context_metadata"):
                    agent.bind_context_metadata({"client_data": client_data})
        
        # Core components
        self.policies = policies or ChiefPolicies()
        self.memory = memory or ChiefMemory()
        self.task_decomposer = TaskDecomposer(self.specialists)
        self.quality_controller = QualityController(self.policies)
        self.escalation_manager = EscalationManager(self.policies)
        
        # State
        self.active_tasks: dict[str, SubTask] = {}
        self.decision_log: list[ChiefDecision] = []
        self.conversation_context: dict[str, Any] = {}
        
        # Configuration
        self.routing_threshold = 0.3
        self.multi_agent_threshold = 0.6
        self.quality_threshold = 0.7
        self.auto_escalate_critical = True

    # ============================================================
    # CORE PROCESSING
    # ============================================================
    
    async def process(self, query: str, context: AgentContext) -> AgentResponse:
        """
        Main entry point with full Chief Agent workflow:
        1. Analyze & classify
        2. Check policies/compliance
        2. Decompose if complex
        3. Route/delegate with context
        4. Quality control
        5. Consolidate & return
        """
        start_time = datetime.now()
        
        # 1. Load conversation context
        await self._load_context(context)
        
        # 2. Policy/Compliance pre-check
        compliance_check = await self.policies.check_compliance(query, context)
        if not compliance_check.compliant:
            return AgentResponse(
                agent=self.name,
                success=False,
                response=f"Consulta rechazada por política: {compliance_check.reason}",
                data={"compliance_check": compliance_check.model_dump()},
                error="policy_violation",
            )
        
        # 3. Classify intent & assess complexity
        scores = await self._classify_intent(query)
        complexity = await self._assess_complexity(query, scores)
        
        # 4. Check for critical/legal issues requiring escalation
        if self.auto_escalate_critical:
            escalation_check = await self.escalation_manager.check_escalation(query, scores, context)
            if escalation_check.should_escalate:
                return await self._handle_escalation(query, context, escalation_check)
        
        # 4. Decide strategy: simple route vs task decomposition
        if complexity.is_complex:
            return await self._process_complex_query(query, context, scores, complexity)
        else:
            return await self._process_simple_query(query, context, scores)
    
    async def _process_simple_query(
        self,
        query: str,
        context: AgentContext,
        scores: dict[str, float],
    ) -> AgentResponse:
        """Route to single best specialist with quality control."""
        best_agent_name = max(scores, key=scores.get)
        best_score = scores[best_agent_name]
        
        if best_score < self.routing_threshold:
            return AgentResponse(
                agent=self.name,
                success=False,
                response="No estoy seguro de qué especialista necesita. ¿Podrías reformular tu consulta con más detalle?",
                data={"scores": scores},
                error="low_confidence",
            )
        
        # Route to specialist
        specialist = self.specialists[best_agent_name]
        context.metadata["chief_routed"] = True
        context.metadata["routed_to"] = best_agent_name
        context.metadata["routing_confidence"] = best_score
        
        result = await specialist.process(query, context)
        
        # Quality control
        qc_result = await self.quality_controller.review(result, query)
        if not qc_result.passed and qc_result.severity >= 0.7:
            # Re-route or escalate
            return await self._handle_quality_failure(query, context, result, qc_result)
        
        # Log decision
        await self._log_decision(
            query=query,
            decision_type="route",
            rationale=f"Routed to {best_agent_name} (confidence: {best_score:.2f})",
            affected_specialists=[best_agent_name],
            outcome="routed",
            confidence=best_score,
        )
        
        # Add Chief metadata
        result.data["chief_metadata"] = {
            "routed_by": "chief",
            "routing_confidence": best_score,
            "quality_score": qc_result.score,
            "processing_time_ms": (datetime.now() - datetime.now()).total_seconds() * 1000,
        }
        
        return result
    
    async def _process_complex_query(
        self,
        query: str,
        context: AgentContext,
        scores: dict[str, float],
        complexity: "ComplexityAssessment",
    ) -> AgentResponse:
        """Decompose into subtasks, delegate, consolidate with quality control."""
        # Decompose into subtasks
        subtasks = await self.task_decomposer.decompose(query, scores, complexity)
        
        # Execute subtasks with dependency resolution
        results = await self._execute_subtasks(subtasks, context)
        
        # Quality control on all results
        qc_results = await self.quality_controller.review_batch(results, query)
        
        # Handle any quality failures
        for i, qc in enumerate(qc_results):
            if not qc.passed and qc.severity >= 0.7:
                results[i] = await self._handle_quality_failure(
                    query, context, results[i], qc
                )
        
        # Consolidate
        consolidated = await self._consolidate_results(query, results, complexity)
        
        # Log decision
        await self._log_decision(
            query=query,
            decision_type="decompose",
            rationale=f"Decomposed into {len(subtasks)} subtasks for {complexity.type}",
            affected_specialists=[s.specialist for s in subtasks],
            outcome="decomposed_and_consolidated",
            confidence=complexity.confidence,
        )
        
        consolidated.data["chief_metadata"] = {
            "strategy": "decomposition",
            "subtasks_count": len(subtasks),
            "specialists_involved": [s.specialist for s in subtasks],
            "complexity_type": complexity.type,
            "quality_scores": [qc.score for qc in qc_results],
        }
        
        return consolidated
    
    # ============================================================
    # SUBTASK EXECUTION
    # ============================================================
    
    async def _execute_subtasks(
        self,
        subtasks: list[SubTask],
        context: AgentContext,
    ) -> list[AgentResponse]:
        """Execute subtasks respecting dependencies."""
        completed: dict[str, AgentResponse] = {}
        remaining = {s.id: s for s in subtasks}
        
        while remaining:
            # Find ready tasks (dependencies met)
            ready = [
                s for s in remaining.values()
                if all(dep in completed for dep in s.dependencies)
            ]
            
            if not ready:
                # Circular dependency or missing dep - execute anyway
                ready = list(remaining.values())[:1]
            
            # Execute ready tasks in parallel
            tasks = []
            for subtask in ready:
                subtask.status = TaskStatus.IN_PROGRESS
                subtask.assigned_at = datetime.now()
                specialist = self.specialists[subtask.specialist]
                
                # Build sub-context
                sub_context = AgentContext(
                    user_id=context.user_id,
                    tenant_id=context.tenant_id,
                    metadata={
                        **context.metadata,
                        "chief_subtask": True,
                        "subtask_id": subtask.id,
                        "subtask_description": subtask.description,
                        "parent_query": context.metadata.get("original_query", ""),
                    },
                )
                
                task_coro = specialist.process(subtask.description, sub_context)
                tasks.append((subtask.id, task_coro))
            
            # Execute
            for subtask_id, coro in tasks:
                try:
                    result = await coro
                    completed[subtask_id] = result
                    remaining[subtask_id].status = TaskStatus.COMPLETED
                    remaining[subtask_id].completed_at = datetime.now()
                    remaining[subtask_id].result = result
                except Exception as e:
                    remaining[subtask_id].status = TaskStatus.REJECTED
                    completed[subtask_id] = AgentResponse(
                        agent=remaining[subtask_id].specialist,
                        success=False,
                        response=f"Error: {str(e)}",
                        error=str(e),
                    )
            
            # Remove completed
            for tid in list(completed.keys()):
                if tid in remaining:
                    del remaining[tid]
        
        return list(completed.values())
    
    # ============================================================
    # QUALITY CONTROL & CONSOLIDATION
    # ============================================================
    
    async def _handle_quality_failure(
        self,
        query: str,
        context: AgentContext,
        result: AgentResponse,
        qc: "QualityCheckResult",
    ) -> AgentResponse:
        """Handle quality failure - re-route or escalate."""
        # Log
        await self._log_decision(
            query=query,
            decision_type="quality_rejection",
            rationale=f"Quality check failed: {qc.reason}",
            affected_specialists=[result.agent],
            outcome="rejected",
            confidence=qc.score,
        )
        
        # Try alternative specialist if confidence was low
        # For now, escalate
        return await self._escalate_quality(query, context, result, qc)
    
    async def _escalate_quality(
        self,
        query: str,
        context: AgentContext,
        result: AgentResponse,
        qc: "QualityCheckResult",
    ) -> AgentResponse:
        """Escalate quality failure."""
        escalation = await self.escalation_manager.create_escalation(
            reason=f"Quality check failed for {result.agent}: {qc.reason}",
            severity=0.8,
            original_query=query,
            failed_response=result,
            qc_result=qc,
            context=context,
        )
        return await self._handle_escalation(query, context, escalation)
    
    async def _consolidate_results(
        self,
        query: str,
        results: list[AgentResponse],
        complexity: "ComplexityAssessment",
    ) -> AgentResponse:
        """Consolidate multiple specialist responses into coherent answer."""
        # Build synthesis prompt
        responses_text = "\n\n".join([
            f"[{r.agent.upper()}] {r.response}" for r in results
        ])
        
        # Use the chief agent to synthesize (in production, use LLM)
        # For now, simple concatenation with executive summary
        summary = f"ANÁLISIS EJECUTIVO ({len(results)} especialistas consultados)\n\n"
        summary += responses_text
        summary += f"\n\n---\nRespuesta consolidada por Chief Agent con control de calidad."
        
        return AgentResponse(
            agent=self.name,
            success=all(r.success for r in results),
            response=summary,
            data={
                "specialist_responses": [r.data for r in results],
                "specialists_consulted": [r.agent for r in results],
                "consolidation_type": "multi_specialist",
            },
        )
    
    # ============================================================
    # ESCALATION HANDLING
    # ============================================================
    
    async def _handle_escalation(
        self,
        query: str,
        context: AgentContext,
        escalation: "EscalationCheck",
    ) -> AgentResponse:
        """Handle critical/legal escalation."""
        await self._log_decision(
            query=query,
            decision_type="escalate",
            rationale=f"Auto-escalation triggered: {escalation.reason}",
            affected_specialists=escalation.specialists,
            outcome="escalated",
            confidence=0.9,
        )
        
        return AgentResponse(
            agent=self.name,
            success=False,
            response=(
                f"⚠️ ESCALACIÓN AUTOMÁTICA\n\n"
                f"Motivo: {escalation.reason}\n"
                f"Severidad: {escalation.severity}\n"
                f"Especialistas notificados: {', '.join(escalation.specialists)}\n\n"
                f"Este asunto requiere revisión humana. Se ha notificado al equipo senior."
            ),
            data={
                "escalation": escalation.model_dump(),
                "escalated_by": "chief",
            },
            error="escalated",
        )
    
    # ============================================================
    # HELPER METHODS
    # ============================================================
    
    async def _classify_intent(self, query: str) -> dict[str, float]:
        """Classify query against all specialists."""
        scores = {}
        for name, agent in self.specialists.items():
            if hasattr(agent, 'can_handle'):
                scores[name] = agent.can_handle(query)
            else:
                scores[name] = 0.0
        return scores
    
    async def _assess_complexity(
        self,
        query: str,
        scores: dict[str, float],
    ) -> "ComplexityAssessment":
        """Assess if query needs decomposition."""

        # Multiple specialists above threshold
        high_scores = [s for s in scores.values() if s >= self.multi_agent_threshold]
        
        # Query length heuristic
        is_long = len(query) > 500
        
        # Multiple domains detected
        multi_domain = len(high_scores) >= 2
        
        is_complex = multi_domain or is_long
        
        if multi_domain:
            ctype = "multi_domain"
        elif is_long:
            ctype = "long_query"
        else:
            ctype = "simple"
        
        return ComplexityAssessment(
            is_complex=is_complex,
            type=ctype,
            confidence=0.8 if is_complex else 0.9,
            specialist_count=len(high_scores),
        )
    
    async def _load_context(self, context: AgentContext):
        """Load conversation context from memory."""
        if context.correlation_id:
            stored = await self.memory.get_conversation(context.correlation_id)
            if stored:
                self.conversation_context = stored
    
    async def _save_context(self, context: AgentContext):
        """Save conversation context to memory."""
        if context.correlation_id:
            await self.memory.save_conversation(
                context.correlation_id,
                self.conversation_context,
            )
    
    async def _log_decision(
        self,
        query: str,
        decision_type: str,
        rationale: str,
        affected_specialists: list[str],
        outcome: str,
        confidence: float,
    ):
        """Log executive decision for audit trail."""
        decision = ChiefDecision(
            query=query[:200],
            decision_type=decision_type,
            rationale=rationale,
            affected_specialists=affected_specialists,
            outcome=outcome,
            confidence=confidence,
        )
        self.decision_log.append(decision)
        await self.memory.log_decision(decision)
    
    # ============================================================
    # PUBLIC API
    # ============================================================
    
    def get_decision_log(self, limit: int = 50) -> list[ChiefDecision]:
        """Get recent executive decisions."""
        return self.decision_log[-limit:]
    
    def get_active_tasks(self) -> dict[str, SubTask]:
        """Get currently active subtasks."""
        return self.active_tasks
    
    def get_specialist_status(self) -> dict[str, dict]:
        """Get status of all specialists."""
        return {
            name: {
                "available": True,
                "capabilities": agent.capabilities,
                "last_used": self.memory.get_last_used(name),
            }
            for name, agent in self.specialists.items()
        }
    
    async def proactive_check(self, context: AgentContext) -> list[str]:
        """Proactive monitoring - check for upcoming deadlines, compliance issues."""
        alerts = []
        
        # Check calendar deadlines
        # Check compliance
        # Check pending tasks
        
        return alerts


# ============================================================
# SUPPORTING CLASSES (Inline for simplicity)
# ============================================================

from pydantic import BaseModel, Field


class ComplianceCheck(BaseModel):
    compliant: bool
    reason: str | None = None
    risk_level: str = "low"


class ComplexityAssessment(BaseModel):
    is_complex: bool
    type: str
    confidence: float
    specialist_count: int


class QualityCheckResult(BaseModel):
    passed: bool
    score: float
    reason: str | None = None
    severity: float = 0.0


class EscalationCheck(BaseModel):
    should_escalate: bool
    reason: str
    severity: float
    specialists: list[str]


# Placeholder imports for components (implement in separate files)
class ChiefPolicies:
    async def check_compliance(self, query: str, context: AgentContext) -> ComplianceCheck:
        # Check for PII, legal advice limits, etc.
        return ComplianceCheck(compliant=True)


class ChiefMemory:
    async def get_conversation(self, conv_id: str) -> dict:
        return {}
    async def save_conversation(self, conv_id: str, data: dict):
        pass
    async def log_decision(self, decision: "ChiefDecision"):
        pass
    def get_last_used(self, specialist: str) -> Optional[datetime]:
        return None


class TaskDecomposer:
    def __init__(self, specialists: dict):
        self.specialists = specialists
    
    async def decompose(
        self,
        query: str,
        scores: dict[str, float],
        complexity: ComplexityAssessment,
    ) -> list[SubTask]:
        """Decompose complex query into specialist subtasks."""
        subtasks = []
        
        # Get top specialists by score
        sorted_specs = sorted(
            [(name, score) for name, score in scores.items() if score >= 0.3],
            key=lambda x: x[1],
            reverse=True,
        )
        
        for i, (name, score) in enumerate(sorted_specs[:3]):
            # Create subtask description based on specialist domain
            domain_prompts = {
                "mercantil": "Aspectos mercantiles: constitución, estatutos, juntas, disolución",
                "administrativo": "Aspectos administrativos: licencias, recursos, contratos públicos",
                "contable": "Aspectos contables/fiscales: modelos, cierres, impuestos",
                "personal": "Aspectos laborales: nóminas, contratos, SS, PRL",
            }
            
            subtasks.append(SubTask(
                specialist=name,
                description=f"{domain_prompts.get(name, '')}: {query}",
                priority=Priority.HIGH if score > 0.7 else Priority.NORMAL,
                metadata={"source_score": score},
            ))
        
        return subtasks


class QualityController:
    def __init__(self, policies: ChiefPolicies):
        self.policies = policies
    
    async def review(self, result: AgentResponse, query: str) -> QualityCheckResult:
        # Basic quality checks
        score = 1.0
        reasons = []
        
        if not result.success:
            score -= 0.3
            reasons.append("Specialist returned error")
        
        if not result.response or len(result.response) < 50:
            score -= 0.2
            reasons.append("Response too short")
        
        if "error" in result.data:
            score -= 0.2
            reasons.append("Error in response data")
        
        return QualityCheckResult(
            passed=score >= 0.7,
            score=score,
            reason="; ".join(reasons) if reasons else None,
            severity=1.0 - score,
        )
    
    async def review_batch(self, results: list[AgentResponse], query: str) -> list[QualityCheckResult]:
        return [await self.review(r, query) for r in results]


class EscalationManager:
    def __init__(self, policies: ChiefPolicies):
        self.policies = policies
    
    async def check_escalation(
        self,
        query: str,
        scores: dict[str, float],
        context: AgentContext,
    ) -> EscalationCheck:
        # Check for legal/urgent keywords
        urgent_keywords = [
            "urgente", "inmediato", "denuncia", "demanda", "embargo",
            "inspección", "sanción", "fallecimiento", "accidente",
            "despido", "huelga", "concurso", "quiebra",
        ]
        
        query_lower = query.lower()
        matches = [kw for kw in urgent_keywords if kw in query_lower]
        
        if matches:
            return EscalationCheck(
                should_escalate=True,
                reason=f"Palabras clave urgentes detectadas: {', '.join(matches)}",
                severity=0.9,
                specialists=["mercantil", "administrativo", "contable", "personal"],
            )
        
        return EscalationCheck(should_escalate=False, reason="", severity=0.0, specialists=[])
    
    async def create_escalation(
        self,
        reason: str,
        severity: float,
        original_query: str,
        failed_response: AgentResponse,
        qc_result: Any,
        context: AgentContext,
    ) -> dict:
        return {
            "reason": reason,
            "severity": severity,
            "query": original_query,
            "failed_agent": failed_response.agent,
            "qc_score": qc_result.score if qc_result else 0,
        }