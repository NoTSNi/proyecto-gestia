"""GESTIA Web - Detección proactiva de beneficios fiscales (Fase F).

Analiza los datos de cada empresa cliente frente a los requisitos de
beneficios/deducciones de la KB curada, y produce ALERTAS para la asesoría:

"ES cliente X podría beneficiarse de la deducción por I+D+i si acredita
gastos; le falta justificar los proyectos."

Regla del sistema: el agente PROPONE, la asesoría DECIDE. Estas alertas son
recomendaciones con fuentes, nunca decisiones ejecutadas.
"""

from __future__ import annotations

from agents.knowledge_base import KB_INSTANCE

# Reglas de detección: (clave_requisito, descripcion_beneficio, fuentes, evaluador)
# El evaluador recibe el dict `empresa` y devuelve:
#   (aplica: bool, cumple_requisitos: bool|None, razon: str)
#
# `aplica`: el beneficio es relevante para este tipo de empresa.
# `cumple_requisitos`: True si ya cumple, False si le falta algo, None si no se sabe.

REGLAS_BENEFICIOS = [
    {
        "id": "idd_i",
        "beneficio": "Deducción por actividades de I+D+i (art. 35 LIS)",
        "fuentes": ["Ley 27/2014 (LIS)", "art. 35"],
        "evaluador": lambda e: _eval_idd(e),
    },
    # La reserva de capitalización (art. 25) aplica a casi toda empresa con
    # beneficio: se trata como conocimiento consultable en la KB, NO como
    # alerta proactiva (evitaría ruido al señalar a todos los clientes).
    {
        "id": "innovacion_reducida",
        "beneficio": "Tratamientos especiales por sector tecnológico/energético",
        "fuentes": ["Ley 27/2014", "deducciones regionales"],
        "evaluador": lambda e: _eval_sector(e),
    },
]

# Keywords del negocio que sugieren actividad elegible
_KEYWORDS_IDD = ["desarrollo", "software", "investigación", "i+d", "tecnología",
                 "ingenier", "biotec", "farmac", "laboratorio", "industria", "prototipo"]
_KEYWORDS_SECTOR_REDUCIDO = ["digitalización", "software", "tecnología", "energía",
                             "renovable", "exportación"]


def _eval_idd(empresa: dict):
    nombre = (str(empresa.get("nombre") or "") + " " + str(empresa.get("nombre_comercial") or "")).lower()
    cnae = str(empresa.get("cnae") or "")
    meta = str(empresa.get("metadata_json") or "").lower()

    sugerido = any(k in nombre for k in _KEYWORDS_IDD) or any(k in meta for k in _KEYWORDS_IDD)
    if not sugerido:
        return False, None, "No hay indicios de actividad de I+D+i en los datos de la empresa."
    # Tecnología/sector -> potencialmente elegible pero falta justificar gastos
    return True, None, (
        "La actividad sugiere posibles gastos de I+D+i. La deducción exige acreditar "
        "y documentar los proyectos (memoria técnica, gastos, personal cualificado). "
        "Conviene que la asesoría solicite al cliente el detalle de proyectos de I+D."
    )


def _eval_reserva(empresa: dict):
    # Requiere incremento de fondos propios y que parte del beneficio se reserve
    estado = str(empresa.get("estado") or "")
    if estado == "baja":
        return False, None, "Empresa dada de baja."
    return True, None, (
        "La reserva de capitalización exige: tener beneficio en el ejercicio, "
        "incrementar fondos propios y dotar la reserva. La asesoría debe revisar el "
        f"último balance de {empresa.get('nombre', 'la empresa')} (CNAE "
        f"{empresa.get('cnae') or '?'})."
    )


def _eval_sector(empresa: dict):
    nombre = (str(empresa.get("nombre") or "")).lower()
    cnae = str(empresa.get("cnae") or "")
    if any(k in nombre for k in _KEYWORDS_SECTOR_REDUCIDO) or cnae.startswith(("62", "63", "35")):
        return True, None, (
            "Actividad tecnológica/energética detectada: revisar deducciones y "
            "tipos reducidos aplicables (I+D, digitalización, bonificaciones)."
        )
    return False, None, "Sin indicios de sector con tratamientos especiales."


async def detectar_beneficios_empresa(empresa: dict) -> list[dict]:
    """Devuelve las alertas de beneficios aplicables a una empresa."""
    alertas = []
    for regla in REGLAS_BENEFICIOS:
        try:
            aplica, cumple, razon = regla["evaluador"](empresa)
        except Exception:
            continue
        if not aplica:
            continue
        alertas.append({
            "id": regla["id"],
            "beneficio": regla["beneficio"],
            "fuentes": regla["fuentes"],
            "razon": razon,
            "cumple": cumple,
            "accion": (
                "Cumple requisitos, revisar documentación para aplicar."
                if cumple is True else
                "Requiere revisión por la asesoría para confirmar elegibilidad."
            ),
        })
    return alertas


async def detectar_beneficios_todas(empresas: list[dict]) -> list[dict]:
    """Analiza todas las empresas y devuelve las alertas (para el panel asesor)."""
    todas = []
    for emp in empresas:
        alertas = await detectar_beneficios_empresa(emp)
        for a in alertas:
            a["empresa_id"] = emp["id"]
            a["empresa_nombre"] = emp["nombre"]
            a["empresa_nif"] = emp["nif"]
        todas.extend(alertas)
    return todas