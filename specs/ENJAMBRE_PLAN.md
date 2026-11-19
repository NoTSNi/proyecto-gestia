# Plan del Enjambre de Agentes — GESTIA

## Objetivo
Un enjambre de **bots especializados** que construyan, configuren, integren, monitoricen y mantengan GESTIA end-to-end, ahorrando tokens LLM y garantizando seguridad, estabilidad, observabilidad y compliance.

---

## Arquitectura del Enjambre

```
+---------------------------------------------------------------------------------+
|                    ORQUESTADOR DEL ENJAMBRE (Swarm Orchestrator)                |
|  • Recibe objetivos de alto nivel                                               |
|  • Descompone en tareas atómicas                                                |
|  • Asigna a bots especializados                                                 |
|  • Verifica gates de calidad (tests, lint, security, coste)                    |
|  • Consolida resultados y reporta                                               |
+-----------------------------------+---------------------------------------------+
                                    |
         +--------------------------+--------------------------+
         |                          |                          |
         v                          v                          v
+----------------+          +----------------+          +----------------+
|  INFRA BOTS    |          |  DOMAIN BOTS   |          |  OPS BOTS      |
|  (configuran,  |          |  (lógica de    |          |  (observan,    |
|   despliegan)  |          |   negocio)     |          |   mantienen)   |
+-------+--------+          +-------+--------+          +-------+--------+
        |                          |                          |
  +-----+-----+              +-----+-----+              +-----+-----+
  |           |              |           |              |           |
  v           v              v           v              v           v
```

---

## Bots del Enjambre (7 + 1 Orquestador)

### 1. 🏗️ INFRA-BOT: Configurador de Infraestructura
**Responsabilidad**: Provisiona y configura todo el stack base.
- **Entregables**:
  - `docker-compose.yml` (PostgreSQL, Redis, n8n, MinIO, Ollama, GESTIA API, Prometheus, Grafana, Loki)
  - `.env.example` + `.env.local` (secrets management)
  - `Dockerfile` multi-stage (build → runtime, non-root, distroless)
  - `k8s/` manifests (Helm charts) para futuro despliegue cloud
  - `Makefile` / `justfile` con targets: `dev`, `test`, `build`, `deploy`, `logs`, `shell`
  - GitHub Actions / GitLab CI pipeline (lint → test → build → security-scan → deploy-staging)
- **Herramientas**: `terminal`, `write_file`, `patch`, `web_search` (best practices)
- **Gates**: `docker compose config` válido, `hadolint` clean, `trivy` sin CRITICAL/HIGH

### 2. 🔗 INFRA-BOT: Integrador de Conectores Externos
**Responsabilidad**: Implementa y mantiene todos los conectores a apps externas.
- **Conectores prioritarios** (fase 1):
  - **AEAT** — Webhooks SII, consulta censal, presentación modelos (130, 200, 303, 390, etc.)
  - **Seguridad Social** — Sistema RED, SILTRA, certificados, partes de baja/alta
  - **Registros Mercantiles** — Depósito cuentas, legalización libros, nombramientos
  - **Facturae / FACe** — Envío facturas electrónicas AA.PP.
  - **Bancos (EBICS/PSD2)** — Conciliación bancaria, norma 43/19
- **Conectores secundarios** (fase 2):
  - WhatsApp Business (Meta Cloud API / Twilio)
  - Google Calendar / Gmail / Drive (OAuth2)
  - Email SMTP/IMAP (entrada/salida con DKIM/SPF/DMARC)
  - CRM (HubSpot, Pipedrive, o propio)
  - Firma digital (Autofirma, Signaturit, DocuSign)
  - ERPs (Holded, Contasol, Sage, A3, Odoo)
- **Patrón**: Cada conector = paquete Python tipado (`gestia-connectors-<nombre>`) con:
  - Cliente tipado (Pydantic models request/response)
  - Rate limiting + retry con backoff + circuit breaker
  - Tests con `respx` / `pytest-httpx` (mockeo total, sin red real en CI)
  - Documentación OpenAPI generada + ejemplos reales
- **Herramientas**: `terminal`, `write_file`, `patch`, `skill_view` (api-design, security-review)

