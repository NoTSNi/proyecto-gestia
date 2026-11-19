# GESTIA — Asistente Multi-Agente para Asesoría/Gestoría

> **GESTIA** = **Gest**oría + **IA**. Sistema multi-agente para gestionar múltiples empresas (multi-tenant) en 4 áreas: **Mercantil, Administrativo, Contable, Personal**.

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16+-blue.svg)](https://postgresql.org)
[![n8n](https://img.shields.io/badge/n8n-Workflow-orange.svg)](https://n8n.io)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://docker.com)

---

## 🎯 Visión General

GESTIA es un **asistente multi-agente** diseñado para asesorías/gestorías que gestionan **múltiples empresas clientes**. Combina:

| Componente | Tecnología | Propósito |
|------------|------------|-----------|
| **Agentes Especialistas** | Python + LangGraph/Custom | Razonamiento experto por dominio (Mercantil, Administrativo, Contable, Personal) |
| **Supervisor/Router** | Custom | Clasificación de intenciones, routing, consolidación |
| **Automatización Determinista** | **n8n** | OCR, Calendar sync, Notificaciones, Webhooks AEAT/SS, ETL contable |
| **Document Vault** | MinIO + pgvector + Docling | Subida, OCR, clasificación, RAG, versionado |
| **API REST** | FastAPI + SQLAlchemy 2.0 | Multi-tenant con RLS, JWT, OpenAPI |
| **Frontend** | React 18 + Vite + Tailwind | Dashboard asesor + Portal cliente |

---

## 🏗️ Arquitectura

```
┌─────────────────────────────────────────────────────────────────┐
│                        GESTIA CORE                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │  Supervisor │  │   Router    │  │   Memory    │              │
│  │  (Orquest.) │  │  (Intents)  │  │  (Multi-tenant)          │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘              │
└─────────┼────────────────┼────────────────┼─────────────────────┘
          │                │                │
    ┌─────▼─────┐    ┌─────▼─────┐    ┌─────▼─────┐
    │ MERCANTIL │    │  ADMIN    │    │ CONTABLE  │    ┌────────┐
    │ Specialist│    │ Specialist│    │ Specialist│    │PERSONAL│
    └───────────┘    └───────────┘    └───────────┘    │Specialist│
                                                      └────────┘
    ┌─────────────────────────────────────────────────────────┐
    │                    SHARED LAYER                          │
    │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐    │
    │  │ Tenant   │ │ Document │ │ Calendar │ │ Comms    │    │
    │  │ Registry │ │ Vault    │ │Deadlines │ │ Portal   │    │
    │  └──────────┘ └──────────┘ └──────────┘ └──────────┘    │
    └─────────────────────────────────────────────────────────┘
                              │
                    ┌─────────▼─────────┐
                    │   API Gateway     │
                    │  (FastAPI/REST)   │
                    └────────┬──────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
        ┌──────────┐  ┌──────────┐  ┌──────────┐
        │  Web UI  │  │  Portal  │  │  Mobile  │
        │ (React)  │  │ Cliente  │  │  (PWA)   │
        └──────────┘  └──────────┘  └──────────┘
```

---

## 🤖 Agentes Especialistas

| Agente | Dominio | Capabilities Principales |
|--------|---------|--------------------------|
| **Mercantil** | Derecho Mercantil | Constitución SL, modificación estatutos, juntas, libros oficiales, disolución, depósito cuentas |
| **Administrativo** | Derecho Administrativo | Licencias, subvenciones, recursos (reposición/alzada/TEAR), contratos públicos, sanciones |
| **Contable** | Contabilidad/Fiscalidad | Modelos 303, 390, 200, 202, 111, 190, 347, 349, cierres, conciliación bancaria |
| **Personal** | Laboral/Nóminas | Nóminas, contratos, TC1/TC2, altas/bajas SS, absentismo, PRL, IRPF retenciones |

**Supervisor**: Clasifica intención → Ruta a especialista(s) → Consolida respuesta

---

## ⚙️ n8n — Automatización Determinista (Ahorro masivo de tokens)

| Workflow | Trigger | Qué hace | Tokens ahorrados |
|----------|---------|----------|------------------|
| `gestia-ingest-document` | Webhook | Upload → OCR (Docling) → Split → Clasificar → Embed → Vector DB → Callback | ~500-2000/doc |
| `gestia-calendar-sync` | Cron (lunes 6AM) | AEAT/SS/BOE → BD → Alertas 15d/7d/1d/día | ~200-500/empresa/mes |
| `gestia-notify-multichannel` | Webhook | Email/Slack/WhatsApp/Portal → Template → Send | ~100-300/notif |
| `gestia-aeat-webhook` | Webhook (AEAT) | Validar → Actualizar modelo → Notificar | ~50-100/evento |
| `gestia-contable-sync` | Cron (3AM) | ERP → Facturas nuevas → Conciliación → Callback | ~1000-5000/sync |

**Regla de oro**: Todo lo determinista → n8n. Solo razonamiento experto → Agentes LLM.

---

## 📥 Canales de Entrada Seguros (Clientes → GESTIA)

| Canal | Seguridad | Uso recomendado |
|-------|-----------|-----------------|
| **Portal Web** | HTTPS, JWT httpOnly, MFA (TOTP/Passkeys), cuota/tenant, antivirus, cuarentena | **Base** - Facturas, contratos, escritos |
| **Email** | Dominio propio, DKIM/DMARC/SPF, OAuth2 IMAP, parsing seguro | **Base** - Facturas por email, comunicaciones |
| **WhatsApp Business** | Meta Verified, E2E, plantillas HSM, opt-in LOPD | **Opcional v1.1** - Fotos facturas, notificaciones push |
| **API/SFTP** | mTLS, API key rotativa, rate-limit, validación XSD Facturae/SII | **Clientes grandes/ERP** - Integración automática |
| **PWA Móvil** | Camera API, offline-first, WebAuthn, background sync | **Opcional v1.2** - Captura facturas in situ |

**Unificación**: Todos los canales → `DocumentIngestionService` → Cuarentena + Hash SHA-256 + Audit Log → n8n → Callback → Vault indexado.

---

## 🚀 Quick Start

### Prerrequisitos
- Docker + Docker Compose
- Git
- (Opcional) GPU para Docling CUDA

### 1. Clonar y configurar
```bash
cd PROYECTO_GESTIA
cp .env.example .env
# Editar .env con valores reales (JWT_SECRET, N8N_ENCRYPTION_KEY, etc.)
```

### 2. Levantar stack
```bash
docker-compose up -d
# Servicios: postgres, redis, minio, n8n, gestia-api, gestia-web
```

### 3. Inicializar BD
```bash
docker-compose exec gestia-api python scripts/setup_db.py --seed
```

### 4. Acceder
- **API Docs**: http://localhost:8000/docs
- **n8n**: http://localhost:5678 (admin / password del .env)
- **MinIO Console**: http://localhost:9001
- **Web UI**: http://localhost:5173

### 5. Credenciales demo (tras --seed)
| Usuario | Email | Password | Rol |
|---------|-------|----------|-----|
| Admin | admin@gestia.app | admin123 | superadmin |
| Asesor | asesor@gestia.app | asesor123 | asesor_contable |
| Cliente | cliente@demo.com | cliente123 | cliente_titular |

---

## 📁 Estructura del Proyecto

```
PROYECTO_GESTIA/
├── .github/workflows/          # CI/CD
├── agents/                     # Agentes multi-agente
│   ├── base_agent.py          # Clase base
│   ├── supervisor.py          # Orquestador + Router
│   ├── specialist_base.py     # Base especialistas
│   └── specialists/           # 4 especialistas
│       ├── mercantil.py
│       ├── administrativo.py
│       ├── contable.py
│       └── personal.py
├── api/                        # FastAPI REST API
│   ├── main.py                # App factory + middlewares
│   └── routes/                # Endpoints por dominio
│       ├── auth.py
│       ├── empresas.py
│       ├── documentos.py
│       ├── calendario.py
│       ├── fiscal.py
│       ├── personal.py
│       ├── mercantil.py
│       ├── administrativo.py
│       ├── notificaciones.py
│       └── internal.py        # Callbacks n8n
├── gestia_core/               # Paquete compartido
│   ├── config/                # Settings (Pydantic Settings)
│   ├── database/              # SQLAlchemy 2.0 + RLS
│   ├── models/                # Modelos multi-tenant
│   ├── schemas/               # Pydantic API schemas
│   ├── security/              # JWT, RBAC, RLS context
│   └── utils/                 # Hash, NIF, dates, pagination
├── shared/                    # Servicios compartidos
│   ├── document_vault/        # OCR, RAG, MinIO
│   ├── calendar_deadlines/    # Calendario fiscal/laboral/mercantil
│   ├── comms_portal/          # Email, WhatsApp, notificaciones
│   └── tenant_registry/       # Multi-tenant onboarding
├── n8n/workflows/             # Workflows n8n (JSON export)
├── scripts/                   # Setup, seed, demo
├── tests/                     # Unit, integration, e2e
├── alembic/                   # Migraciones BD
├── web-ui/                    # React + Vite + Tailwind
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
├── .env.example
└── README.md
```

---

## 🔐 Seguridad (Multi-tenant + RLS)

- **Row Level Security (RLS)** en **todas** las tablas via `tenant_id`
- **JWT** en httpOnly cookies (SameSite=Strict) + refresh tokens rotativos
- **RBAC**: `superadmin`, `admin_asesoria`, `asesor_*`, `cliente_titular`, `cliente_empleado`
- **MFA**: TOTP + WebAuthn (Passkeys)
- **Cifrado**: AES-256 en reposo (MinIO SSE-KMS + pgcrypto), TLS 1.3 en tránsito
- **Audit Log**: Append-only, inmutable (quién, qué, cuándo, IP, hash)
- **Validación**: Pydantic schemas en todo input, magic bytes en uploads
- **Rate limiting**: Por IP (anon) y por usuario (auth)

---

## 🧪 Testing

```bash
# Unit tests
docker-compose exec gestia-api pytest tests/unit -v --cov

# Integration tests (Testcontainers PostgreSQL)
docker-compose exec gestia-api pytest tests/integration -v

# E2E tests (Playwright)
cd web-ui && npm run test:e2e

# Contract tests (Schemathesis)
docker-compose exec gestia-api pytest tests/contract -v
```

---

## 📦 Despliegue Producción

```bash
# Build imágenes producción
docker-compose -f docker-compose.yml -f docker-compose.prod.yml build

# Deploy con Coolify / Railway / VPS + Docker Swarm
# Variables críticas en .env.production:
# - JWT_SECRET_KEY (64+ chars)
# - N8N_ENCRYPTION_KEY (32 bytes base64)
# - POSTGRES_PASSWORD fuerte
# - MINIO_ROOT_PASSWORD fuerte
# - Certificados TLS (Let's Encrypt via Traefik/Caddy)
```

**Health checks**: `/health` (API), `/healthz` (n8n), `pg_isready` (PG), `redis-cli ping` (Redis)

---

## 🗺️ Roadmap

### Fase 1: Foundation (Semanas 1-2) ✅
- [x] Repo, Docker, CI/CD, DB schema multi-tenant, Auth JWT, Tenant Registry, Document Vault (cuarentena), Calendar sync

### Fase 2: Specialists Parallel (Semanas 3-6) 🔄
- [ ] Mercantil Agent (constitución, juntas, libros, disolución)
- [ ] Administrativo Agent (licencias, subvenciones, recursos)
- [ ] Contable Agent (303, 390, 200, 111, 190, 347, 349, cierres)
- [ ] Personal Agent (nóminas, contratos, TC1/TC2, SS, PRL)

### Fase 3: Orchestration & API (Semanas 7-8)
- [ ] Supervisor Router (intent classification + delegación)
- [ ] Comms Portal (Email, WhatsApp, Portal, Slack)
- [ ] API Gateway completa + Webhooks AEAT/SS
- [ ] E2E: Alta empresa → Factura → 303 → Presentación

### Fase 4: Web UI & Polish (Semanas 9-10)
- [ ] Dashboard Asesor (empresas, alertas, docs, agentes)
- [ ] Portal Cliente (mis docs, mis alertas, subir facturas)
- [ ] Observabilidad (structlog + OTel + Grafana/Loki)
- [ ] Hardening seguridad

### Fase 5+: Mejoras Continuas
- [ ] PWA móvil + Camera API
- [ ] Integración ERP (Holded, FacturaDirecta, Sage, A3)
- [ ] Firma digital (Autofirma/Cl@ve)
- [ ] IA generativa contratos/escritos (RAG + plantillas)
- [ ] Marketplace plantillas/plantillas por comunidad autónoma

---

## 🤝 Contribuir

1. Fork del repo
2. Crear rama: `git checkout -b feature/nueva-funcionalidad`
2. Commits convencionales: `feat:`, `fix:`, `docs:`, `refactor:`
3. Tests obligatorios para nueva funcionalidad
4. PR con descripción clara

---

## 📄 Licencia

MIT License - Ver `LICENSE` para detalles.

---

## 🙋 Soporte

- **Issues**: GitHub Issues para bugs/features
- **Discusiones**: GitHub Discussions para preguntas
- **Email**: soporte@gestia.app

---

**GESTIA** — Tu asesoría, potenciada por IA. 🚀