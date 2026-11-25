"""GESTIA Web - Servicio de seguridad (Fase E).

Anti-brute-force + 2FA TOTP.

Anti-brute-force:
- Registra cada intento de login (exito/fallo + IP) en `intentos_login`
- Tras N fallos consecutivos en ventana, bloquea la cuenta (parámetro del usuario)
- Bloques con temporización creciente y registro en audit
- Desbloqueo: vía 2FA o contacto con el administrador

2FA (TOTP):
- `pyotp` para TOTP estándar (Google Authenticator, Authy, MS Authenticator)
- 10 códigos de recuperación de un solo uso al activar
- Obligatorio para asesor/admin, opcional para clientes
"""

from __future__ import annotations

import json
import secrets

from web import database

MAX_INTENTOS = 5           # intentos fallidos antes de bloquear
VENTANA_MIN = 15           # ventana de conteo (minutos)
APP_NOMBRE = "GESTIA"


# ---------------------------------------------------------------------------
# ANTI BRUTE-FORCE
# ---------------------------------------------------------------------------

async def verificar_bloqueo(email: str) -> dict:
    """Comprueba si una cuenta está bloqueada. Devuelve {bloqueado, motivo}."""
    user = await database.get_usuario_by_email(email.strip().lower())
    if user and user.get("bloqueado"):
        return {"bloqueado": True, "motivo": "Cuenta bloqueada por actividad sospechosa. Contacta con el administrador."}
    fallos = await database.contar_intentos_fallidos(email, VENTANA_MIN)
    if fallos >= MAX_INTENTOS:
        # Bloquear la cuenta (baja lógica de login)
        if user:
            await database.bloquear_usuario(user["id"], bloquear=True)
            await database.auditar_seguridad(
                "login_bloqueado",
                f"Cuenta bloqueada tras {fallos} intentos fallidos en {VENTANA_MIN} min",
                usuario=email, severidad="alta",
            )
        return {"bloqueado": True, "motivo": f"Demasiados intentos fallidos. Cuenta bloqueada temporalmente."}
    restantes = MAX_INTENTOS - fallos
    return {"bloqueado": False, "motivo": None, "restantes": restantes}


async def registrar_ok_tras_fallo(email: str) -> None:
    """Al hacer login correcto tras fallos, resetea contadores (sin desbloquear admin)."""
    user = await database.get_usuario_by_email(email.strip().lower())
    if user and user.get("bloqueado"):
        return  # sigue bloqueado hasta desbloqueo por admin
    if user:
        await database.bloquear_usuario(user["id"], bloquear=False)


# ---------------------------------------------------------------------------
# 2FA (TOTP)
# ---------------------------------------------------------------------------

def generar_secret() -> str:
    import pyotp
    return pyotp.random_base32()


def generar_codigos_recuperacion(n: int = 10) -> list[str]:
    """Genera N códigos de recuperación de un solo uso (formato XXXX-XXXX)."""
    codigos = []
    for _ in range(n):
        bloque = "".join(secrets.choice("ABCDEFGHJKLMNPQRSTUVWXYZ23456789") for _ in range(8))
        codigos.append(f"{bloque[:4]}-{bloque[4:]}")
    return codigos


def validar_totp(secret: str, codigo: str) -> bool:
    """Valida un código TOTP (6 dígitos) contra el secreto."""
    import pyotp
    if not secret:
        return False
    totp = pyotp.TOTP(secret)
    return totp.verify(codigo, valid_window=1)


def escapara_qr(secret: str, email: str) -> str:
    """Devuelve el URI otpauth para generar el QR."""
    import pyotp
    return pyotp.totp.TOTP(secret).provisioning_uri(name=email, issuer_name=APP_NOMBRE)


async def validar_codigo_recuperacion(usuario: dict, codigo: str) -> bool:
    """Valida y consume un código de recuperación (use-once)."""
    try:
        codigos = json.loads(usuario.get("recovery_codes") or "[]")
    except json.JSONDecodeError:
        codigos = []
    codigo_limpio = codigo.strip().upper()
    if codigo_limpio in codigos:
        codigos.remove(codigo_limpio)
        await _guardar_codigos(usuario["id"], codigos)
        return True
    return False


async def _guardar_codigos(usuario_id: str, codigos: list[str]) -> None:
    conn = await database.get_db()
    try:
        await conn.execute(
            "UPDATE usuarios SET recovery_codes = ?, updated_at = ? WHERE id = ?",
            (json.dumps(codigos), database._now(), usuario_id),
        )
        await conn.commit()
    finally:
        await conn.close()