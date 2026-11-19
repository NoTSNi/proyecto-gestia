# Manual de Uso GESTIA

## 📖 Introducción

GESTIA es un asistente multi-agente para asesorías/gestorías que gestiona empresas en 4 dominios especializados: **Mercantil, Administrativo, Contable y Personal**.

---

## 🚀 Primeros Pasos

### 1. Levantar el Sistema

```bash
cd PROYECTO_GESTIA

# 1. Copiar configuración
cp .env.example .env
# Editar .env con valores reales

# 2. Levantar todos los servicios
docker-compose up -d

# 3. Inicializar la base de datos
docker-compose exec gestia-api python scripts/setup_db.py --seed
```

### 2. Acceder a los Servicios

| Servicio | URL | Usuario | Contraseña |
|----------|-----|---------|------------|
| **API Docs** | http://localhost:8000/docs | - | - |
| **n8n** | http://localhost:5678 | ver .env | `N8N_BASIC_AUTH_PASSWORD` |
| **MinIO Console** | http://localhost:9001 | `MINIO_ACCESS_KEY` | `MINIO_SECRET_KEY` |

### 3. Credenciales Demo (tras --seed)

```
Admin:    admin@gestia.app / admin123 (superadmin)
Asesor:   asesor@gestia.app / asesor123 (asesor_contable)
Cliente:  cliente@demo.com / cliente123 (cliente_titular)
```

---

## 🤖 Uso de Agentes Especialistas

### MercantilAgent (Derecho Mercantil)

**Capacidades:**
- Constitución de sociedades
- Modificación de estatutos
- Disolución y liquidación
- Libros oficiales
- Juntas generales
- Depósito de cuentas anuales

**Ejemplo:**
```
Usuario: "Quiero constituir una SL con 10.000€ de capital"
Agente: "Te ayudo. Necesito: 1) Denominación social, 2) Objeto social, 3) Socios y porcentajes, 4) Administrador(es), 5) Domicilio social"
```

### AdministrativoAgent (Derecho Administrativo)

**Capacidades:**
- Licencias y subvenciones
- Recursos administrativos
- Contratos públicos
- Sanciones administrativas

### ContableAgent (Contabilidad/Fiscalidad)

**Capacidades:**
- Modelos fiscales (303, 390, 200, 111, 190, 347, 349)
- Cierres contables
- Conciliación bancaria

### PersonalAgent (Laboral)

**Capacidades:**
- Nóminas y salarios
- Contratos laborales
- TC1/TC2
- Altas/bajas a la Seguridad Social
- Retenciones IRPF

---

## 📥 Uso de n8n Workflows

### Workflow: gestia-ingest-document

**Trigger:** Webhook `/webhook/gestia-ingest`

**Proceso:**
1. Recibe documento
2. OCR con Docling
3. Clasificación automática
4. Embeddings con PGVector
5. Indexa en base vectorial
6. Callback a sistema

**Tokens ahorrados:** ~500-2000/documento

### Workflow: gestia-calendar-sync

**Trigger:** Cron (lunes 6AM)

**Proceso:**
- Actualiza plazos AEAT/SS/BOE
- Crea alertas 15d/7d/1d/día

### Workflow: gestia-notify-multichannel

**Trigger:** Webhook

**Canales soportados:**
- Email
- Slack
- WhatsApp Business
- Portal web

---

## 📁 Estructura del Proyecto

```
PROYECTO_GESTIA/
├── agents/
│   ├── base_agent.py          # Clase base
│   ├── supervisor.py          # Orquestador
│   ├── specialist_base.py     # Base especialistas
│   └── specialists/           # Agentes (mercantil, admin, contable, personal)
├── api/
│   ├── main.py                # Aplicación FastAPI
│   └── routes/                # Endpoints por dominio
├── gestia_core/               # Paquete compartido
│   ├── config/                # Settings (Pydantic)
│   ├── database/              # SQLAlchemy 2.0 + RLS
│   ├── models/                # Modelos multi-tenant
│   ├── schemas/               # Pydantic schemas
│   ├── security/              # JWT, RBAC, RLS context
│   └── utils/                 # Herramientas
├── shared/                    # Servicios compartidos
│   ├── document_vault/        # OCR, RAG, MinIO
│   ├── calendar_deadlines/    # Calendario fiscal
│   └── comms_portal/          # Comunicaciones
├── n8n/workflows/             # Workflows automatización
├── web-ui/                    # Frontend React
├── docker-compose.yml
└── pyproject.toml
```

---

## 🔐 Seguridad

**Multi-tenant:**
- Row Level Security (RLS) en todas las tablas
- `tenant_id` como columna compartida
- Políticas de aislamiento

**Autenticación:**
- JWT en httpOnly cookies
- Refresh tokens rotativos
- MFA: TOTP + WebAuthn (Passkeys)

**Cifrado:**
- AES-256 en reposo (MinIO SSE-KMS + pgcrypto)
- TLS 1.3 en tránsito

**Audit Log:**
- Append-only, inmutable
- Captura: quién, qué, cuándo, IP, hash

---

## 🧪 Testing

```bash
# Unit tests
docker-compose exec gestia-api pytest tests/unit -v

# Integration tests
docker-compose exec gestia-api pytest tests/integration -v

# E2E tests (Web UI)
cd web-ui && npm run test:e2e
```

---

## 📦 Despliegue

### Desarrollo

```bash
docker-compose up -d
```

### Producción

```bash
# Build images
docker-compose -f docker-compose.yml -f docker-compose.prod.yml build

# Variables críticas requeridas:
# - JWT_SECRET_KEY (64+ chars)
# - N8N_ENCRYPTION_KEY (32 bytes base64)
# - POSTGRES_PASSWORD
# - MINIO_ROOT_PASSWORD
```

---

## 🆘 Soporte

- GitHub Issues: para bugs/features
- GitHub Discussions: preguntas generales
- Email: soporte@gestia.app

---

*GESTIA — Tu asesoría, potenciada por IA.*