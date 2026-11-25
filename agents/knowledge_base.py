"""GESTIA Agents - Base de Conocimiento curada por especialista (Fase F).

Cada especialista consulta su propia KB (contable, mercantil, laboral,
administrativo) EN LOCAL (FTS5) sin depender de servicios externos.

IMPORTANTE: este conocimiento es REFERENCIA orientativa y puede quedar
desactualizado. Regla del sistema: el agente PROPONE, la asesoría DECIDE.
Las fechas/requisitos deben verificarse en fuente oficial (AEAT, SS, RM)
antes de ejecutar. Cada entrada lleva fuentes y fecha de vigencia.

Estructura: KNOWLEDGE[dominio] = [ {titulo, texto, fuentes, vigente_desde}, ... ]
"""

from __future__ import annotations

import re

KNOWLEDGE: dict[str, list[dict]] = {
    # =====================================================================
    # CONTABLE / FISCAL
    # =====================================================================
    "contable": [
        {
            "titulo": "Modelo 303 - IVA (autoliquidación trimestral/mensual)",
            "texto": (
                "Autoliquidación trimestral del IVA (mensual para grandes empresas y "
                "grupos). Se declara en enero-abril-julio-octubre (Q1: hasta 20/04, "
                "Q2: hasta 20/07, Q3: hasta 20/10, Q4: hasta 30/01). En régimen "
                "simplificado se usa el mismo formulario. Incluye cuotas devengadas y "
                "deducibles, resultado a ingresar o a compensar/compensación. Se "
                "presenta por internet (AEAT) con certificado o con Cl@ve. Resultado: "
                "a ingresar si el IVA devengado supera el deducible; a compensar en "
                "caso contrario."
            ),
            "fuentes": ["AEAT - Modelo 303", "Real Decreto 1624/1992"],
            "vigente_desde": "2024-01-01",
        },
        {
            "titulo": "Modelo 111 - Retenciones IRPF (trimestral)",
            "texto": (
                "Declaración trimestral de retenciones a cuenta del IRPF sobre "
                "trabajadores, arrendamientos, profesionales y actividades. Plazos: "
                "hasta 20/04 (Q1), 20/07 (Q2), 20/10 (Q3), 30/01 (Q4). Cuando los "
                "trabajadores son varios y superan umbrales se usa el modelo 111; el "
                "resumen anual va en el 190."
            ),
            "fuentes": ["AEAT - Modelo 111", "Real Decreto 2066/1999"],
            "vigente_desde": "2024-01-01",
        },
        {
            "titulo": "Modelo 390 - Resumen anual del IVA",
            "texto": (
                "Declaración-resumen anual del IVA que acompaña a las liquidaciones "
                "trimestrales. Se presenta entre el 1 y el 30 de enero del año "
                "siguiente. Incluye el conjunto de operaciones del año, las cuotas "
                "deducibles y las compensaciones. Es obligatoria para todos los "
                "sujetos pasivos salvo los acogidos al régimen simplificado que no "
                "estén obligados a presentarla por otras razones."
            ),
            "fuentes": ["AEAT - Modelo 390"],
            "vigente_desde": "2024-01-01",
        },
        {
            "titulo": "Modelo 200 - Impuesto sobre Sociedades",
            "texto": (
                "Autoliquidación anual del Impuesto sobre Sociedades. Se presenta en "
                "los 25 primeros días naturales siguientes a los 6 meses posteriores a "
                "la conclusión del periodo impositivo (para sociedades con ejercicio "
                "natural: del 1 al 25 de julio). Base imponible (27% o 25/23% pymes), "
                "deducciones y bonificaciones. Importante para el análisis: el "
                "resultado del 303/IVA NO es el resultado contable; el IS se calcula "
                "sobre el resultado contable ajustado."
            ),
            "fuentes": ["AEAT - Modelo 200", "LIS 27/2014"],
            "vigente_desde": "2025-01-01",
        },
        {
            "titulo": "Beneficios y deducciones fiscales frecuentes",
            "texto": (
                "1) Deducción por I+D+i (art. 35 LIS): 25% gastos + 42% exceso sobre "
                "media, más 17% personal cualificado. 2) Deducción por inversión en "
                "producción de bienes corporales nuevos (pymes, atípica). 3) Reserva de "
                "capitalización (art. 25 LIS): exención del 10% del incremento de fondos "
                "propios, hasta 10% de la base. 4) Libertad de amortización para pymes. "
                "5) Para autónomos/EPD: deducción de gastos, y en IRPF por actividades "
                "económicas la deducción por inicio de actividad. Detectar qué beneficios "
                "aplica cada cliente requiere ver su base, su inversión en I+D y su "
                "incremento de fondos propios vs. requisitos."
            ),
            "fuentes": ["Ley 27/2014 (LIS)", "Real Decreto Legislativo 5/2004 (IRPF)"],
            "vigente_desde": "2025-01-01",
        },
        {
            "titulo": "Cierre contable anual y elaboración de cuentas",
            "texto": (
                "El cierre contable comprende: inventario de existencias, periodicación "
                "de gastos e ingresos, amortizaciones, provisiones, ajustes por "
                "inflación si aplican, conciliación bancaria y reclasificaciones. "
                "Resultado: la cuenta de pérdidas y ganancias y el balance. Las cuentas "
                "se aprueban en junta y se depositan en el Registro Mercantil en el mes "
                "siguiente a la aprobación (dentro de los 6 primeros meses del ejercicio)."
            ),
            "fuentes": ["Código de Comercio", "PGC Real Decreto 1514/2007"],
            "vigente_desde": "2024-01-01",
        },
        {
            "titulo": "Modelo 347 - Operaciones con terceros",
            "texto": (
                "Declaración anual de operaciones con terceros por importe superior a "
                "3.005,06 € (IVA/IRPF). Se presenta en febrero (formato telemático). "
                "Es obligatoria para quien supere umbrales de facturación."
            ),
            "fuentes": ["AEAT - Modelo 347"],
            "vigente_desde": "2024-01-01",
        },
        {
            "titulo": "Modelo 349 - Operaciones intracomunitarias",
            "texto": (
                "Declaración recapitulativa de operaciones intracomunitarias (ventas y "
                "compras de bienes/servicios en la UE). Periodicidad mensual si superas "
                "umbral, si no, trimestral. Se acompaña del modelo 303."
            ),
            "fuentes": ["AEAT - Modelo 349"],
            "vigente_desde": "2024-01-01",
        },
        {
            "titulo": "TC1/TC2 - Cotizaciones Seguridad Social",
            "texto": (
                "El TC1 es el boletín de cotización mensual (importe a pagar de cuotas "
                "de la empresa y del trabajador). El TC2 es la relación nominal de "
                "trabajadores del mes. Se liquidan entre el 1 y el último día hábil del "
                "mes siguiente (sistema RED/Sistema de Liquidación Directa). El cálculo "
                "depende de: base de cotización por contingencias comunes y "
                "profesionales, tipos (31-35% aprox. empresarial) y porcentajes del "
                "trabajador. Para calcular el coste real hay que multiplicar la base "
                "por los tipos vigentes."
            ),
            "fuentes": ["SEPE/TGSS - Sistema de Liquidación Directa"],
            "vigente_desde": "2024-01-01",
        },
    ],
    # =====================================================================
    # MERCANTIL
    # =====================================================================
    "mercantil": [
        {
            "titulo": "Constitución de sociedad limitada",
            "texto": (
                "Para constituir una SL: 1) certificación negativa de denominación en el "
                "Registro Mercantil Central; 2) otorgamiento de la escritura ante "
                "notario (con estatutos); 3) pago del capital social mínimo (3.000 €, "
                "desembolsado); 4) NIF provisional; 5) inscripción en el Registro "
                "Mercantil Provincial (la sociedad adquiere personalidad); 6) alta en "
                "actividad económica (IAE/AEAT), seguridad social e IVA/IRPF si procede."
            ),
            "fuentes": ["Ley de Sociedades de Capital 1/2010", "RMC"],
            "vigente_desde": "2024-01-01",
        },
        {
            "titulo": "Juntas generales de socios",
            "texto": (
                "La junta general ordinaria se convoca por el administrador y debe "
                "celebrarse dentro de los 6 primeros meses del ejercicio para aprobar las "
                "cuentas anuales. La convocatoria se publica en la web de la sociedad "
                "(o en BORME). Las juntas extraordinarias se celebran cuando lo pide la "
                "ley, un porcentaje del capital o el interés social. Los acuerdos se "
                "transcriben en el libro de actas."
            ),
            "fuentes": ["Ley de Sociedades de Capital 1/2010 (art. 163-175)"],
            "vigente_desde": "2024-01-01",
        },
        {
            "titulo": "Libros obligatorios y depósito de cuentas",
            "texto": (
                "La sociedad debe llevar: libro de inventarios y cuentas anuales, libro "
                "diario, libro de actas de juntas, y libro registro de socios. Las "
                "cuentas anuales aprobadas se depositan en el Registro Mercantil en el "
                "mes siguiente a la aprobación (dentro de los 6 primeros meses del "
                "ejercicio). El depósito permite 'el cierre registral' si no se hace."
            ),
            "fuentes": ["Ley de Sociedades de Capital 1/2010", "Registro Mercantil"],
            "vigente_desde": "2024-01-01",
        },
        {
            "titulo": "Disolución y liquidación de sociedad",
            "texto": (
                "Causas de disolución (art. 363 LSC): cese en el ejercicio de la "
                "actividad, pérdidas que reduzcan el patrimonio a menos de la mitad del "
                "capital, reducción del capital por debajo del mínimo, etc. La disolución "
                "la acuerda la junta o la obtiene judicialmente. Tras ella se abre el "
                "periodo de liquidación: inventario, pago de deudas, adjudicación del "
                "remanente a socios, elevar a público el balance final y la inscripción "
                "de la extinción."
            ),
            "fuentes": ["Ley de Sociedades de Capital 1/2010 (art. 363-396)"],
            "vigente_desde": "2024-01-01",
        },
        {
            "titulo": "Aumento y reducción de capital",
            "texto": (
                "Aumento de capital: por aportaciones dinerarias, no dinerarias, o "
                "compensación de créditos. Requiere acuerdo de junta, escritura y "
                "modificación estatutaria, inscripción en el RM (derecho de suscripción "
                "preferente). Reducción: puede ser por devolución de aportaciones, por "
                "pérdidas (para reequilibrar) o por constitución de reservas; aplican "
                "reglas de protección de acreedores."
            ),
            "fuentes": ["Ley de Sociedades de Capital 1/2010 (art. 295-360)"],
            "vigente_desde": "2024-01-01",
        },
    ],
    # =====================================================================
    # LABORAL / PERSONAL
    # =====================================================================
    "personal": [
        {
            "titulo": "Tipos de contrato laboral",
            "texto": (
                "Contrato indefinido (ordinario), temporal por circunstancias de la "
                "producción (hasta 6 meses ampliable), obra o servicio (solo para "
                "actividades concretas con duración determinada), prácticas (para "
                "titulados, 6 meses a 2 años), formación en alternancia, relevo, y "
                "fijos discontinuos. El contrato debe constar por escrito, y la empresa "
                "debe comunicar las altas a la Seguridad Social antes del inicio."
            ),
            "fuentes": ["Real Decreto Legislativo 2/2015 (Estatuto de los Trabajadores)"],
            "vigente_desde": "2024-01-01",
        },
        {
            "titulo": "Nómina mensual - estructura",
            "texto": (
                "La nómina tiene: encabezado (datos de empresa y trabajador, periodo), "
                "devengos (salario base, pluses, complementos, pagas prorrateadas, horas "
                "extra) y deducciones (seguridad social: contingencias comunes 4,7%, "
                "desempleo, formación; IRPF según retención). Resultado: el neto a "
                "percibir = devengos - deducciones. Para calcular correctamente hay que "
                "conocer el convenio colectivo aplicable y la base de cotización."
            ),
            "fuentes": ["Estatuto de los Trabajadores", "Convenio colectivo aplicable"],
            "vigente_desde": "2024-01-01",
        },
        {
            "titulo": "IRPF retenciones del trabajo",
            "texto": (
                "La retención de IRPF depende de: importe de la retribución anual, "
                "situación familiar (número de hijos y de pareja con rentas), y "
                "circunstancias personales. El tipo se aplica sobre el salario bruto y "
                "se resta en cada nómina. La retención se regulariza en la declaración "
                "anual. Para calcularla se usan las tablas del Reglamento de IRPF."
            ),
            "fuentes": ["Real Decreto 439/2007 (Reglamento IRPF)"],
            "vigente_desde": "2024-01-01",
        },
        {
            "titulo": "Altas, bajas y variaciones en Seguridad Social",
            "texto": (
                "Las altas, bajas y variaciones de trabajadores se comunican a la "
                "Seguridad Social con carácter previo (alta antes del inicio de la "
                "relación). Sistema RED o Sistema de Liquidación Directa (SLD). La baja "
                "se comunica al cese. La no comunicación puede generar recargos. "
                "También hay que comunicar las variaciones de datos (jornada, salario, "
                "grupo)."
            ),
            "fuentes": ["Real Decreto 84/1996", "TGSS"],
            "vigente_desde": "2024-01-01",
        },
        {
            "titulo": "Prevención de riesgos laborales (PRL)",
            "texto": (
                "La empresa debe: planificar la prevención, evaluar los riesgos, formar "
                "e informar a los trabajadores, realizar reconocimientos médicos, y "
                "coordinar si hay contratas. Ante accidentes laborales se debe notificar "
                "y elaborar el parte. El incumplimiento puede acarrear sanciones y "
                "responsabilidades."
            ),
            "fuentes": ["Ley 31/1995 de PRL"],
            "vigente_desde": "2024-01-01",
        },
    ],
    # =====================================================================
    # ADMINISTRATIVO
    # =====================================================================
    "administrativo": [
        {
            "titulo": "Licencias de obra y actividad",
            "texto": (
                "Toda obra de nueva construcción, ampliación, reforma que afecte a "
                "estructura o cambio de uso suele requerir licencia municipal. La "
                "licencia de actividad (apertura) se pide antes de iniciar la actividad. "
                "El silencio administrativo y los plazos dependen de la ordenanza "
                "municipal. Si se deniega, cabe recurso de alzada ante la propia "
                "administración o contencioso."
            ),
            "fuentes": ["Ley 7/1985 Reguladora de las Bases del Régimen Local", "TRLSRU 7/2015"],
            "vigente_desde": "2024-01-01",
        },
        {
            "titulo": "Subvenciones públicas",
            "texto": (
                "Las subvenciones a empresas salen en convocatorias (BOE o autonómicas). "
                "El procedimiento: solicitud, resolución, justificación del gasto y, si "
                "aplica, reintegro. La empresa debe disponer de la documentación "
                "justificativa (facturas, medios de pago) durante el plazo exigido y "
                "estar al corriente de obligaciones tributarias y frente a la SS. "
                "Beneficiarse de una subvención puede condicionar la actividad."
            ),
            "fuentes": ["Ley 38/2003 General de Subvenciones"],
            "vigente_desde": "2024-01-01",
        },
        {
            "titulo": "Recursos y reclamaciones administrativas",
            "texto": (
                "Frente a actos administrativos caben: recurso de alzada (si es acto de "
                "órgano subordinado, ante el superior) y recurso de reposición "
                "(potestativo, ante el mismo órgano). Ambos suelen tener plazo de 1 mes "
                "desde la notificación. Agotada la vía administrativa, cabe recurso "
                "contencioso-administrativo (2 meses). Para sanciones tributarias el "
                "plazo es distinto."
            ),
            "fuentes": ["Ley 39/2015 del Procedimiento Administrativo Común"],
            "vigente_desde": "2024-01-01",
        },
        {
            "titulo": "Contratación pública (licitaciones)",
            "texto": (
                "La empresa puede presentarse a licitaciones de la administración. El "
                "procedimiento está regulado por la LCSP 9/2017. Requiere: acreditación "
                "de solvencia, no estar incurso en prohibiciones de contratar, y "
                "documentación de capacidad. Los plazos de presentación suelen ser de 15 "
                "a 30 días naturales. La adjudicación puede ser por procedimiento "
                "abierto, restringido o negociado."
            ),
            "fuentes": ["Ley 9/2017 de Contratos del Sector Público"],
            "vigente_desde": "2024-01-01",
        },
        {
            "titulo": "Expedientes sancionadores",
            "texto": (
                "Ante una inspección o denuncia, la administración puede incoar un "
                "expediente sancionador. El interesado puede presentar alegaciones y "
                "pruebas, y recurrir la resolución. Plazos típicos: 10 días para "
                "alegaciones tras el pliego. La sanción se gradúa según la gravedad. No "
                "obstante, siempre conviene evaluar si cabe paralización o acuerdo."
            ),
            "fuentes": ["Ley 39/2015"],
            "vigente_desde": "2024-01-01",
        },
    ],
}