### 3. 🧠 DOMAIN-BOT: Arquitecto de Agentes de Negocio (4 áreas)
**Responsabilidad**: Diseña e implementa los agentes especialistas (estilo LEXIA).
- **Agentes a crear** (1 por área + supervisor):
  - `MercantilAgent` — Constitución, libros, juntas, modificaciones, disoluciones, M&A
  - `AdministrativoAgent` — Licencias, subvenciones, recursos, contratos públicos
  - `ContableAgent` — Contabilidad, impuestos, SII, facturae, cuentas anuales, conciliación
  - `LaboralAgent` — Nóminas, contratos, SS, prevención, ERTE/ERE, inspecciones, convenios
  - `SupervisorGestia` — Router multi-área, detecta dominio, delega, consolida
- **Base compartida** (reutiliza patrón LEXIA):
  - `BaseAgent` + `IdentificacionGestia` (RGPD + AI Act Art.50 + ENS)
  - `SpecialistBase` con `procesar()`, `debe_transferir()`, `generar_briefing()`
  - `Orchestrator` central (enrutamiento por `tipo_evento`)
  - RAG por área (vector DB con normativa, jurisprudencia, formularios, plantillas)
- **Herramientas**: `skill_view` (tdd-workflow, verification-loop, coding-standards), `write_file`, `patch`

### 4. 💰 DOMAIN-BOT: Optimizador de Costes LLM (Token Saver)
**Responsabilidad**: Implementa la estrategia híbrida de ahorro de tokens.
- **Componentes**:
  - **SemanticCache** (Redis + VectorDB: Qdrant/Chroma) — Embedding de prompts, búsqueda k-NN, TTL configurable, invalidación por versión de prompt
  - **ModelRouter** — Reglas de enrutamiento:
    - Clasificación / resumen / extracción → Kev-4B / DeepSeek-V4-Flash / Gemini-3.6-Flash (gratis/barato)
    - Redacción documentos / razonamiento legal / análisis riesgo → Gemini-2.5-Pro / GPT-4o / Claude (premium)
    - Casos borde OCR / visión → GPT-4o-mini / Gemini-Flash-Vision
  - **LocalSummarizer** (Ollama: `llama3.3`, `qwen2.5:7b`) — Pre-procesa docs >4k tokens antes de cloud
  - **PromptTemplates** — Sistema de plantillas versionadas (Jinja2) con few-shot fijos, variables tipadas
  - **MeteringMiddleware** — Interceptor FastAPI que registra: tenant, evento, modelo, tokens_in/out, coste estimado, latencia
  - **BudgetAlerts** — Límites por tenant/mes, alertas Slack/Email/webhook al 80%/95/100%
- **Métricas objetivo**: 70-85% reducción tokens vs naive; <€0.01/empresa/mes en LLM para operaciones rutinarias
- **Herramientas**: `skill_view` (cost-aware-llm-pipeline, redis-patterns), `write_file`, `patch`

### 5. 📊 OPS-BOT: Observabilidad y Fiabilidad
**Responsabilidad**: Logs, métricas, trazas, alertas, dashboards, SLOs.
- **Stack**: OpenTelemetry → Prometheus + Grafana + Loki + Tempo (o Jaeger)
- **Instrumentación**:
  - **Logs estructurados** (JSON, `structlog`): request_id, tenant_id, user_id, agente, acción, duración, resultado, error
  - **Métricas RED** (Rate, Errors, Duration) por endpoint, por agente, por modelo LLM
  - **Trazas distribuidas** (W3C trace-context) cross-service: API → Agentes → n8n → Conectores → DB
  - **Business metrics**: empresas activas, declaraciones presentadas, nóminas generadas, documentos procesados, coste LLM/tenant
- **Dashboards Grafana** (provisionados as code):
  - System: CPU, RAM, DB connections, Redis, n8n queue
  - Application: RPS, p50/p95/p99 latency, error rate by type
  - LLM: tokens/día, coste/día, cache hit rate, model distribution
  - Business: MRR, churn, usage por módulo
- **Alertas** (PrometheusRule + Alertmanager → Slack/Email/PagerDuty):
  - Latencia p99 > 2s, error rate > 1%, cola n8n > 100, DB connections > 80%
  - Coste LLM tenant > budget 80%, cache hit rate < 30%
  - Fallos webhooks AEAT/SS, certificados caducando <30 días
- **SLOs**: Disponibilidad 99.9%, latencia p99 < 2s, error rate < 0.1%, frescura datos < 5min
- **Herramientas**: `skill_view` (dashboard-builder, verification-loop), `write_file`, `patch`

