# ROADMAP GESTIA — Hoja de ruta consensuada

> Documento vivo. Cada fase deja algo usable. Las fases A–D son las prioridades
> decididas con el cliente (JasCano). Las cláusulas de seguridad del final son
> **invariantes**: ninguna fase puede romperlas.

---

## Fase A — Chat con agentes en la web (✅ completada)

Conectar la inteligencia que ya existe al producto.

- [x] Página de consulta al asesor: el usuario escribe y el **ChiefAgent** enruta al especialista (mercantil/administrativo/contable/personal)
- [x] Los 4 especialistas leen de la BD real (empresas, documentos, calendario, usuarios) en vez de contexto fijo
- [x] Respuesta estructurada: plan de acción, documentos necesarios, fechas, fuentes, confianza
- [x] Control de calidad del supervisor (score ≥ 0.7) y auto-escalación por palabras críticas (inspección, demanda, embargo, fallecimiento)
- [x] Historial de conversaciones por tenant (persistido) — tabla `consultas` + vista `/advisor/consultas`
- [ ] Selector de empresa cliente para el asesor (Fase B habilita el multi-empresa en el chat)

**Definición de "hecho"**: un asesor pregunta "¿qué tiene que presentar Tech Solutions este trimestre?" y recibe una respuesta razonada con datos reales de la BD.

## Fase B — Administración completa multi-tenant (✅ completada)

- [x] Editar empresa (datos fiscales, dirección, régimen, estado)
- [x] Baja/reactivación de empresas (baja lógica con histórico)
- [x] Gestión de usuarios desde la web: alta, edición, cambio de rol, activar/desactivar
- [x] Roles: superadmin, admin_asesoria, asesor_*, cliente_titular, cliente_empleado
- [x] Generación automática de obligaciones al dar de alta (303, 111, TC1/TC2 según régimen y CNAE)
- [x] Selector de empresa cliente en el chat del asesor (consulta multi-empresa)

## Fase C — Ciclo de facturas con validación del cliente (✅ núcleo completado)

Flujo: alta → pendiente → validación del cliente (con corrección) → fusión + log + Excel.

- [x] Alta de facturas desde el portal cliente (formulario con emisor, NIF, fecha, nº, concepto, base, IVA, total)
- [x] **Estado "pendiente de validación"** en BD (tabla `facturas`)
- [x] El cliente revisa y **corrige** los datos antes de validar (tabla editable)
- [x] Validación → pasa a **validada** + **registro en log** (`log_validaciones`: quién, cuándo, qué se corrigió)
- [x] **Exportación Excel por empresa** (openpyxl): hoja Facturas + hoja Log + hoja Empresa, botón "Descargar Excel"
- [x] Aislamiento total por tenant verificado
- [ ] Subida de archivos reales (PDF/imagen/XLSX) con **cuarentena + OCR** — conecta con Document Vault (Fase D)
- [ ] Notificación al cliente al quedar datos pendientes (email/WhatsApp — Fase G)

**Decisión de diseño acordada**: la BD es la fuente de verdad; el Excel es el entregable descargable (hoja principal + log). Los agentes consultan la BD para PYG/IVA/TC1.

## Fase D — Document Vault integrado (✅ núcleo completado)

- [x] Subida de archivos reales desde el portal cliente con **cuarentena**: allowlist por magic bytes (no extensión), hash SHA-256 anti-duplicados, rechazo de ejecutables/macros (.exe, .xlsm, .docm...)
- [x] Extracción de texto: PDF (pypdf), XLSX (solo lectura de celdas), TXT/CSV
- [x] **Almacenamiento por `empresa/año/mes/`** (data/vault/<tenant>/<año>/<mes>) + metadatos en BD
- [x] Clasificación automática por keywords (factura, nómina, contrato, modelo fiscal, escritura, extracto)
- [x] **Búsqueda full-text (FTS5)** aislada por tenant en el portal cliente
- [x] Navegación por año/mes en el portal
- [x] Los agentes reciben el inventario de archivos del tenant en el contexto
- [ ] Embeddings semánticos (all-MiniLM-L6-v2) + búsqueda por similitud — mejora de calidad, FTS5 ya cubre el caso base
- [ ] Descarga del archivo original desde el portal

## Fase E — Seguridad en profundidad (✅ núcleo completado)

- [x] **Anti-hackeo de login**: bloqueo tras 5 intentos fallidos en 15 min, con desbloqueo por administrador (que limpia el contador); registro de cada intento (email/IP/éxito) en `intentos_login`; auditoría de logins fallidos/bloqueados.
- [x] **2FA (TOTP)** con `pyotp`: activación con QR (Google Auth/Authy/MS Auth), 10 códigos de recuperación de un solo uso, verificación en login en 2 pasos, desactivación. Disponible para todos los roles (recomendado en asesor/admin).
- [x] **Agente monitor de seguridad**: barrido del audit log (ráfagas de logins fallidos, cuentas bloqueadas, 2FA fallidos, cambios 2FA) → informe + resumen; panel `/advisor/seguridad` con botón "Ejecutar barrido".
- [x] **Auditoría de seguridad**: tabla `audit_seguridad` (tipo, detalle, tenant, usuario, IP, severidad) para toda acción sensible.
- [x] **Anti-bucle y control de coste**: `agents/cost_control.py` — `AgentBudget` con límite de tokens por consulta, máx. iteraciones de descomposición, máx. subtareas, timeout global (`asyncio.timeout`); el ChiefAgent gasta tokens en cada operación y corta (devuelve error controlado) si se excede; informe de coste visible en el chat.
- [x] **Model routing**: `agents/model_routing.py` — mejor modelo por tarea/dominio, configurable por entorno; tareas mecánicas SIN LLM. (Conexión con LLM real pendiente en Fase H.)
- [ ] Alertas automatizadas del monitor (email/WhatsApp — Fase G).