class KnowledgeBase:
    """Búsqueda FTS-like local sobre el conocimiento curado por dominio."""

    def __init__(self):
        self._tokens: dict[str, list[tuple[float, dict]]] = {}
        for dominio, entries in KNOWLEDGE.items():
            idx = []
            for e in entries:
                texto = f"{e['titulo']} {e['texto']}".lower()
                # score simple por match de palabras significativas
                idx.append((texto, e))
            self._tokens[dominio] = idx

    def buscar(self, dominio: str, query: str, top_k: int = 4) -> list[dict]:
        """Devuelve entradas del dominio ordenadas por relevancia a la query."""
        entries = KNOWLEDGE.get(dominio, [])
        if not entries or not query:
            return []

        palabras = [p for p in re.findall(r"[a-záéíóúñ]{3,}", query.lower()) if p not in
                    ("que", "para", "una", "con", "los", "las", "del", "por", "como", "cuanto", "tengo")]
        if not palabras:
            return entries[:top_k]

        scored = []
        for e in entries:
            texto = f"{e['titulo']} {e['texto']}".lower()
            score = sum(2 if p in e["titulo"].lower() else (1 if p in texto else 0)
                        for p in palabras)
            if score > 0:
                scored.append((score, e))
        scored.sort(key=lambda x: -x[0])
        return [e for _, e in scored[:top_k]]

    def buscar_todas(self, query: str, top_k: int = 3) -> dict[str, list[dict]]:
        """Busca en todas las KB y devuelve por dominio."""
        return {d: self.buscar(d, query, top_k) for d in KNOWLEDGE}


# Instancia global reutilizable (los agentes se crean por consulta en la web)
KB_INSTANCE = KnowledgeBase()