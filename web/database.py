"""GESTIA Web - Capa de datos SQLite (multi-tenant).

Base de datos local SQLite con esquema real para la web:
- empresas  (tenants)
- usuarios  (roles por tenant)
- documentos, notificaciones, calendario_eventos (aislados por tenant)

Usa aiosqlite para no bloquear el bucle de FastAPI. Toda query de tenant
recibe tenant_id explicitamente (isolacion a nivel de aplicacion).
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import aiosqlite

# Ubicacion de la BD: data/gestia_web.db junto al proyecto
_DB_DIR = Path(__file__).resolve().parent.parent / "data"
_DB_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = _DB_DIR / "gestia_web.db"

_SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS empresas (
    id               TEXT PRIMARY KEY,
    nif              TEXT NOT NULL UNIQUE,
    nombre           TEXT NOT NULL,
    nombre_comercial TEXT,
    regimen_iva      TEXT DEFAULT 'general',
    periodicidad_iva TEXT DEFAULT 'trimestral',
    cnae             TEXT,
    estado           TEXT DEFAULT 'activa',
    direccion        TEXT,
    municipio        TEXT,
    provincia        TEXT,
    telefono         TEXT,
    movil            TEXT,
    email_contacto   TEXT,
    whatsapp         TEXT,
    web              TEXT,
    persona_contacto TEXT,
    metadata_json    TEXT DEFAULT '{}',
    created_at       TEXT NOT NULL,
    updated_at       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS usuarios (
    id            TEXT PRIMARY KEY,
    email         TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    full_name     TEXT,
    rol           TEXT NOT NULL DEFAULT 'cliente',
    tenant_id     TEXT,
    activo        INTEGER NOT NULL DEFAULT 1,
    tfa_secret    TEXT,
    tfa_activado  INTEGER NOT NULL DEFAULT 0,
    recovery_codes TEXT DEFAULT '[]',
    bloqueado     INTEGER NOT NULL DEFAULT 0,
    intentos_fallidos INTEGER NOT NULL DEFAULT 0,
    ultimo_intento TEXT,
    created_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL,
    FOREIGN KEY (tenant_id) REFERENCES empresas(id)
);

CREATE TABLE IF NOT EXISTS intentos_login (
    id         TEXT PRIMARY KEY,
    email      TEXT NOT NULL,
    ip         TEXT,
    exito      INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    created_ts REAL
);

CREATE INDEX IF NOT EXISTS idx_intentos_email ON intentos_login (email);

CREATE TABLE IF NOT EXISTS audit_seguridad (
    id         TEXT PRIMARY KEY,
    tipo       TEXT NOT NULL,
    detalle    TEXT,
    tenant_id  TEXT,
    usuario    TEXT,
    ip         TEXT,
    severidad  TEXT DEFAULT 'info',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS documentos (
    id         TEXT PRIMARY KEY,
    tenant_id  TEXT NOT NULL,
    nombre     TEXT NOT NULL,
    tipo       TEXT NOT NULL DEFAULT 'otro',
    estado     TEXT NOT NULL DEFAULT 'clasificado',
    cantidad   TEXT,
    monto      TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (tenant_id) REFERENCES empresas(id)
);

CREATE TABLE IF NOT EXISTS notificaciones (
    id         TEXT PRIMARY KEY,
    tenant_id  TEXT NOT NULL,
    mensaje    TEXT NOT NULL,
    subtitulo  TEXT,
    tipo       TEXT DEFAULT 'info',
    leida      INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    FOREIGN KEY (tenant_id) REFERENCES empresas(id)
);

CREATE TABLE IF NOT EXISTS calendario_eventos (
    id          TEXT PRIMARY KEY,
    tenant_id   TEXT NOT NULL,
    titulo      TEXT NOT NULL,
    descripcion TEXT,
    tipo        TEXT DEFAULT 'fiscal',
    fecha       TEXT NOT NULL,
    FOREIGN KEY (tenant_id) REFERENCES empresas(id)
);

CREATE TABLE IF NOT EXISTS consultas (
    id         TEXT PRIMARY KEY,
    tenant_id  TEXT NOT NULL,
    user_id    TEXT NOT NULL,
    query      TEXT NOT NULL,
    respuesta  TEXT NOT NULL,
    agente     TEXT,
    strategy   TEXT,
    success    INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    FOREIGN KEY (tenant_id) REFERENCES empresas(id)
);

CREATE TABLE IF NOT EXISTS facturas (
    id              TEXT PRIMARY KEY,
    tenant_id       TEXT NOT NULL,
    emisor          TEXT,
    nif_emisor      TEXT,
    fecha_factura   TEXT,
    numero          TEXT,
    concepto        TEXT,
    base            TEXT,
    iva             TEXT,
    total           TEXT,
    tipo            TEXT DEFAULT 'recibida',
    estado          TEXT NOT NULL DEFAULT 'pendiente_validacion',
    archivo_original TEXT,
    creado_por      TEXT,
    validado_por    TEXT,
    validado_en     TEXT,
    created_at      TEXT NOT NULL,
    FOREIGN KEY (tenant_id) REFERENCES empresas(id)
);

CREATE TABLE IF NOT EXISTS log_validaciones (
    id          TEXT PRIMARY KEY,
    tenant_id   TEXT NOT NULL,
    factura_id  TEXT NOT NULL,
    accion      TEXT NOT NULL,
    detalle     TEXT,
    usuario     TEXT,
    created_at  TEXT NOT NULL,
    FOREIGN KEY (tenant_id) REFERENCES empresas(id)
);

CREATE TABLE IF NOT EXISTS archivos (
    id          TEXT PRIMARY KEY,
    tenant_id   TEXT NOT NULL,
    nombre      TEXT NOT NULL,
    ruta        TEXT NOT NULL,
    tipo        TEXT,
    tamano      INTEGER,
    hash_sha256 TEXT NOT NULL,
    anio        TEXT NOT NULL,
    mes         TEXT NOT NULL,
    estado      TEXT NOT NULL DEFAULT 'clasificado',
    texto       TEXT DEFAULT '',
    clasificacion TEXT,
    subido_por  TEXT,
    created_at  TEXT NOT NULL,
    FOREIGN KEY (tenant_id) REFERENCES empresas(id)
);

CREATE VIRTUAL TABLE IF NOT EXISTS archivos_fts_v2 USING fts5(
    nombre, texto, archivo_id UNINDEXED, tokenize='porter unicode61'
);
"""