## Fase F — Bases de conocimiento por especialista (RAG curado) (✅ núcleo completado)

- [x] **KB curada por dominio** en `agents/knowledge_base.py` (FTS5 local, sin servicios externos):
  - Contable: modelos 303/390/200/111/347/349, cierre contable, beneficios I+D, reserva capitalización, TC1/TC2
  - Mercantil: constitución, juntas, libros, depósito cuentas, disolución, ampliación/reducción capital
  - Laboral: tipos de contrato, nómina, IRPF retenciones, altas/bajas SS, PRL
  - Administrativo: licencias, subvenciones, recursos, contratación pública, expedientes sancionadores
- [x] **Cada agente consulta su KB** y añade citas normativas (⚖ + fuentes) a sus respuestas vía `_enrich_with_kb`
- [x] **Model routing** en `agents/model_routing.py`: mejor modelo por tarea/dominio, configurable por entorno; tareas mecánicas SIN LLM. (Pendiente conectarlo al LLM real en Fase H.)
- [x] **Detección proactiva de beneficios fiscales** (`web/services/beneficios.py`): analiza cada empresa y alerta a la asesoría (I+D, sector tecnológico/energético) — mostrado en el dashboard del asesor, con fuentes
- [x] Fuentes + fecha de vigencia en cada entrada; **el agente propone, la asesoría decide**
- [ ] Integrar con LLM real (RAG semántico con embeddings + modelo por agente) — Fase H
- [ ] KB actualizable / versionable en el panel (CRUD de conocimiento)

## Fase G — Canales y automatización reales (✅ núcleo completado)

- [x] **CommsPortal** (`web/services/comms.py`): capa unificada de comunicaciones con 3 canales y **modo mock seguro por defecto** (sin credenciales = demo, sin envío externo; con credenciales = envío real):
  - **Email (SMTP real)**: `GESTIA_SMTP_HOST/PORT/USER/PASS/FROM`. Requiere host+user para saltar de mock a real (TLS).
  - **WhatsApp (Twilio Sandbox, gratis para pruebas)**: `GESTIA_TWILIO_ACCOUNT_SID/AUTH_TOKEN/WHATSAPP_FROM`. Sin credenciales → mock.
  - **n8n automatizaciones**: `GESTIA_N8N_WEBHOOK_URL` — GESTIA notifica eventos a workflows n8n (que a su vez pueden llamar de vuelta a GESTIA).
- [x] **Tabla `comunicaciones`** (append-only por tenant): canal, destino, asunto, cuerpo, estado (real|mock|error), id externo, usuario, fecha — auditoría de cada envío.
- [x] **Panel `/advisor/comunicaciones` real**: estado de cada canal (mock/real), formulario de envío de prueba (email/whatsapp/n8n) y historial de envíos.
- [x] **Eventos n8n disparados automáticamente**: `documento_recibido` (al subir archivo validado), `factura_registrada` (alta de factura), `cliente_nuevo` (alta de empresa). Cron para plazos y alertas del monitor: pendiente (ver abajo).
- [x] Cada envío se registra en BD igual en mock que en real.
- [ ] **Cron de plazos próximos** (recordatorios de modelos 303/111/TC1 a clientes + alertas del monitor de seguridad) — conectar a n8n/email de forma programada.
- [ ] **Configuración de credenciales por empresa** en el panel (hoy se configuran por variables de entorno).
- [ ] **Reportes**: revisar a fondo con el cliente qué reportes necesita la asesoría. Anotado.
- [ ] Chat por WhatsApp (misma lógica del chat web, transporte diferente)
- [ ] Email real (SMTP propio, DKIM/SPF/DMARC)
- [ ] n8n desplegado: calendario fiscal sincronizado, alertas 15/7/1 días, notificaciones multi-canal
- [ ] API/SFTP para ERP (clientes grandes)

## Fase H — Producción

- [ ] Postgres + RLS (aislamiento a nivel de BD)
- [ ] Docker Compose completo (api, web, postgres, redis, n8n, vault)
- [ ] CI/CD, backups, observabilidad

---

## Invariantes de seguridad (NO negociables)

1. **Los datos aportados por clientes son SOLO datos.** Nunca se ejecutan, nunca se interpretan como instrucciones para el sistema ni los agentes, y nunca se mezclan con el prompt de sistema. Todo contenido entrante pasa por cuarentena (allowlist de tipos, magic bytes, hash) y el agente recibe el contenido como *dato*, no como *orden*.
2. **Aislamiento total de tenants.** El tenant se deriva SIEMPRE del JWT del servidor, nunca de parámetros del cliente. Ningún cliente puede ver datos de otro cliente, por ningún canal.
3. **Auditoría.** Toda acción sensible (acceso, subida, validación, cambio de rol) queda registrada de forma append-only.
4. **Control de coste.** Ningún agente puede quedarse en bucle: presupuesto de tokens, máximo de iteraciones, timeout y circuit breaker por defecto.
5. **Modelo adecuado a la tarea.** Ninguna tarea mecánica usa LLM si puede ser determinista; el routing de modelos es configurable y auditable.
6. **El agente propone, la asesoría decide.** Las respuestas con implicación legal/fiscal son recomendaciones con fuentes, no decisiones ejecutadas sin supervisión.
