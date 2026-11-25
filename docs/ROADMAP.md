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

## Fase C — Ciclo de facturas con validación del cliente

Flujo: subida → lectura → hoja pendiente → validación del cliente → fusión + log.

- [ ] Subida de documentos desde el portal cliente (PDF, imagen, CSV, XLSX sin macros)
- [ ] OCR + extracción de datos (Docling): emisor, NIF, fecha, base, IVA, total, concepto
- [ ] **Hoja "pendiente de validar"** por empresa (en BD y en el Excel exportado)
- [ ] Notificación al cliente: "revisa y valida los datos extraídos"
- [ ] Tras validación: fusión con la hoja principal + **registro de log** (datos aportados, quién validó, cuándo)
- [ ] Exportación Excel por empresa: hoja principal + hoja pendiente + hoja log
- [ ] Almacenamiento de documentos por `empresa/año/mes/` + metadatos en BD

**Fuente de verdad: BD.** El Excel es el entregable/exportación para el cliente; la BD permite a los agentes consultar (PYG, IVA, TC1/TC2).

## Fase D — Document Vault integrado

- [ ] Subida → cuarentena → OCR → clasificación → embeddings (all-MiniLM-L6-v2) → índice por tenant
- [ ] Búsqueda semántica en el portal
- [ ] Los agentes citan documentos reales en sus respuestas
- [ ] Aislamiento total del índice por tenant

## Fase E — Seguridad en profundidad

- [ ] **2FA (TOTP)** para cuentas de asesor/admin (obligatorio) y clientes (opcional): `pyotp`, QR, 10 códigos de recuperación. *Adelantable — argumento de venta antes de la primera visita a una asesoría.*
- [ ] **Agente monitor de seguridad**: revisa el audit log (accesos no permitidos, login fallidos, subidas sospechosas, accesos cross-tenant) en ejecución programada y alerta a la asesoría
- [ ] **Anti-bucle y control de coste**: presupuesto de tokens por consulta, máx. iteraciones por agente, timeout, circuit breaker
- [ ] **Model routing**: mejor modelo por tarea (router barato/rápido, razonamiento potente, mecánico sin LLM); configurable por agente vía OpenRouter
- [ ] Rate limiting, auditoría append-only de toda acción sensible

## Fase F — Bases de conocimiento por especialista (RAG curado)

- [ ] KB Contable: modelos AEAT (303, 390, 200, 111, 190, 347, 349...), cómo redactarlos, cuándo presentarlos, beneficios fiscales y requisitos
- [ ] KB Mercantil: constitución, juntas, libros, disolución, depósito de cuentas
- [ ] KB Laboral: nóminas, contratos, TC1/TC2, altas/bajas SS, PRL, IRPF
- [ ] KB Administrativo: licencias, subvenciones, recursos, contratación pública
- [ ] Detección proactiva: "a este cliente le falta requisito X para el beneficio Y" → alerta a la asesoría
- [ ] Fuentes oficiales + versionado + fecha de vigencia. **El agente propone, la asesoría firma.**

## Fase G — Canales y automatización reales

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
