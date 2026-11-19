"""GESTIA API Routes - Package exports."""

from api.routes import (
    auth,
    empresas,
    documentos,
    calendario,
    fiscal,
    personal,
    mercantil,
    administrativo,
    notificaciones,
    internal,
)

__all__ = [
    "auth",
    "empresas",
    "documentos",
    "calendario",
    "fiscal",
    "personal",
    "mercantil",
    "administrativo",
    "notificaciones",
    "internal",
]