### 6. ✅ OPS-BOT: Testing & CI/CD Gatekeeper
**Responsabilidad**: Garantiza calidad en cada commit/PR.
- **Pirámide de tests**:
  - **Unit** (80%): Agentes, conectores, utils, routers — `pytest`, `pytest-asyncio`, `pytest-mock`, coverage >90%
  - **Integration** (15%): API endpoints, DB transactions, n8n workflows, webhooks — `testcontainers` (PostgreSQL, Redis, MinIO, n8n)
  - **Contract** (5%): OpenAPI schema validation, AEAT/SS payloads — `schemathesis`, `pact-python`
  - **E2E** (smoke): Flujos críticos (alta empresa → obligaciones → presentación modelo) — `playwright` headless
- **Quality Gates** (GitHub Actions):
  - `ruff` + `mypy --strict` + `bandit` + `pip-audit` + `trivy fs`
  - `pytest --cov --cov-fail-under=85`
  - `hadolint` Dockerfile, `checkov` k8s manifests
  - `semantic-release` / `conventional-changelog` para versionado
- **Chaos/Resilience** (mensual): `chaos-mesh` o `litmus` — kill pods, latency injection, DB failover
- **Herramientas**: `skill_view` (e2e-testing, tdd-workflow, verification-loop), `terminal`, `write_file`

### 7. 📚 OPS-BOT: Documentación Viva y ADRs
**Responsabilidad**: Mantiene docs sincronizadas con código.
- **ADRs** (Architecture Decision Records) — `adr-tools`, uno por decisión técnica relevante
- **OpenAPI/Swagger** — Generado desde código FastAPI (`fastapi.openapi`), publicado en `/docs`
- **Runbooks** — Procedimientos operativos: deploy, rollback, cert rotation, incident response, backup/restore
- **API Reference** — `redocly` + ejemplos por conector
- **Diagramas** — Mermaid en repo (arquitectura, flujos datos, secuencias), renderizados en CI
- **Changelog** — Autogenerado desde conventional commits
- **Herramientas**: `skill_view` (docs-governance, diagram-design), `write_file`, `patch`

---

### 8. 🎭 ORQUESTADOR: Swarm Orchestrator (Meta-bot)
**Responsabilidad**: Coordina a los 7 bots, gestiona dependencias, verifica gates globales.
- **Flujo**:
  1. Recibe objetivo (ej: "implementar conector AEAT SII")
  2. Descompone en tareas atómicas con dependencias (DAG)
  3. Asigna a bots especializados en paralelo donde sea posible
  4. Ejecuta quality gates tras cada bot
  5. Consolida PR único o stacked PRs
  6. Reporta estado: qué pasó, qué falló, qué queda, métricas
- **Implementación**: Puede ser un script Python que usa `subprocess` + `asyncio` para lanzar bots como subprocesos Hermes, o un workflow n8n que orquesta CLI calls
- **Estado persistente**: `swarm_state.json` (tasks, assignments, results, gates)

---

## Secuencia de Ejecución (Fases)

### FASE 0 — Fundación (Semana 1)
| Bot | Tarea | Gate |
|-----|-------|------|
| Infra-Config | docker-compose.yml base (PG, Redis, n8n, MinIO, Ollama, API, Obs stack) | docker compose up -d healthy |
| Infra-Config | .env.example, Dockerfile, Makefile, CI pipeline | CI verde en push |
| Infra-Config | PostgreSQL schema multi-tenant (RLS), migraciones Alembic | alembic upgrade head ok |
| Domain-Agentes | BaseAgent, IdentificacionGestia, SpecialistBase, Orchestrator | Tests unit pasan |
| Domain-Agentes | SupervisorGestia (router 4 áreas + general) | Tests router >95% accuracy |
| TokenSaver | SemanticCache (Redis+Qdrant), ModelRouter skeleton | Cache hit/miss logs |
| Observabilidad | OpenTelemetry instrumentación base, Prometheus+Grafana+Loki up | Dashboards cargan |
| Testing | CI pipeline con quality gates | PR de prueba pasa gates |
| Docs | Estructura docs/, adr init, OpenAPI export | mkdocs serve ok |

