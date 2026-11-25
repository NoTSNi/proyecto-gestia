"""GESTIA Agents - Control de coste y anti-bucle (Fase E).

Presupuesto por consulta para evitar que un agente se quede en bucle y
gaste tokens de forma ilimitada.

Mecanismos:
- Timeout global por consulta (asyncio)
- Máximo de iteraciones de descomposición de subtareas (anti-bucle)
- Máximo de subtareas ejecutadas por consulta
- Contador de tokens/coste estimado: cada operación consume tokens
  simulados (para cuando se conecten LLM reales, y para detectar fugas hoy)
- Circuit breaker básico: si una consulta agota su presupuesto, se marca
  y el sistema la corta devolviendo un error controlado
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field


# Coste en "tokens simulados" por operación. Cuando los agentes usen LLM real,
# estos se sustituyen por el conteo real de tokens del proveedor.
@dataclass
class CostePorOperacion:
    clasificar_intencion: int = 120
    comprobar_compliance: int = 80
    evaluar_escalado: int = 100
    subtarea: int = 400          # cada subtarea delegada a un especialista
    calidad_review: int = 150    # cada revisión de calidad
    consolidar: int = 200        # consolidación de resultados complejos


@dataclass
class AgentBudget:
    """Presupuesto de una consulta."""

    max_iteraciones: int = 3          # máx. pasadas de descomposición (anti-bucle)
    max_subtareas: int = 8            # máx. subtareas por consulta
    timeout_seg: float = 30.0         # timeout global por consulta
    token_limit: int = 100_000        # tope de tokens gastados por consulta
    costes: CostePorOperacion = field(default_factory=CostePorOperacion)

    # Estado (mutado durante la consulta)
    tokens_gastados: int = field(default=0, repr=False)
    operaciones: int = field(default=0, repr=False)
    excedido: bool = field(default=False, repr=False)
    inicio: float = field(default=0.0, repr=False)

    def start(self) -> None:
        self.tokens_gastados = 0
        self.operaciones = 0
        self.excedido = False
        self.inicio = time.time()

    def gastar(self, cantidad: int) -> bool:
        """Consume tokens. Devuelve False si se supera el límite."""
        self.tokens_gastados += cantidad
        self.operaciones += 1
        if self.tokens_gastados > self.token_limit or time.time() - self.inicio > self.timeout_seg:
            self.excedido = True
            return False
        return True

    def bajo_presupuesto(self) -> bool:
        return not self.excedido and self.tokens_gastados < self.token_limit

    @property
    def segundos_restantes(self) -> float:
        return max(0.0, self.timeout_seg - (time.time() - self.inicio))

    @property
    def informe(self) -> dict:
        return {
            "tokens_estimados": self.tokens_gastados,
            "operaciones": self.operaciones,
            "excedido": self.excedido,
            "timeout_seg": self.timeout_seg,
        }