# Multi-stage Dockerfile for GESTIA API
FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Development stage
FROM base AS development

ENV VENV_PATH="/opt/venv"
ENV PATH="${VENV_PATH}/bin:$PATH"

RUN pip install --upgrade pip && \
    pip install uv

COPY pyproject.toml uv.lock* README.md ./
RUN uv venv --seed ${VENV_PATH} && \
    ${VENV_PATH}/bin/pip install --no-cache-dir -e . && \
    ${VENV_PATH}/bin/pip install --no-cache-dir uvicorn[standard] watchfiles

COPY . .

EXPOSE 8000

CMD ["/opt/venv/bin/python", "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# Production builder
FROM base AS builder

RUN pip install --upgrade pip && \
    pip install uv

COPY pyproject.toml uv.lock* README.md ./
RUN uv sync --frozen --no-dev

# Production stage
FROM python:3.11-slim AS production

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Non-root user
RUN groupadd -r gestia && useradd -r -g gestia gestia

# Runtime deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder --chown=gestia:gestia /app/.venv .venv
COPY --from=builder --chown=gestia:gestia /app .

USER gestia

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]