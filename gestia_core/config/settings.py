"""GESTIA Core Configuration.

Centralized settings using Pydantic Settings v2.
All configuration via environment variables with validation.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --------------------------------------------
    # APP
    # --------------------------------------------
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    LOG_LEVEL: str = "INFO"
    APP_NAME: str = "GESTIA"
    APP_VERSION: str = "0.1.0"

    # --------------------------------------------
    # DATABASE
    # --------------------------------------------
    POSTGRES_USER: str = "gestia"
    POSTGRES_PASSWORD: str = "changeme"
    POSTGRES_DB: str = "gestia"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432

    @property
    def DATABASE_URL(self) -> PostgresDsn:
        return PostgresDsn.build(
            scheme="postgresql+asyncpg",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_HOST,
            port=self.POSTGRES_PORT,
            path=self.POSTGRES_DB,
        )

    # --------------------------------------------
    # REDIS
    # --------------------------------------------
    REDIS_URL: RedisDsn = "redis://localhost:6379/0"

    # --------------------------------------------
    # MINIO / S3
    # --------------------------------------------
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "gestia"
    MINIO_SECRET_KEY: str = "changeme123"
    MINIO_BUCKET: str = "gestia-documents"
    MINIO_SECURE: bool = False

    @property
    def MINIO_URL(self) -> str:
        scheme = "https" if self.MINIO_SECURE else "http"
        return f"{scheme}://{self.MINIO_ENDPOINT}"

    # --------------------------------------------
    # N8N
    # --------------------------------------------
    N8N_WEBHOOK_BASE_URL: str = "http://localhost:5678/webhook/gestia"
    N8N_API_KEY: str | None = None

    # --------------------------------------------
    # AUTH / JWT
    # --------------------------------------------
    JWT_SECRET_KEY: str = Field(..., min_length=32)
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # MFA / Passkeys
    MFA_ISSUER: str = "GESTIA"
    WEBAUTHN_RP_ID: str = "localhost"
    WEBAUTHN_RP_NAME: str = "GESTIA"

    # --------------------------------------------
    # LLM PROVIDERS
    # --------------------------------------------
    OPENROUTER_API_KEY: str | None = None
    OPENAI_API_KEY: str | None = None
    GEMINI_API_KEY: str | None = None
    DEEPSEEK_API_KEY: str | None = None

    DEFAULT_LLM_MODEL: str = "deepseek/deepseek-chat"
    DEFAULT_LLM_PROVIDER: Literal["openrouter", "openai", "google", "deepseek"] = "openrouter"
    EMBEDDING_MODEL: str = "text-embedding-3-small"

    # Modelos gratuitos (con suffix -free)
    FREE_MODELS: str = "solar-pro4-free,gemini-3.6-flash-free,deepseek-v4-flash-free,qwen3.8-flash-next,glm-5.3-flash,gemma-4"

    @property
    def free_models_list(self) -> list[str]:
        return [m.strip() for m in self.FREE_MODELS.split(",") if m.strip()]

    # --------------------------------------------
    # OCR / DOCUMENT PROCESSING
    # --------------------------------------------
    DOCLING_ENABLED: bool = True
    DOCLING_DEVICE: Literal["cpu", "cuda"] = "cpu"
    OCR_LANGUAGES: str = "es,en"

    AZURE_DOC_INTEL_ENDPOINT: str | None = None
    AZURE_DOC_INTEL_KEY: str | None = None

    # --------------------------------------------
    # EMAIL
    # --------------------------------------------
    SMTP_HOST: str = "smtp.sendgrid.net"
    SMTP_PORT: int = 587
    SMTP_USER: str = "apikey"
    SMTP_PASSWORD: str | None = None
    EMAIL_FROM: str = "noreply@gestia.app"
    EMAIL_FROM_NAME: str = "GESTIA"

    # Inbound email (IMAP)
    IMAP_HOST: str = "imap.gmail.com"
    IMAP_PORT: int = 993
    IMAP_USER: str | None = None
    IMAP_PASSWORD: str | None = None
    IMAP_OAUTH2: bool = False

    # --------------------------------------------
    # WHATSAPP BUSINESS
    # --------------------------------------------
    WHATSAPP_ENABLED: bool = False
    WHATSAPP_PROVIDER: Literal["360dialog", "meta", "twilio"] = "360dialog"
    WHATSAPP_API_KEY: str | None = None
    WHATSAPP_PHONE_NUMBER_ID: str | None = None
    WHATSAPP_WEBHOOK_VERIFY_TOKEN: str | None = None

    # --------------------------------------------
    # EXTERNAL APIs
    # --------------------------------------------
    AEAT_CERT_PATH: str | None = None
    AEAT_CERT_PASSWORD: str | None = None
    SS_RED_SISTEMA_API_KEY: str | None = None
    SS_RED_SISTEMA_USER: str | None = None
    SS_RED_SISTEMA_PASS: str | None = None

    # --------------------------------------------
    # MONITORING
    # --------------------------------------------
    OTEL_EXPORTER_OTLP_ENDPOINT: str | None = None
    PROMETHEUS_METRICS_PORT: int = 9090

    # --------------------------------------------
    # FEATURE FLAGS
    # --------------------------------------------
    FEATURE_OCR: bool = True
    FEATURE_RAG: bool = True
    FEATURE_WHATSAPP: bool = False
    FEATURE_API_SYNC: bool = True
    FEATURE_WEB_UI: bool = True


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance for dependency injection."""
    return Settings()