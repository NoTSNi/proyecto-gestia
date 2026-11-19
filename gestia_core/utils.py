"""GESTIA Utils - Common utilities."""

from __future__ import annotations

import hashlib
import mimetypes
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import BinaryIO
from uuid import UUID


# --------------------------------------------
# HASH / IDENTIFIERS
# --------------------------------------------

def generate_uuid() -> str:
    return str(uuid.uuid4())


def validate_uuid(value: str) -> bool:
    try:
        UUID(value)
        return True
    except ValueError:
        return False


def sha256_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(filepath: Path | str) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_stream(stream: BinaryIO) -> str:
    h = hashlib.sha256()
    for chunk in iter(lambda: stream.read(8192), b""):
        h.update(chunk)
    return h.hexdigest()


# --------------------------------------------
# FILE / MIME
# --------------------------------------------

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/tiff",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "text/csv",
    "application/xml",
    "text/xml",
    "application/zip",
}

MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB


def validate_file_type(content_type: str, filename: str) -> tuple[bool, str | None]:
    """Validate file type by MIME and extension."""
    # Check MIME
    if content_type not in ALLOWED_MIME_TYPES:
        return False, f"MIME type {content_type} not allowed"

    # Check extension matches
    ext = Path(filename).suffix.lower()
    mime_from_ext = mimetypes.guess_type(filename)[0]
    if mime_from_ext and mime_from_ext != content_type:
        return False, f"Extension {ext} doesn't match MIME {content_type}"

    return True, None


def validate_file_size(size_bytes: int) -> tuple[bool, str | None]:
    if size_bytes > MAX_FILE_SIZE:
        return False, f"File size {size_bytes} exceeds max {MAX_FILE_SIZE}"
    return True, None


# --------------------------------------------
# NIF / CIF VALIDATION (ESPAÑA)
# --------------------------------------------

NIF_REGEX = re.compile(r"^[0-9]{8}[A-Z]$")
CIF_REGEX = re.compile(r"^[A-W][0-9]{7}[0-9A-J]$")
NIE_REGEX = re.compile(r"^[XYZ][0-9]{7}[A-Z]$")

NIF_CONTROL = "TRWAGMYFPDXBNJZSQVHLCKE"


def validate_nif(nif: str) -> bool:
    """Validate Spanish NIF/CIF/NIE."""
    nif = nif.upper().strip()

    # NIF (persona física)
    if NIF_REGEX.match(nif):
        numero = int(nif[:8])
        letra = nif[8]
        return NIF_CONTROL[numero % 23] == letra

    # NIE (extranjeros)
    if NIE_REGEX.match(nif):
        # Convertir X/Y/Z a 0/1/2
        first = nif[0]
        if first == "X":
            nif_num = "0" + nif[1:8]
        elif first == "Y":
            nif_num = "1" + nif[1:8]
        elif first == "Z":
            nif_num = "2" + nif[1:8]
        else:
            return False
        numero = int(nif_num)
        letra = nif[8]
        return NIF_CONTROL[numero % 23] == letra

    # CIF (persona jurídica)
    if CIF_REGEX.match(nif):
        return validate_cif(nif)

    return False


def validate_cif(cif: str) -> bool:
    """Validate Spanish CIF."""
    cif = cif.upper()
    letra = cif[0]
    numeros = cif[1:8]
    control = cif[8]

    if not numeros.isdigit():
        return False

    # Algoritmo CIF
    suma = 0
    for i, digito in enumerate(numeros):
        d = int(digito)
        if i % 2 == 0:  # posiciones pares (0-indexed)
            d = d * 2
            if d > 9:
                d = d - 9
        suma += d

    control_calculado = (10 - (suma % 10)) % 10
    control_letra = "JABCDEFGHI"[control_calculado]

    if control.isdigit():
        return int(control) == control_calculado
    else:
        return control == control_letra


# --------------------------------------------
# DATE / TIME
# --------------------------------------------

def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def parse_flexible_date(date_str: str) -> datetime | None:
    """Parse date from multiple formats."""
    formats = [
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%Y/%m/%d",
        "%d.%m.%Y",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S%z",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    return None


def get_quarter(month: int) -> int:
    return (month - 1) // 3 + 1


def quarter_dates(year: int, quarter: int) -> tuple[datetime, datetime]:
    """Return start and end dates for a quarter."""
    start_month = (quarter - 1) * 3 + 1
    end_month = start_month + 2
    start = datetime(year, start_month, 1, tzinfo=timezone.utc)
    if end_month == 12:
        end = datetime(year, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
    else:
        end = datetime(year, end_month + 1, 1, tzinfo=timezone.utc)
        end = end.replace(day=1) - timedelta(seconds=1)
    return start, end


from datetime import timedelta


# --------------------------------------------
# PAGINATION
# --------------------------------------------

def paginate(
    items: list,
    page: int = 1,
    per_page: int = 20,
    max_per_page: int = 100,
) -> dict:
    """Paginate a list of items."""
    per_page = min(per_page, max_per_page)
    page = max(page, 1)
    total = len(items)
    total_pages = (total + per_page - 1) // per_page
    start = (page - 1) * per_page
    end = start + per_page
    return {
        "data": items[start:end],
        "meta": {
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
        },
        "links": {
            "self": f"?page={page}&per_page={per_page}",
            "next": f"?page={page+1}&per_page={per_page}" if page < total_pages else None,
            "prev": f"?page={page-1}&per_page={per_page}" if page > 1 else None,
            "last": f"?page={total_pages}&per_page={per_page}",
        },
    }


# --------------------------------------------
# SANITIZATION
# --------------------------------------------

def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe storage."""
    # Remove path traversal
    filename = Path(filename).name
    # Keep only safe chars
    filename = re.sub(r"[^a-zA-Z0-9._\- ]", "_", filename)
    # Limit length
    if len(filename) > 255:
        name, ext = Path(filename).stem, Path(filename).suffix
        filename = name[:255 - len(ext)] + ext
    return filename


def mask_sensitive(data: dict, sensitive_keys: set[str] | None = None) -> dict:
    """Mask sensitive fields in dict for logging."""
    if sensitive_keys is None:
        sensitive_keys = {
            "password", "password_hash", "secret", "token", "api_key",
            "private_key", "certificado", "nif", "cif", "iban",
            "tarjeta", "cvv", "pin", "mfa_secret",
        }
    result = {}
    for k, v in data.items():
        if k.lower() in sensitive_keys:
            result[k] = "***MASKED***"
        elif isinstance(v, dict):
            result[k] = mask_sensitive(v, sensitive_keys)
        elif isinstance(v, list):
            result[k] = [mask_sensitive(i, sensitive_keys) if isinstance(i, dict) else i for i in v]
        else:
            result[k] = v
    return result