### FASE 1 — Conectores Críticos (Semana 2-3)
| Bot | Conector | Gate |
|-----|----------|------|
| Integrador | AEAT SII (envío facturas, consulta estado) | Test mock 100% cobertura |
| Integrador | Seguridad Social RED/SILTRA | Test mock 100% cobertura |
| Integrador | Registros Mercantiles (depósito cuentas) | Test mock 100% cobertura |
| Integrador | Facturae/FACe | Test mock 100% cobertura |
| TokenSaver | LocalSummarizer (Ollama) + PromptTemplates v1 | Benchmark tokens ahorrados |
| Observabilidad | Business metrics + alertas base | Alertas disparan en staging |

### FASE 2 — Agentes de Negocio + RAG (Semana 3-4)
| Bot | Agente | Gate |
|-----|--------|------|
| Domain-Agentes | MercantilAgent + RAG (ley sociedades, formularios) | Tests casos reales >90% |
| Domain-Agentes | ContableAgent + RAG (PGC, modelos IVA/IS/IRPF) | Tests casos reales >90% |
| Domain-Agentes | LaboralAgent + RAG (ET, convenios, SS) | Tests casos reales >90% |
| Domain-Agentes | AdministrativoAgent + RAG (LPAC, LCSP, subvenciones) | Tests casos reales >90% |
| TokenSaver | ModelRouter reglas completas + MeteringMiddleware | Dashboard coste/tenant |
| Integrador | WhatsApp Business + Email SMTP/IMAP | E2E flujo notificación |
| Observabilidad | Traces cross-service (API→Agentes→n8n→Conectores) | Traza completa visible |

### FASE 3 — n8n Workflows + Automatizaciones (Semana 4-5)
| Bot | Workflow n8n | Gate |
|-----|--------------|------|
| Integrador | Ingesta docs: upload→OCR→split→classify→embed→vectorDB | 100 docs test <5min |
| Integrador | Calendario fiscal/laboral: cálculo plazos, alertas, presentación | 100 empresas test |
| Integrador | Notificaciones multicanal (Email, Slack, WhatsApp, Portal) | Delivery >99.5% |
| Integrador | Webhooks AEAT/SS/Registros → routing interno | 0 pérdida eventos |
| Integrador | Sync ERP/Contable → BD + conciliación bancaria | Conciliación >95% auto |
| Integrador | Reportes programados (IVA trimestral, IRPF, nóminas) | Generación <30s |
| TokenSaver | Benchmark completo: tokens ahorrados vs baseline | Target >70% |

### FASE 4 — Hardening + Compliance + MVP (Semana 5-6)
| Bot | Tarea | Gate |
|-----|-------|------|
| Observabilidad | Chaos testing mensual, runbooks incidentes | MTTR <30min |
| Testing | E2E flujos críticos 100% (alta empresa → presentación modelo) | 0 flaky |
| Docs | ADRs completos, runbooks, API ref, diagramas | mkdocs build ok |
| Infra-Config | Hardening: non-root, read-only fs, secrets rotation, network policies | trivy 0 CRIT/HIGH |
| Compliance | ENS auto-evaluación, ISO 27001 controles mapeados | Checklist >90% |
| Todos | MVP DEMO: 1 tenant demo, 4 empresas, 1 mes operaciones simuladas | Demo stakeholder ok |

---

## Gates de Calidad Globales (por fase)

| Gate | Herramienta | Threshold |
|------|-------------|-----------|
| Lint/Type | ruff + mypy --strict | 0 errors |
| Security | bandit + pip-audit + trivy fs | 0 CRITICAL/HIGH |
| Tests Unit | pytest --cov | Coverage >90% |
| Tests Int | testcontainers | 100% pass |
| Contract | schemathesis | 0 violations |
| E2E | playwright | 0 flaky, 100% critical paths |
| Docker | hadolint + checkov | 0 warnings |
| Coste LLM | MeteringMiddleware + dashboard | <€0.01/empresa/mes rutinario |
| Cache Hit | SemanticCache metrics | >50% (fase 2), >70% (fase 3) |
| Latencia p99 | Prometheus/Grafana | <2s |
| Disponibilidad | SLO tracking | >99.9% |

---

## Stack Tecnológico Definitivo

