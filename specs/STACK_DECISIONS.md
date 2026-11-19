# Decisiones de Stack — GESTIA (Consensuadas)

## Decisiones Tomadas

| Decisión | Opción Elegida | Alternativas Descartadas | Justificación |
|----------|----------------|--------------------------|---------------|
| **API Framework** | FastAPI + Pydantic v2 | Flask, Django REST, NestJS | Tipado nativo, OpenAPI auto, async, rendimiento, ecosistema |
| **Base de Datos** | PostgreSQL 16 + RLS | MySQL, SQLite, MongoDB | Multi-tenant nativo (RLS), JSONB, estándar enterprise, extensiones |
| **ORM** | SQLAlchemy 2.0 (async) | Tortoise, Prisma, Django ORM | Typed, async, Alembic maduro, control fino |
| **Cache + Vector** | Redis 7 + Qdrant | Valkey + Chroma, Upstash + Pinecone | Open source, self-hosted, rendimiento, filtrado metadata |
| **Workflows/Automatización** | n8n (self-hosted) | Temporal, Prefect, Airflow, custom | Visual, 400+ nodos, webhooks nativos, código cuando hace falta, comunidad |
| **LLM Local** | Ollama (llama3.3, qwen2.5:7b, kev-4b) | LM Studio, Jan, vLLM | CLI simple, modelos GGUF, API compatible OpenAI, Kev integrado |
| **LLM Cloud (gratis/barato)** | OpenRouter | Together, Fireworks, Groq directos | Un endpoint, 100+ modelos, routing automático, gratuito generoso |
| **LLM Premium** | Anthropic/Google/OpenAI selectivos | Solo uno, solo open source | Calidad máxima solo donde ROI justifica (redacción, razonamiento complejo) |
| **Observabilidad** | OpenTelemetry → Prometheus + Grafana + Loki + Tempo | Datadog, New Relic, Elastic | Estándar CNCF, vendor-neutral, auto-instrumentación, coste 0 |
| **CI/CD** | GitHub Actions + `act` local | GitLab CI, Jenkins, CircleCI | Estándar de facto, matrix, caching, reusable workflows, gratis para open source |
| **Infra Local** | Docker Compose + `just` | Podman, DevContainer, Vagrant | Reproducible, simple, `docker compose up`, todos los servicios |
| **Infra Cloud (futuro)** | Helm + ArgoCD | Terraform + Flux, Pulumi + Crossplane | GitOps nativo K8s, progresivo desde Compose |
| **Secrets** | `.env` local / 1Password CLI / AWS Secrets Manager | HashiCorp Vault, SOPS, Doppler | Rotación, auditoría, escalable |
| **Testing** | pytest + testcontainers + playwright + schemathesis | unittest, jest, cypress solo | Pirámide completa, determinista, contract testing real |
| **Lint/Type** | `ruff` + `mypy --strict` | flake8 + black + pylint, eslint | Velocidad, unificación, strict mode real |
| **Security** | `bandit` + `pip-audit` + `trivy` + `checkov` | Snyk, SonarQube, Semgrep solo | Gratis, integra CI, coverage amplio |
| **Docs** | MkDocs + Material + Mermaid + adr-tools | Sphinx, Docusaurus, GitBook | Markdown, versionado en repo, diagramas renderizados |
| **Diagramas** | Mermaid (en repo) + diagram-design skill | PlantUML, draw.io, Excalidraw | Texto plano, diffable, render GitHub/GitLab/MkDocs |

## Decisiones Pendientes (Confirmar en Kickoff)

| Decisión | Opciones | Recomendación | Impacto |
|----------|----------|---------------|---------|
| **Gestor de paquetes Python** | `uv` (recomendado) vs `pip`/`poetry`/`pdm` | `uv` — velocidad, lockfile, workspace, Python management | Alto (velocidad DX) |
| **Monorepo vs Multi-repo** | Monorepo (apps/, packages/, connectors/) vs Multi-repo | Monorepo — shared types, atomic commits, DX simple | Medio |
| **Auth/Z** | JWT + RBAC (custom) vs Keycloak vs Auth0 vs Clerk | JWT + RBAC simple v1 → Keycloak v2 | Medio |
| **API Gateway** | Traefik (labels Docker) vs Kong vs NGINX | Traefik — auto-discovery, Let's Encrypt, middleware | Bajo (local) / Alto (cloud) |
| **Email Transaccional** | Resend vs SendGrid vs Postmark vs SMTP propio | Resend — DX, precio, deliverability | Bajo |
| **S3/Object Storage** | MinIO (local) → AWS S3 / Cloudflare R2 (cloud) | MinIO compatible S3 | Bajo |
| **Feature Flags** | LaunchDarkly vs Unleash vs custom JSON | Custom JSON v1 → Unleash v2 | Bajo |

## Principios Arquitectónicos (No Negociables)

1. **Multi-tenant real desde día 1** — RLS en PostgreSQL, `tenant_id` en TODO, tests de aislamiento
2. **Local-first** — Todo corre en `docker compose up` sin credenciales cloud obligatorias
3. **Observabilidad por defecto** — OpenTelemetry auto-instrumentación, nada en prod sin logs/métricas/trazas
4. **Security by default** — Non-root containers, read-only fs, secrets rotados, 0 CRIT/HIGH en CI
5. **Coste LLM visible y controlado** — Metering middleware obligatorio, budgets por tenant, alertas
6. **Tests deterministas** — `testcontainers` para integración, mocks totales para unit, 0 red en CI
7. **Documentación viva** — ADRs para decisiones, OpenAPI desde código, diagramas Mermaid en repo
8. **Conventional Commits + Semantic Release** — Versionado automático, changelog generado
9. **n8n para lo determinista, LLM para lo semántico** — Separación clara, 70-85% tokens ahorrados
10. **Compliance desde diseño** — RGPD, AI Act Art.50, ENS, ISO 27001 mapeados a controles técnicos
