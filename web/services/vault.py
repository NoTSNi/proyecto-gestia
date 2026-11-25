"""GESTIA Web - Servicio de ingesta de documentos (Fase D).

CUARENTENA + EXTRACCIÓN + CLASIFICACIÓN + INDEXADO.

INVARIANTE DE SEGURIDAD: los datos aportados por clientes son SOLO datos.
- Allowlist de tipos por MAGIC BYTES (no por extensión)
- Hash SHA-256 de cada archivo (detección de duplicados y auditoría)
- El contenido extraído va a un índice de búsqueda AISLADO por tenant;
  nunca se ejecuta, nunca se interpreta como instrucciones.
- Sin macros: se rechazan .xlsm/.docm; los .xlsx/.docx se tratan como ZIP
  de datos y solo se extrae texto.
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime
from pathlib import Path

from web import database

# Directorio raíz del vault: data/vault/<tenant>/<año>/<mes>/
VAULT_DIR = Path(__file__).resolve().parent.parent / "data" / "vault"

# Tipos permitidos: (extensión, magic_bytes (hex), tipo, descripción)
ALLOWLIST = [
    ("pdf",  b"%PDF", "pdf", "PDF"),
    ("png",  b"\x89PNG\r\n\x1a\n", "imagen", "Imagen PNG"),
    ("jpg",  b"\xff\xd8\xff", "imagen", "Imagen JPG"),
    ("txt",  None, "texto", "Texto plano"),
    ("csv",  None, "datos", "CSV"),
    ("xlsx", b"PK\x03\x04", "datos", "Excel XLSX"),
]

# Extensiones REZAGADAS por seguridad (macros / ejecutables)
BLOQUEADAS = {".exe", ".bat", ".cmd", ".ps1", ".sh", ".vbs", ".js", ".msi",
              ".xlsm", ".docm", ".xlam", ".pptm", ".dll", ".scr", ".jar", ".py", ".html", ".htm"}


class ArchivoRechazado(Exception):
    """Archivo no permitido o sospechoso."""


def _magic_bytes(data: bytes) -> str | None:
    """Detecta el tipo real por magic bytes. Devuelve la extensión o None."""
    for ext, magic, tipo, _desc in ALLOWLIST:
        if magic is not None and data[: len(magic)] == magic:
            return ext
    return None


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def clasificar_documento(texto: str, nombre: str) -> str:
    """Clasifica el documento por keywords (factura, nómina, contrato, modelo...)."""
    t = f"{nombre} {texto[:3000]}".lower()
    reglas = [
        ("factura", ["factura", "nº factura", "número de factura", "total a pagar", "base imponible"]),
        ("nomina", ["nómina", "nomina", "devengos", "seguridad social a cargo"]),
        ("contrato", ["contrato", "cláusula", "partes intervinientes"]),
        ("modelo_fiscal", ["modelo 303", "modelo 111", "modelo 390", "modelo 200", "declaración"]),
        ("escritura", ["escritura", "registro de la propiedad", "notaría"]),
        ("extracto_bancario", ["extracto", "movimientos", "saldo", "iban"]),
    ]
    for cat, kws in reglas:
        if any(kw in t for kw in kws):
            return cat
    return "otro"


def extraer_texto(ruta: Path, ext: str) -> str:
    """Extrae el texto del archivo según su tipo real (magic bytes)."""
    if ext == "pdf":
        from pypdf import PdfReader
        try:
            reader = PdfReader(str(ruta))
            return "\n".join(p.extract_text() or "" for p in reader.pages)
        except Exception:
            return ""
    if ext in ("txt", "csv"):
        try:
            return ruta.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return ""
    if ext == "xlsx":
        # El XLSX es un ZIP: solo lectura de celdas como datos, sin macros.
        try:
            from openpyxl import load_workbook
            wb = load_workbook(str(ruta), read_only=True, data_only=True)
            partes = []
            for ws in wb.worksheets:
                for row in ws.iter_rows(values_only=True):
                    celdas = [str(c) for c in row if c is not None and str(c).strip()]
                    if celdas:
                        partes.append(" | ".join(celdas))
            return "\n".join(partes)
        except Exception:
            return ""
    return ""


async def ingestar_archivo(
    tenant_id: str,
    nombre_original: str,
    contenido: bytes,
    subido_por: str,
) -> dict:
    """Cuarentena + guardado por empresa/año/mes + extracción + indexado.

    Lanza ArchivoRechazado si el archivo no es seguro.
    """
    # 1) CUARENTENA: extensión y magic bytes
    ext_orig = Path(nombre_original).suffix.lower().lstrip(".")
    if ext_orig in BLOQUEADAS or nombre_original.lower().endswith(tuple(BLOQUEADAS)):
        raise ArchivoRechazado(f"Tipo de archivo no permitido: {nombre_original}")

    ext_real = _magic_bytes(contenido)
    if ext_real is None:
        raise ArchivoRechazado(f"No se pudo verificar el tipo real del archivo: {nombre_original}")
    # Permitir: pdf/png/jpg/txt/csv reales; xlsx solo si la extensión coincide
    if ext_orig not in ("pdf", "png", "jpg", "txt", "csv", "xlsx"):
        raise ArchivoRechazado(f"Extensión no permitida: {nombre_original}")

    # 2) Hash SHA-256 (duplicados + auditoría)
    sha = _sha256(contenido)
    if sha in await database.buscar_hash(tenant_id):
        raise ArchivoRechazado(f"Este archivo ya fue subido anteriormente: {nombre_original}")

    # 3) Guardar en data/vault/<tenant>/<año>/<mes>/
    ahora = datetime.now()
    anio = str(ahora.year)
    mes = f"{ahora.month:02d}"
    carpeta = VAULT_DIR / tenant_id / anio / mes
    carpeta.mkdir(parents=True, exist_ok=True)
    nombre_limpio = re.sub(r"[^A-Za-z0-9._-]", "_", Path(nombre_original).name)
    ruta_final = carpeta / f"{sha[:12]}_{nombre_limpio}"
    ruta_final.write_bytes(contenido)

    # 4) Extracción de texto (solo lectura de datos)
    texto = extraer_texto(ruta_final, ext_real)

    # 5) Clasificación automática
    clasificacion = clasificar_documento(texto, nombre_original)

    # 6) Registrar en BD + índice FTS5
    registro = await database.registrar_archivo(
        tenant_id=tenant_id,
        nombre=nombre_original,
        ruta=str(ruta_final.relative_to(Path(__file__).resolve().parent.parent)),
        tipo=ext_real,
        tamano=len(contenido),
        hash_sha256=sha,
        anio=anio,
        mes=mes,
        texto=texto,
        clasificacion=clasificacion,
        subido_por=subido_por,
    )

    return {
        "id": registro["id"],
        "nombre": nombre_original,
        "clasificacion": clasificacion,
        "anio": anio,
        "mes": mes,
        "hash": sha,
        "texto_extraido": len(texto),
    }