_demo_empresas = [
    {
        "id": "demo-tech-solutions", "nif": "B12345678",
        "nombre": "Tech Solutions SL", "nombre_comercial": "Tech Solutions",
        "regimen_iva": "general", "periodicidad_iva": "trimestral", "cnae": "6201",
        "estado": "activa", "direccion": "Calle Mayor 10",
        "municipio": "Madrid", "provincia": "Madrid",
    },
    {
        "id": "demo-construcciones", "nif": "B87654321",
        "nombre": "Construcciones del Sur SL", "nombre_comercial": "Construcciones Sur",
        "regimen_iva": "general", "periodicidad_iva": "mensual", "cnae": "4121",
        "estado": "activa", "direccion": "Avda. América 5",
        "municipio": "Sevilla", "provincia": "Sevilla",
    },
    {
        "id": "demo-asesoria", "nif": "B11111111",
        "nombre": "GESTIA Asesores SL", "nombre_comercial": "GESTIA",
        "regimen_iva": "simplificado", "periodicidad_iva": "trimestral", "cnae": "6920",
        "estado": "activa", "direccion": "Calle Principal 1",
        "municipio": "Madrid", "provincia": "Madrid",
    },
]

# (id, email, full_name, rol, tenant_id, password_plano)
_usuarios_demo = [
    ("usuario-admin", "admin@gestia.app", "Admin GESTIA", "superadmin", "demo-asesoria", "admin123"),
    ("usuario-asesor", "asesor@gestia.app", "Ana García", "asesor_contable", "demo-asesoria", "asesor123"),
    ("usuario-cliente-tech", "cliente@tech-solutions.com", "Tech Solutions SL", "cliente_titular", "demo-tech-solutions", "cliente123"),
    ("usuario-cliente-sur", "cliente@construccionessur.com", "Construcciones del Sur SL", "cliente_titular", "demo-construcciones", "cliente123"),
]

_documentos_demo = {
    "demo-tech-solutions": [
        ("Factura Telefónica - Mar 2025", "factura_recibida", "completado", "118,58 €"),
        ("Nómina Enero 2025 - Juan Pérez", "nomina", "pendiente", "1.880,00 €"),
        ("Contrato laboral - Nuevo empleado", "contrato_laboral", "en_revision", "—"),
        ("Modelo 303 - IVA Q1 2025", "modelo_303", "en_preparacion", "1.250,00 €"),
    ],
    "demo-construcciones": [
        ("Factura Proveedor Cemento - Feb 2025", "factura_recibida", "completado", "2.340,00 €"),
        ("REA - Recurso alzada licencia obra", "recurso", "tramitacion", "—"),
        ("Modelo 111 - IRPF Q1 2025", "modelo_111", "en_preparacion", "4.120,00 €"),
    ],
    "demo-asesoria": [
        ("Escritura constitución", "escritura_publica", "clasificado", "—"),
        ("Modelo 390 - Resumen anual 2024", "modelo_390", "completado", "0,00 €"),
    ],
}

_notificaciones_demo = {
    "demo-tech-solutions": [
        ("Modelo 303 vence en 5 días", "IVA Q1 2025 - Presenta antes 20/04", "danger"),
        ("Nómina enero pendiente de firmar", "Juan Pérez García - Revisa y firma", "warning"),
        ("Nuevo mensaje de tu asesor", "Respuesta sobre contrato indefinido", "info"),
    ],
    "demo-construcciones": [
        ("Modelo 111 vence en 7 días", "IRPF Q1 2025 - Presenta antes 20/04", "danger"),
        ("Licencia de obra pendiente de resolución", "Ayuntamiento de Sevilla", "warning"),
    ],
    "demo-asesoria": [
        ("Depósito de cuentas 2025", "Registro Mercantil - Presenta antes 30/06", "info"),
    ],
}

