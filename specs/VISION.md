# GESTIA — Visión y Alcance

## Qué es
Sistema multi-agente (estilo LEXIA_OS) para **asesoría/gestoría multi-tenant** que gestiona 4 dominios:
1. **Mercantil** — Constitución, libros oficiales, juntas, modificaciones estatutarias, disoluciones
2. **Administrativo** — Licencias, subvenciones, recursos, contratos públicos, patrimonio
3. **Contable** — Contabilidad, impuestos (IVA, IS, IRPF), SII, facturae, cuentas anuales, conciliación
4. **Personal/Laboral** — Nóminas, contratos, SS, prevención, ERTE/ERE, inspecciones, convenios

## Arquitectura objetivo (híbrida GESTIA Core + n8n)

```
┌─────────────────────────────────────────────────────────────────────┐
│                        GESTIA CORE (Python/FastAPI)                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                  │
│  │  Agentes    │  │  LLM Calls  │  │  RAG/Vector │  ← Solo lo que  │
│  │  (Lógica    │  │  (Razonam.) │  │  (Búsqueda) │     requiere    │
│  │  negocio)   │  │             │  │             │     IA real     │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘                  │
└─────────┼────────────────┼────────────────┼─────────────────────────┘
          │                │                │
          ▼                ▼                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        N8N (Orquestación determinista)              │
│  Ingestión docs · Calendario fiscal/laboral · Notificaciones       │
│  Webhooks AEAT/SS/Registros · Sync ERP · Reportes programados       │
└─────────────────────────────────────────────────────────────────────┘
```

## Diferenciadores vs LEXIA
| Aspecto | LEXIA | GESTIA |
|---------|-------|--------|
| Dominio | Legal (bufetes) | Gestoría/Asesoría (4 áreas) |
| Tenant | Bufete (1 abogado principal) | Asesoría (múltiples empresas cliente) |
| Entidad central | Expediente | Empresa + Obligaciones periódicas |
| Calendarización | Plazos judiciales | **Calendario fiscal/laboral obligatorio** (AEAT, SS) |
| Integración clave | WhatsApp/Email/Calendario | **AEAT, SS, Registros, ERP, Facturae, SII** |
| Documentos | Contratos, escritos | **Libros oficiales, modelos fiscales, nóminas, TC** |

## Multi-tenant real
- Una instancia = una asesoría/gestoría
- Cada tenant = una empresa cliente de la asesoría
- Aislamiento datos: Row-Level Security (PostgreSQL) + tenant_id en todo
- Facturación por uso (metering): empresas activas, documentos, declaraciones, nóminas

## Compliance
- **RGPD + AI Act Art.50** (base, como LEXIA)
- **ENS** (Esquema Nacional Seguridad) — obligatorio para proveedores AA.PP.
- **ISO 27001** — diferencial competitivo para gestorías
- **AEAT/SS**: cumplimiento normativo estricto (modelos, plazos, formatos)

## Ahorro tokens (estrategia híbrida)
| Capa | Qué hace | Ahorro estimado |
|------|----------|-----------------|
| **n8n** (determinista) | Ingesta OCR, calendario, notificaciones, webhooks, sync ERP, reportes | 70-85% tokens totales |
| **Caché semántico** (Redis + VectorDB) | Deduplicación prompts, respuestas frecuentes | 30-50% en LLM calls |
| **Routing modelos** | Kev/DeepSeek/Gemini-free para clasificación, resumen; premium solo para redacción/razonamiento | 60-80% coste LLM |
| **Resumidores locales** (Ollama) | Pre-procesado docs largos antes de cloud | 40-60% tokens entrada |
| **Prompts optimizados + plantillas** | Few-shot fijos, system prompts compartidos | 20-30% tokens/petición |
| **Metering por tenant/evento** | Visibilidad coste real, alertas, budgets | Control financiero |
