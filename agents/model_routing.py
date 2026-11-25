"""GESTIA Agents - Model routing (Fase E/F).

Elige el mejor modelo de IA por tarea. Configurable por agente y por tipo de
operación, permitiendo controlar coste vs. calidad.

Regla de plataforma: las tareas mecánicas NO usan LLM (n8n); el routing se
usa en operaciones que requieren razonamiento. La configuración vive en
`MODEL_MAP` y puede sobreescribirse por entorno/archivo.

Cuando se conecte el LLM real (Fase H), cada función del agente llamará a
`resolve(tarea)` para obtener el modelo con el que invocar al proveedor.
"""

from __future__ import annotations

import os

# Modelo por defecto (proveedor OpenRouter). Configurable vía entorno.
DEFAULT_MODEL = os.getenv("GESTIA_DEFAULT_MODEL", "deepseek/deepseek-v4-flash-0731")

# Mapa tarea -> modelo recomendado. Rutas por especialista.
MODEL_MAP: dict[str, str] = {
    # Tareas baratas (router / clasificar / extraer)
    "router": os.getenv("GESTIA_MODEL_ROUTER", "deepseek/deepseek-v4-flash-0731"),
    "clasificar_intencion": os.getenv("GESTIA_MODEL_CLASIF", "deepseek/deepseek-v4-flash-0731"),
    "extraer_datos": os.getenv("GESTIA_MODEL_EXTRAER", "deepseek/deepseek-v4-flash-0731"),
    # Razonamiento (por dominio - modelos potentes)
    "razonamiento_contable": os.getenv("GESTIA_MODEL_CONTABLE", "openrouter/auto"),
    "razonamiento_mercantil": os.getenv("GESTIA_MODEL_MERCANTIL", "openrouter/auto"),
    "razonamiento_personal": os.getenv("GESTIA_MODEL_PERSONAL", "openrouter/auto"),
    "razonamiento_administrativo": os.getenv("GESTIA_MODEL_ADMIN", "openrouter/auto"),
    # Elaboración de documentos
    "redactar_documento": os.getenv("GESTIA_MODEL_REDACT", "openrouter/auto"),
    # Consolidación / síntesis
    "consolidar": os.getenv("GESTIA_MODEL_CONSOLIDAR", "deepseek/deepseek-v4-flash-0731"),
}

# Barato y rápido -> sin LLM (determinista)
MECANICAS = {"listar", "sumar", "contar", "generar_xml", "conciliar", "calcular_nomina"}


class ModelRouter:
    """Resuelve el modelo a usar para cada tarea/dominio."""

    def __init__(self, mapa: dict[str, str] | None = None):
        self.mapa = mapa or MODEL_MAP

    def resolve(self, tarea: str) -> str | None:
        """Devuelve el modelo para una tarea, o None si no aplica LLM."""
        if tarea in MECANICAS:
            return None  # determinista, sin LLM
        return self.mapa.get(tarea, DEFAULT_MODEL)

    def resolve_especialista(self, dominio: str) -> str:
        """Modelo de razonamiento para un especialista."""
        key = f"razonamiento_{dominio}"
        return self.mapa.get(key, DEFAULT_MODEL)

    def resumen(self) -> dict[str, str]:
        """Devuelve el mapa para auditoría (cuál se usa por tarea)."""
        return dict(self.mapa)


# Instancia global
ROUTER = ModelRouter()