_eventos_demo = {
    "demo-tech-solutions": [
        ("Modelo 303 - Q1", "Presentación IVA trimestral", "fiscal", "2025-04-20"),
        ("Modelo 111 - Q1", "Retenciones IRPF", "fiscal", "2025-04-20"),
        ("TC1/TC2", "Seguridad Social mensual", "laboral", "2025-04-30"),
    ],
    "demo-construcciones": [
        ("Modelo 111 - Q1", "Retenciones IRPF", "fiscal", "2025-04-20"),
        ("Licencia obra", "Resolución esperada", "administrativo", "2025-05-15"),
    ],
    "demo-asesoria": [
        ("Depósito cuentas", "Registro Mercantil", "mercantil", "2025-06-30"),
    ],
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return str(uuid4())


async def get_db() -> aiosqlite.Connection:
    """Abro una conexion aiosqlite (por request)."""
    conn = await aiosqlite.connect(DB_PATH)
    conn.row_factory = aiosqlite.Row
    return conn


def hash_password(password: str) -> str:
    """Hash bcrypt real (bcrypt 5 no es compatible con passlib)."""
    import bcrypt

    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    import bcrypt

    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


async def init_db() -> None:
    """Crea tablas y siembra datos demo (idempotente)."""
    conn = await get_db()
    try:
        await conn.executescript(_SCHEMA)

        # Migración ligera: columnas de contacto (BD creadas antes de Fase C)
        cur = await conn.execute("PRAGMA table_info(empresas)")
        cols = {row["name"] for row in await cur.fetchall()}
        for col in ("telefono", "movil", "email_contacto", "whatsapp", "web", "persona_contacto"):
            if col not in cols:
                await conn.execute(f"ALTER TABLE empresas ADD COLUMN {col} TEXT")

        # Migración ligera: columnas de seguridad 2FA en usuarios (Fase E)
        cur = await conn.execute("PRAGMA table_info(usuarios)")
        cols_usuario = {row["name"] for row in await cur.fetchall()}
        for col_us in ("tfa_secret", "recovery_codes", "bloqueado", "intentos_fallidos", "ultimo_intento"):
            if col_us not in cols_usuario:
                tipo = "INTEGER NOT NULL DEFAULT 0" if col_us in ("bloqueado", "intentos_fallidos") else "TEXT"
                if col_us == "tfa_activado":
                    continue
                await conn.execute(f"ALTER TABLE usuarios ADD COLUMN {col_us} {tipo}")
        if "tfa_activado" not in cols_usuario:
            await conn.execute("ALTER TABLE usuarios ADD COLUMN tfa_activado INTEGER NOT NULL DEFAULT 0")

        # Migración ligera: created_ts (epoch) en intentos_login (Fase E)
        try:
            cur = await conn.execute("PRAGMA table_info(intentos_login)")
            cols_int = {row["name"] for row in await cur.fetchall()}
            if "created_ts" not in cols_int:
                await conn.execute("ALTER TABLE intentos_login ADD COLUMN created_ts REAL")
        except Exception:
            pass

        now = _now()
        for emp in _demo_empresas:
            cur = await conn.execute("SELECT 1 FROM empresas WHERE id = ?", (emp["id"],))
            if not await cur.fetchone():
                await conn.execute(
                    """INSERT INTO empresas
                    (id, nif, nombre, nombre_comercial, regimen_iva, periodicidad_iva,
                     cnae, estado, direccion, municipio, provincia, metadata_json, created_at, updated_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        emp["id"], emp["nif"], emp["nombre"], emp["nombre_comercial"],
                        emp["regimen_iva"], emp["periodicidad_iva"], emp["cnae"],
                        emp["estado"], emp["direccion"], emp["municipio"], emp["provincia"],
                        "{}", now, now,
                    ),
                )

        for uid, email, name, rol, tenant, plain in _usuarios_demo:
            cur = await conn.execute("SELECT 1 FROM usuarios WHERE email = ?", (email,))
            if not await cur.fetchone():
                await conn.execute(
                    """INSERT INTO usuarios
                    (id, email, password_hash, full_name, rol, tenant_id, activo, created_at, updated_at)
                    VALUES (?,?,?,?,?,?,1,?,?)""",
                    (uid, email, hash_password(plain), name, rol, tenant, now, now),
                )

        for tenant_id, docs in _documentos_demo.items():
            cur = await conn.execute("SELECT COUNT(*) c FROM documentos WHERE tenant_id = ?", (tenant_id,))
            row = await cur.fetchone()
            if row and row["c"] == 0:
                for nombre, tipo, estado, monto in docs:
                    await conn.execute(
                        """INSERT INTO documentos (id, tenant_id, nombre, tipo, estado, cantidad, monto, created_at)
                        VALUES (?,?,?,?,?,?,?,?)""",
                        (_new_id(), tenant_id, nombre, tipo, estado, "1", monto, now),
                    )

        for tenant_id, notifs in _notificaciones_demo.items():
            cur = await conn.execute("SELECT COUNT(*) c FROM notificaciones WHERE tenant_id = ?", (tenant_id,))
            row = await cur.fetchone()
            if row and row["c"] == 0:
                for mensaje, subtitulo, tipo in notifs:
                    await conn.execute(
                        """INSERT INTO notificaciones (id, tenant_id, mensaje, subtitulo, tipo, leida, created_at)
                        VALUES (?,?,?,?,?,0,?)""",
                        (_new_id(), tenant_id, mensaje, subtitulo, tipo, now),
                    )

        for tenant_id, events in _eventos_demo.items():
            cur = await conn.execute("SELECT COUNT(*) c FROM calendario_eventos WHERE tenant_id = ?", (tenant_id,))
            row = await cur.fetchone()
            if row and row["c"] == 0:
                for titulo, desc, tipo, fecha in events:
                    await conn.execute(
                        """INSERT INTO calendario_eventos (id, tenant_id, titulo, descripcion, tipo, fecha)
                        VALUES (?,?,?,?,?,?)""",
                        (_new_id(), tenant_id, titulo, desc, tipo, fecha),
                    )

        await conn.commit()
    finally:
        await conn.close()


async def get_empresa(tenant_id: str) -> dict | None:
    conn = await get_db()
    try:
        cur = await conn.execute("SELECT * FROM empresas WHERE id = ?", (tenant_id,))
        row = await cur.fetchone()
        return dict(row) if row else None
    finally:
        await conn.close()


async def list_empresas() -> list[dict]:
    conn = await get_db()
    try:
        cur = await conn.execute("SELECT * FROM empresas ORDER BY nombre", ())
        rows = await cur.fetchall()
        return [dict(r) for r in rows]
    finally:
        await conn.close()


async def list_documentos(tenant_id: str) -> list[dict]:
    conn = await get_db()
    try:
        cur = await conn.execute(
            "SELECT * FROM documentos WHERE tenant_id = ? ORDER BY created_at DESC", (tenant_id,)
        )
        rows = await cur.fetchall()
        return [dict(r) for r in rows]
    finally:
        await conn.close()


async def list_notificaciones(tenant_id: str) -> list[dict]:
    conn = await get_db()
    try:
        cur = await conn.execute(
            "SELECT * FROM notificaciones WHERE tenant_id = ? ORDER BY created_at DESC", (tenant_id,)
        )
        rows = await cur.fetchall()
        return [dict(r) for r in rows]
    finally:
        await conn.close()


async def list_eventos(tenant_id: str) -> list[dict]:
    conn = await get_db()
    try:
        cur = await conn.execute(
            "SELECT * FROM calendario_eventos WHERE tenant_id = ? ORDER BY fecha", (tenant_id,)
        )
        rows = await cur.fetchall()
        return [dict(r) for r in rows]
    finally:
        await conn.close()


async def list_usuarios(tenant_id: str | None = None) -> list[dict]:
    """Si tenant_id es None, devuelve todos (superadmin/asesor)."""
    conn = await get_db()
    try:
        if tenant_id:
            cur = await conn.execute(
                "SELECT * FROM usuarios WHERE tenant_id = ? ORDER BY full_name", (tenant_id,)
            )
        else:
            cur = await conn.execute("SELECT * FROM usuarios ORDER BY full_name", ())
        rows = await cur.fetchall()
        return [dict(r) for r in rows]
    finally:
        await conn.close()


async def crear_empresa(data: dict) -> str:
    """Crea una empresa (tenant) y devuelve su id."""
    conn = await get_db()
    try:
        now = _now()
        eid = _new_id()
        await conn.execute(
            """INSERT INTO empresas
            (id, nif, nombre, nombre_comercial, regimen_iva, periodicidad_iva,
             cnae, estado, direccion, municipio, provincia, telefono, movil,
             email_contacto, whatsapp, web, persona_contacto, metadata_json, created_at, updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                eid, data.get("nif", ""), data.get("nombre", ""),
                data.get("nombre_comercial"), data.get("regimen_iva", "general"),
                data.get("periodicidad_iva", "trimestral"), data.get("cnae"),
                data.get("estado", "activa"), data.get("direccion"),
                data.get("municipio"), data.get("provincia"), data.get("telefono"),
                data.get("movil"), data.get("email_contacto"), data.get("whatsapp"),
                data.get("web"), data.get("persona_contacto"),
                "{}", now, now,
            ),
        )
        await conn.commit()
        return eid
    finally:
        await conn.close()


async def get_usuario_by_email(email: str) -> dict | None:
    conn = await get_db()
    try:
        cur = await conn.execute("SELECT * FROM usuarios WHERE email = ?", (email,))
        row = await cur.fetchone()
        return dict(row) if row else None
    finally:
        await conn.close()


async def actualizar_empresa(tenant_id: str, data: dict) -> None:
    """Actualiza los datos editables de una empresa (tenant)."""
    conn = await get_db()
    try:
        await conn.execute(
            """UPDATE empresas SET
                nif = ?, nombre = ?, nombre_comercial = ?, regimen_iva = ?,
                periodicidad_iva = ?, cnae = ?, direccion = ?, municipio = ?,
                provincia = ?, estado = ?, telefono = ?, movil = ?,
                email_contacto = ?, whatsapp = ?, web = ?, persona_contacto = ?,
                updated_at = ?
            WHERE id = ?""",
            (
                data.get("nif", ""), data.get("nombre", ""),
                data.get("nombre_comercial"), data.get("regimen_iva", "general"),
                data.get("periodicidad_iva", "trimestral"), data.get("cnae"),
                data.get("direccion"), data.get("municipio"), data.get("provincia"),
                data.get("estado", "activa"), data.get("telefono"), data.get("movil"),
                data.get("email_contacto"), data.get("whatsapp"), data.get("web"),
                data.get("persona_contacto"), _now(), tenant_id,
            ),
        )
        await conn.commit()
    finally:
        await conn.close()


async def cambiar_estado_empresa(tenant_id: str, estado: str) -> None:
    """Baja lógica / reactivación de una empresa (estado: baja|inactiva|activa)."""
    conn = await get_db()
    try:
        await conn.execute(
            "UPDATE empresas SET estado = ?, updated_at = ? WHERE id = ?",
            (estado, _now(), tenant_id),
        )
        await conn.commit()
    finally:
        await conn.close()


async def crear_usuario(
    email: str,
    password: str,
    full_name: str,
    rol: str,
    tenant_id: str | None,
) -> None:
    """Da de alta un usuario con rol (para la asesoría o un cliente)."""
    conn = await get_db()
    try:
        now = _now()
        await conn.execute(
            """INSERT INTO usuarios
            (id, email, password_hash, full_name, rol, tenant_id, activo, created_at, updated_at)
            VALUES (?,?,?,?,?,?,1,?,?)""",
            (_new_id(), email.strip().lower(), hash_password(password),
             full_name.strip(), rol, tenant_id, now, now),
        )
        await conn.commit()
    finally:
        await conn.close()


async def actualizar_usuario(usuario_id: str, full_name: str | None = None,
                             rol: str | None = None) -> None:
    """Actualiza nombre y/o rol de un usuario."""
    conn = await get_db()
    try:
        sets, params = [], []
        if full_name is not None:
            sets.append("full_name = ?")
            params.append(full_name)
        if rol is not None:
            sets.append("rol = ?")
            params.append(rol)
        if not sets:
            return
        sets.append("updated_at = ?")
        params.append(_now())
        params.append(usuario_id)
        await conn.execute(f"UPDATE usuarios SET {', '.join(sets)} WHERE id = ?", params)
        await conn.commit()
    finally:
        await conn.close()


async def cambiar_estado_usuario(usuario_id: str, activo: bool) -> None:
    """Activa/desactiva un usuario (baja lógica)."""
    conn = await get_db()
    try:
        await conn.execute(
            "UPDATE usuarios SET activo = ?, updated_at = ? WHERE id = ?",
            (1 if activo else 0, _now(), usuario_id),
        )
        await conn.commit()
    finally:
        await conn.close()


# Obligaciones fiscales base por régimen (se generan al dar de alta una empresa)
_OBLIGACIONES_BASE = {
    "general": [
        ("Modelo 303 - IVA trimestral", "Presentación IVA (cuatrimestral)", "fiscal"),
        ("Modelo 111 - Retenciones IRPF", "Retenciones IRPF (trimestral)", "fiscal"),
        ("TC1/TC2 - Seguridad Social", "Cotizaciones mensuales SS", "laboral"),
    ],
    "simplificado": [
        ("Modelo 303 - IVA simplificado", "Presentación IVA (cuatrimestral)", "fiscal"),
        ("Modelo 111 - Retenciones IRPF", "Retenciones IRPF (trimestral)", "fiscal"),
        ("TC1/TC2 - Seguridad Social", "Cotizaciones mensuales SS", "laboral"),
    ],
}


async def generar_obligaciones(tenant_id: str) -> int:
    """Genera el calendario de obligaciones base para una empresa nueva.

    Devuelve el número de obligaciones creadas. Idempotente: si ya existen
    eventos de tipo 'fiscal'/'laboral' para el tenant, no duplica.
    """
    conn = await get_db()
    try:
        empresa = await get_empresa(tenant_id)
        if not empresa:
            return 0
        regimen = empresa.get("regimen_iva", "general")
        obligaciones = _OBLIGACIONES_BASE.get(regimen, _OBLIGACIONES_BASE["general"])

        cur = await conn.execute(
            "SELECT COUNT(*) c FROM calendario_eventos WHERE tenant_id = ? AND tipo IN ('fiscal','laboral')",
            (tenant_id,),
        )
        row = await cur.fetchone()
        if row and row["c"] > 0:
            return 0  # ya generadas

        creadas = 0
        for titulo, desc, tipo in obligaciones:
            await conn.execute(
                """INSERT INTO calendario_eventos (id, tenant_id, titulo, descripcion, tipo, fecha)
                VALUES (?,?,?,?,?,?)""",
                (_new_id(), tenant_id, titulo, desc, tipo, _now()[:10]),
            )
            creadas += 1
        await conn.commit()
        return creadas
    finally:
        await conn.close()


async def registrar_consulta(
    tenant_id: str,
    user_id: str,
    query: str,
    respuesta: str,
    agente: str | None = None,
    strategy: str | None = None,
    success: bool = True,
) -> None:
    """Registra una consulta y su respuesta (auditoría por tenant)."""
    conn = await get_db()
    try:
        await conn.execute(
            """INSERT INTO consultas (id, tenant_id, user_id, query, respuesta, agente, strategy, success, created_at)
            VALUES (?,?,?,?,?,?,?,?,?)""",
            (_new_id(), tenant_id, user_id, query, respuesta, agente, strategy,
             1 if success else 0, _now()),
        )
        await conn.commit()
    finally:
        await conn.close()


async def list_consultas(tenant_id: str | None = None, limit: int = 100) -> list[dict]:
    """Consulta el histórico de preguntas/respuestas (filtrado por tenant)."""
    conn = await get_db()
    try:
        if tenant_id:
            cur = await conn.execute(
                "SELECT * FROM consultas WHERE tenant_id = ? ORDER BY created_at DESC LIMIT ?",
                (tenant_id, limit),
            )
        else:
            cur = await conn.execute(
                "SELECT * FROM consultas ORDER BY created_at DESC LIMIT ?", (limit,)
            )
        rows = await cur.fetchall()
        return [dict(r) for r in rows]
    finally:
        await conn.close()


# ---------------------------------------------------------------------------
# DOCUMENT VAULT (Fase D)
# ---------------------------------------------------------------------------

async def registrar_archivo(
    tenant_id: str, nombre: str, ruta: str, tipo: str | None, tamano: int,
    hash_sha256: str, anio: str, mes: str, texto: str, clasificacion: str,
    subido_por: str | None = None,
) -> dict:
    """Guarda el registro del archivo y lo indexa en FTS5."""
    conn = await get_db()
    try:
        now = _now()
        aid = _new_id()
        await conn.execute(
            """INSERT INTO archivos
            (id, tenant_id, nombre, ruta, tipo, tamano, hash_sha256, anio, mes,
             estado, texto, clasificacion, subido_por, created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (aid, tenant_id, nombre, ruta, tipo, tamano, hash_sha256, anio, mes,
             "indexado", texto, clasificacion, subido_por, now),
        )
        # Índice FTS5 (archivo_id UNINDEXED para cruzar; rowid numérico automático)
        await conn.execute("INSERT INTO archivos_fts_v2(nombre, texto, archivo_id) VALUES (?,?,?)",
                           (nombre, texto, aid))
        await conn.commit()
        return {"id": aid}
    finally:
        await conn.close()


async def buscar_hash(tenant_id: str) -> list[str]:
    conn = await get_db()
    try:
        cur = await conn.execute(
            "SELECT hash_sha256 FROM archivos WHERE tenant_id = ?", (tenant_id,)
        )
        rows = await cur.fetchall()
        return [r["hash_sha256"] for r in rows]
    finally:
        await conn.close()


async def list_archivos(tenant_id: str | None = None, anio: str | None = None,
                        mes: str | None = None) -> list[dict]:
    """Lista archivos del tenant, opcionalmente filtrado por año/mes."""
    conn = await get_db()
    try:
        where, params = [], []
        if tenant_id:
            where.append("tenant_id = ?")
            params.append(tenant_id)
        if anio:
            where.append("anio = ?")
            params.append(anio)
        if mes:
            where.append("mes = ?")
            params.append(mes)
        sql = "SELECT * FROM archivos"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY created_at DESC"
        cur = await conn.execute(sql, params)
        rows = await cur.fetchall()
        return [dict(r) for r in rows]
    finally:
        await conn.close()


async def list_anios_meses(tenant_id: str) -> list[dict]:
    """Agrupa los archivos por año/mes para la navegación."""
    conn = await get_db()
    try:
        cur = await conn.execute(
            """SELECT anio, mes, COUNT(*) n FROM archivos
            WHERE tenant_id = ? GROUP BY anio, mes ORDER BY anio DESC, mes DESC""",
            (tenant_id,),
        )
        rows = await cur.fetchall()
        return [dict(r) for r in rows]
    finally:
        await conn.close()


async def buscar_archivos(tenant_id: str, query: str, limit: int = 20) -> list[dict]:
    """Búsqueda full-text (FTS5) AISLADA por tenant.

    El índice FTS5 no tiene tenant_id, así que se filtra cruzando con la tabla
    archivos (que sí está aislada). El texto devuelto es SOLO datos de ese tenant.
    """
    conn = await get_db()
    try:
        # FTS5: término con prefijo para matches parciales
        termino = " ".join(f'"{w}"*' for w in query.split() if w)
        cur = await conn.execute(
            """SELECT a.* FROM archivos_fts_v2 f
            JOIN archivos a ON a.id = f.archivo_id
            WHERE a.tenant_id = ? AND archivos_fts_v2 MATCH ?
            ORDER BY bm25(archivos_fts_v2) LIMIT ?""",
            (tenant_id, termino, limit),
        )
        rows = await cur.fetchall()
        return [dict(r) for r in rows]
    except Exception:
        # FTS5 puede fallar con queries extrañas; devolver vacío
        return []
    finally:
        await conn.close()


# ---------------------------------------------------------------------------
# SEGURIDAD (Fase E): intentos de login, auditoría, 2FA
# ---------------------------------------------------------------------------

async def registrar_intento_login(email: str, exito: bool, ip: str | None = None) -> None:
    import time
    conn = await get_db()
    try:
        await conn.execute(
            "INSERT INTO intentos_login (id, email, ip, exito, created_at, created_ts) VALUES (?,?,?,?,?,?)",
            (_new_id(), email.strip().lower(), ip, 1 if exito else 0, _now(), time.time()),
        )
        await conn.commit()
    finally:
        await conn.close()


async def contar_intentos_fallidos(email: str, ventana_min: int = 15) -> int:
    """Cuenta intentos fallidos de un email en la última ventana (para bloquear)."""
    import time
    conn = await get_db()
    try:
        # Timestamps numéricos (epoch) para comparar de forma robusta
        limite = time.time() - (ventana_min * 60)
        cur = await conn.execute(
            "SELECT COUNT(*) c FROM intentos_login WHERE email = ? AND exito = 0 AND created_ts >= ?",
            (email.strip().lower(), limite),
        )
        row = await cur.fetchone()
        return row["c"] if row else 0
    finally:
        await conn.close()


async def auditar_seguridad(tipo: str, detalle: str, tenant_id: str | None = None,
                            usuario: str | None = None, ip: str | None = None,
                            severidad: str = "info") -> None:
    conn = await get_db()
    try:
        await conn.execute(
            """INSERT INTO audit_seguridad (id, tipo, detalle, tenant_id, usuario, ip, severidad, created_at)
            VALUES (?,?,?,?,?,?,?,?)""",
            (_new_id(), tipo, detalle, tenant_id, usuario, ip, severidad, _now()),
        )
        await conn.commit()
    finally:
        await conn.close()


async def list_audit_seguridad(tipo: str | None = None, severidad: str | None = None,
                               limit: int = 200) -> list[dict]:
    conn = await get_db()
    try:
        where, params = [], []
        if tipo:
            where.append("tipo = ?"); params.append(tipo)
        if severidad:
            where.append("severidad = ?"); params.append(severidad)
        sql = "SELECT * FROM audit_seguridad"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        cur = await conn.execute(sql, params)
        rows = await cur.fetchall()
        return [dict(r) for r in rows]
    finally:
        await conn.close()


async def activar_tfa(usuario_id: str, secret: str, recovery_codes: list[str]) -> None:
    import json
    conn = await get_db()
    try:
        await conn.execute(
            """UPDATE usuarios SET tfa_secret = ?, tfa_activado = 1, recovery_codes = ?, updated_at = ?
            WHERE id = ?""",
            (secret, json.dumps(recovery_codes), _now(), usuario_id),
        )
        await conn.commit()
    finally:
        await conn.close()


async def desactivar_tfa(usuario_id: str) -> None:
    conn = await get_db()
    try:
        await conn.execute(
            """UPDATE usuarios SET tfa_activado = 0, recovery_codes = '[]', updated_at = ?
            WHERE id = ?""",
            (_now(), usuario_id),
        )
        await conn.commit()
    finally:
        await conn.close()


async def bloquear_usuario(usuario_id: str, bloquear: bool = True) -> None:
    conn = await get_db()
    try:
        await conn.execute(
            "UPDATE usuarios SET bloqueado = ?, updated_at = ? WHERE id = ?",
            (1 if bloquear else 0, _now(), usuario_id),
        )
        if not bloquear:
            # Al desbloquear, limpiar intentos fallidos recientes del email
            cur = await conn.execute("SELECT email FROM usuarios WHERE id = ?", (usuario_id,))
            row = await cur.fetchone()
            if row:
                await conn.execute("DELETE FROM intentos_login WHERE email = ?", (row["email"],))
        await conn.commit()
    finally:
        await conn.close()


async def registrar_intentos_2fa(usuario_id: str, intentos: int) -> None:
    conn = await get_db()
    try:
        await conn.execute(
            "UPDATE usuarios SET intentos_fallidos = ?, ultimo_intento = ?, updated_at = ? WHERE id = ?",
            (intentos, _now(), _now(), usuario_id),
        )
        await conn.commit()
    finally:
        await conn.close()


# ---------------------------------------------------------------------------
# FACTURAS + VALIDACIÓN (Fase C)
# ---------------------------------------------------------------------------

async def crear_factura(
    tenant_id: str,
    datos: dict,
    creado_por: str | None = None,
    archivo_original: str | None = None,
) -> str:
    """Crea una factura en estado pendiente de validación."""
    conn = await get_db()
    try:
        now = _now()
        fid = _new_id()
        await conn.execute(
            """INSERT INTO facturas
            (id, tenant_id, emisor, nif_emisor, fecha_factura, numero, concepto,
             base, iva, total, tipo, estado, archivo_original, creado_por, created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                fid, tenant_id,
                datos.get("emisor"), datos.get("nif_emisor"),
                datos.get("fecha_factura"), datos.get("numero"), datos.get("concepto"),
                datos.get("base"), datos.get("iva"), datos.get("total"),
                datos.get("tipo", "recibida"), "pendiente_validacion",
                archivo_original, creado_por, now,
            ),
        )
        await conn.commit()
        return fid
    finally:
        await conn.close()


async def list_facturas(tenant_id: str, estado: str | None = None) -> list[dict]:
    conn = await get_db()
    try:
        if estado:
            cur = await conn.execute(
                "SELECT * FROM facturas WHERE tenant_id = ? AND estado = ? ORDER BY created_at DESC",
                (tenant_id, estado),
            )
        else:
            cur = await conn.execute(
                "SELECT * FROM facturas WHERE tenant_id = ? ORDER BY created_at DESC",
                (tenant_id,),
            )
        rows = await cur.fetchall()
        return [dict(r) for r in rows]
    finally:
        await conn.close()


async def validar_factura(factura_id: str, tenant_id: str, usuario: str, cambios: dict | None = None) -> None:
    """Valida una factura pendiente: pasa a validada y registra el log."""
    conn = await get_db()
    try:
        now = _now()
        # Actualizar campos corregidos por el cliente si los hay
        if cambios:
            sets, params = [], []
            for campo, valor in cambios.items():
                if campo in ("emisor", "nif_emisor", "fecha_factura", "numero", "concepto",
                             "base", "iva", "total"):
                    sets.append(f"{campo} = ?")
                    params.append(valor)
            if sets:
                params.append(factura_id)
                await conn.execute(f"UPDATE facturas SET {', '.join(sets)} WHERE id = ?", params)

        await conn.execute(
            "UPDATE facturas SET estado = 'validada', validado_por = ?, validado_en = ? WHERE id = ? AND tenant_id = ?",
            (usuario, now, factura_id, tenant_id),
        )
        await conn.execute(
            """INSERT INTO log_validaciones (id, tenant_id, factura_id, accion, detalle, usuario, created_at)
            VALUES (?,?,?,?,?,?,?)""",
            (_new_id(), tenant_id, factura_id, "validada",
             f"Validada por {usuario}" + (f" con correcciones: {cambios}" if cambios else ""),
             usuario, now),
        )
        await conn.commit()
    finally:
        await conn.close()


async def list_log_validaciones(tenant_id: str, limit: int = 100) -> list[dict]:
    conn = await get_db()
    try:
        cur = await conn.execute(
            "SELECT * FROM log_validaciones WHERE tenant_id = ? ORDER BY created_at DESC LIMIT ?",
            (tenant_id, limit),
        )
        rows = await cur.fetchall()
        return [dict(r) for r in rows]
    finally:
        await conn.close()


async def exportar_excel_empresa(tenant_id: str) -> bytes:
    """Genera el Excel de la empresa: hoja principal + hoja del mes + hoja log.

    Devuelve los bytes del .xlsx listos para descargar.
    """
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill

    empresa = await get_empresa(tenant_id)
    facturas = await list_facturas(tenant_id)
    log = await list_log_validaciones(tenant_id)

    wb = Workbook()

    # --- Hoja principal: facturas ---
    ws = wb.active
    ws.title = "Facturas"
    header = ["Emisor", "NIF", "Fecha", "Número", "Concepto", "Base", "IVA", "Total", "Estado"]
    ws.append(header)
    for c in ws[1]:
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="1f2937")
    for f in facturas:
        ws.append([
            f.get("emisor"), f.get("nif_emisor"), f.get("fecha_factura"),
            f.get("numero"), f.get("concepto"), f.get("base"),
            f.get("iva"), f.get("total"), f.get("estado"),
        ])
    for col, width in zip("ABCDEFGHI", [30, 14, 12, 12, 40, 12, 12, 12, 18]):
        ws.column_dimensions[col].width = width

    # --- Hoja de log ---
    ws2 = wb.create_sheet("Log validaciones")
    ws2.append(["Fecha", "Factura", "Acción", "Detalle", "Usuario"])
    for c in ws2[1]:
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="4d56b0")
    for l in log:
        ws2.append([l.get("created_at"), l.get("factura_id"), l.get("accion"),
                    l.get("detalle"), l.get("usuario")])
    for col, width in zip("ABCDE", [24, 14, 14, 60, 20]):
        ws2.column_dimensions[col].width = width

    # --- Hoja resumen empresa ---
    ws3 = wb.create_sheet("Empresa")
    ws3.append(["Campo", "Valor"])
    for k, v in [
        ("Empresa", empresa.get("nombre") if empresa else ""),
        ("NIF", empresa.get("nif") if empresa else ""),
        ("Régimen IVA", empresa.get("regimen_iva") if empresa else ""),
        ("Municipio", empresa.get("municipio") if empresa else ""),
        ("Facturas", len(facturas)),
        ("Validadas", sum(1 for f in facturas if f.get("estado") == "validada")),
        ("Pendientes", sum(1 for f in facturas if f.get("estado") != "validada")),
    ]:
        ws3.append([k, v])
    for col, width in zip("AB", [20, 40]):
        ws3.column_dimensions[col].width = width

    import io
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.read()