| Capa | Tecnología | Justificación |
|------|------------|---------------|
| API | FastAPI + Pydantic v2 | Tipado, OpenAPI nativo, async, rendimiento |
| DB | PostgreSQL 16 + RLS | Multi-tenant nativo, JSONB, rendimiento, estándar |
| ORM | SQLAlchemy 2.0 (async) | Typed, async, migraciones Alembic |
| Cache/Vector | Redis 7 + Qdrant | Semantic cache, embeddings, rate limiting |
| Queue/Workflows | n8n (self-hosted) | Visual, 400+ nodos, webhooks, código cuando hace falta |
| LLM Local | Ollama (llama3.3, qwen2.5, kev-4b) | Privacidad, coste 0, control total |
| LLM Cloud | OpenRouter (DeepSeek, Gemini, Qwen, GLM) | Modelos gratis/baratos, routing único |
| LLM Premium | Anthropic/Google/OpenAI (solo redacción/razonamiento) | Calidad máxima donde importa |
| Observabilidad | OpenTelemetry → Prometheus + Grafana + Loki + Tempo | Estándar CNCF, auto-instrumentación |
| CI/CD | GitHub Actions + act local | Estándar, matrix, caching, reusable workflows |
| Infra Local | Docker Compose + just | Reproducible, simple, docker compose up |
| Infra Cloud | Helm + ArgoCD (futuro) | GitOps, progresivo |
| Secrets | .env local / 1Password CLI / AWS Secrets Manager (cloud) | Rotación, auditoría |
| Testing | pytest + testcontainers + playwright + schemathesis | Pirámide completa, determinista |

---

## Riesgos y Mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| Cambios API AEAT/SS sin aviso | Alta | Alto | Conectores versionados, tests con snapshots reales, alertas 404/500 |
| Coste LLM se descontrola | Media | Alto | Hard limits por tenant, alertas 80/95/100%, modelos gratis por defecto |
| n8n se vuelve cuello de botella | Media | Media | Workers horizontales, cola Redis, métricas queue depth |
| Fuga datos entre tenants | Baja | Crítico | RLS PostgreSQL + tests de aislamiento automatizados |
| Certificados digitales caducan | Media | Alto | Monitor expiración 90/60/30/7/1 día, renovación auto donde posible |
| Dependencia n8n (single point) | Baja | Alto | API GESTIA funciona sin n8n (modo degradado), runbooks manuales |
| Cambios normativa (leyes, modelos) | Alta | Medio | RAG actualizable, suscripción BOE/BOE-A, alerts RSS |
| Equipo solo 1 persona | Cierta | Alto | Bots automatizan 80% tareas repetitivas, docs para bus factor |

---

## Métricas de Éxito (KPIs)

| KPI | Target Fase 4 (MVP) | Target Fase 6 (Producción) |
|-----|---------------------|----------------------------|
| Tokens LLM/empresa/mes | <50k | <20k |
| Coste LLM/empresa/mes | <€0.50 | <€0.10 |
| Cache hit rate | >50% | >80% |
| Latencia p99 API | <2s | <500ms |
| Disponibilidad | 99.5% | 99.9% |
| Cobertura tests | >85% | >95% |
| Tiempo deploy | <10min | <5min |
| MTTR incidentes | <1h | <15min |
| Empresas tenant demo | 4 | 100+ |
| Declaraciones auto/mes | 50 | 5000+ |

---

## Próximos Pasos Inmediatos

1. **Aprobar este plan** → Confirmar fases, prioridades, stack
2. **Infra-Bot Configurador** → Ejecutar Fase 0 completa (base reproducibile)
3. **Domain-Bot Agentes** → Implementar BaseAgent + SupervisorGestia + 4 especialistas skeleton
4. **TokenSaver** → SemanticCache + ModelRouter v1 con Kev-4B/DeepSeek-free
5. **Integrador** → Conector AEAT SII (el más crítico y complejo)
6. **Iterar** → Cada fase valida con gates antes de pasar a la siguiente

---

## Notas para el Orquestador del Enjambre

- Cada bot = subproceso independiente con contexto acotado (archivos specs/, tests/, código propio)
- Comunicación via archivos en swarm_workspace/ + swarm_state.json
- Quality gates **bloqueantes**: si un bot falla gate, el orquestador para y reporta
- Paralelismo: bots sin dependencias corren simultáneo (ej: Observabilidad + Testing + Docs en Fase 0)
- Checkpoints: commit al repo tras cada fase completada con tags fase-0, fase-1, etc.