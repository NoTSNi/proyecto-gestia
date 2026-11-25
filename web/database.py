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
    created_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL,
    FOREIGN KEY (tenant_id) REFERENCES empresas(id)
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


async def crear_empresa(data: dict) -> None:
    conn = await get_db()
    try:
        now = _now()
        await conn.execute(
            """INSERT INTO empresas
            (id, nif, nombre, nombre_comercial, regimen_iva, periodicidad_iva,
             cnae, estado, direccion, municipio, provincia, metadata_json, created_at, updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                _new_id(), data.get("nif", ""), data.get("nombre", ""),
                data.get("nombre_comercial"), data.get("regimen_iva", "general"),
                data.get("periodicidad_iva", "trimestral"), data.get("cnae"),
                data.get("estado", "activa"), data.get("direccion"),
                data.get("municipio"), data.get("provincia"), "{}", now, now,
            ),
        )
        await conn.commit()
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
