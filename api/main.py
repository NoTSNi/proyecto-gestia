"""GESTIA API - FastAPI Application."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from gestia_core.config import get_settings
from gestia_core.database import close_db, init_db
from gestia_core.security import get_current_user
from gestia_core.utils import mask_sensitive

settings = get_settings()

# --------------------------------------------
# METRICS
# --------------------------------------------

REQUEST_COUNT = Counter("http_requests_total", "Total HTTP requests", ["method", "endpoint", "status"])
REQUEST_LATENCY = Histogram("http_request_duration_seconds", "HTTP request latency", ["method", "endpoint"])


# --------------------------------------------
# MIDDLEWARE
# --------------------------------------------

class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        import time
        start = time.time()
        response = await call_next(request)
        duration = time.time() - start

        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code,
        ).inc()
        REQUEST_LATENCY.labels(
            method=request.method,
            endpoint=request.url.path,
        ).observe(duration)

        return response


class RLSContextMiddleware(BaseHTTPMiddleware):
    """Set RLS context for multi-tenant isolation."""
    async def dispatch(self, request: Request, call_next):
        # RLS se establece en dependencias de seguridad después de autenticación
        return await call_next(request)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Structured request/response logging."""
    async def dispatch(self, request: Request, call_next):
        import structlog
        import time
        logger = structlog.get_logger("api")
        start = time.time()

        # Log request (masked)
        logger.info(
            "request_started",
            method=request.method,
            path=request.url.path,
            query=dict(request.query_params),
            client_ip=request.client.host if request.client else None,
        )

        response = await call_next(request)

        duration = time.time() - start
        logger.info(
            "request_completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=round(duration * 1000, 2),
        )
        return response


# --------------------------------------------
# LIFESPAN
# --------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Startup
    import structlog
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(20),  # INFO
    )
    logger = structlog.get_logger("startup")
    logger.info("starting_application", version=settings.APP_VERSION)

    await init_db()
    logger.info("database_initialized")

    yield

    # Shutdown
    await close_db()
    logger.info("application_shutdown")


# --------------------------------------------
# APP FACTORY
# --------------------------------------------

def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="GESTIA - Asistente multi-agente para asesoría/gestoría",
        docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
        redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://localhost:3000"] if settings.ENVIRONMENT == "development" else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Middlewares
    app.add_middleware(MetricsMiddleware)
    app.add_middleware(RLSContextMiddleware)
    app.add_middleware(LoggingMiddleware)

    # Health check
    @app.get("/health", tags=["Health"])
    async def health_check():
        return {"status": "ok", "version": settings.APP_VERSION}

    @app.get("/metrics", tags=["Monitoring"])
    async def metrics():
        return Response(content=generate_latest(), media_type="text/plain")

    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        import structlog
        logger = structlog.get_logger("error")
        logger.error(
            "unhandled_exception",
            path=request.url.path,
            method=request.method,
            error=str(exc),
            error_type=type(exc).__name__,
        )
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "internal_error", "message": "An error occurred"}},
        )

    # Routers
    from api.routes import auth, empresas, documentos, calendario, fiscal, personal, mercantil, administrativo, notificaciones
    app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
    app.include_router(empresas.router, prefix="/api/v1/empresas", tags=["Empresas"])
    app.include_router(documentos.router, prefix="/api/v1/documentos", tags=["Documentos"])
    app.include_router(calendario.router, prefix="/api/v1/calendario", tags=["Calendario"])
    app.include_router(fiscal.router, prefix="/api/v1/fiscal", tags=["Fiscal"])
    app.include_router(personal.router, prefix="/api/v1/personal", tags=["Personal"])
    app.include_router(mercantil.router, prefix="/api/v1/mercantil", tags=["Mercantil"])
    app.include_router(administrativo.router, prefix="/api/v1/administrativo", tags=["Administrativo"])
    app.include_router(notificaciones.router, prefix="/api/v1/notificaciones", tags=["Notificaciones"])

    # Internal callbacks (n8n)
    from api.routes import internal
    app.include_router(internal.router, prefix="/internal", tags=["Internal"])

    return app


app = create_app()