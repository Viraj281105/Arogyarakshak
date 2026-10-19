# syntax=docker/dockerfile:1
# ArogyaRakshak API image. Build context: the repository root (see docker-compose.yml).
#
# Two stages: `build` has the compiler toolchain and resolves every wheel into a virtual
# environment; `runtime` gets only that environment, the code and the migrations — no
# gcc, no headers, no pip cache.

# ── build ──────────────────────────────────────────────────────────────────────────────
FROM python:3.11-slim AS build

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Only for the rare dependency without a manylinux wheel; never reaches the runtime image.
RUN apt-get update && apt-get install -y --no-install-recommends gcc \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY apps/api/requirements.txt apps/api/constraints-cpu.txt /tmp/
RUN pip install -r /tmp/requirements.txt

# Domain packages are installed editable from /app/packages, which the runtime stage
# copies to the same path: billnyay/dawacheck/schemesetu read their reference data files
# (e.g. billnyay/data/cghs_rates.json) from the source tree, not from package data.
# Kadi pulls EasyOCR -> torch/torchvision; -c constraints-cpu.txt pins the CPU-only build
# (EasyOCR always runs with gpu=False). kadi[semantic] adds sentence-transformers for the
# optional IndicSBERT signal (#30), off unless KADI_SEMANTIC_MATCHING=true; the model is
# not baked in and downloads from the Hugging Face Hub on first use.
COPY packages/ /app/packages/
RUN pip install -c /tmp/constraints-cpu.txt \
    -e "/app/packages/kadi[semantic]" \
    -e /app/packages/billnyay \
    -e /app/packages/schemesetu \
    -e /app/packages/dawacheck \
    -e /app/packages/daavisetu \
    -e /app/packages/bimanyay

# ── runtime ────────────────────────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/home/app/.cache/huggingface

# Unprivileged runtime user. Code and site-packages stay root-owned (read-only to the
# app); only /home/app is writable, which is where the Hugging Face cache (HF_HOME) and
# EasyOCR (~/.EasyOCR) download model weights at runtime. HF_HOME is created here so an
# empty named volume mounted over it (docker-compose.yml) inherits app's ownership.
RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --home-dir /home/app --create-home \
       --shell /usr/sbin/nologin app \
    && mkdir -p "$HF_HOME" \
    && chown -R app:app /home/app

WORKDIR /app

COPY --from=build /opt/venv /opt/venv
COPY --from=build /app/packages /app/packages

# Application code and its Alembic migrations (ADR-020). With the default
# SCHEMA_MANAGEMENT=migrate the API upgrades the database at start-up; with `none`, run
#   docker compose run --rm api alembic upgrade head
COPY apps/api/app/ /app/app/
COPY apps/api/alembic.ini /app/alembic.ini
COPY apps/api/migrations/ /app/migrations/

# Synthetic demo documents for the demo scenario loaders (POST /kadi/clinical-demo/
# scenarios/{A-E}). Every file is labelled SYNTHETIC; the loaders refuse to run unless
# CLINICAL_DEMO_MODE=true and APP_ENV is not "production" (app.config).
COPY demo/documents/ /app/demo/documents/

USER app

EXPOSE 8000

# Liveness only (no database): a database outage must not restart-loop the container.
HEALTHCHECK --interval=15s --timeout=5s --start-period=60s --retries=3 \
    CMD ["python", "-c", "import sys, urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health/live', timeout=3).status == 200 else 1)"]

# Production default: one process (ADR-019 — in-memory progress stream and rate limiter),
# no --reload, bounded graceful shutdown so in-flight requests can finish on SIGTERM.
# --no-access-log: uvicorn logs raw paths (case ids); app.observability logs route templates.
# docker-compose.yml overrides this for local dev.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--timeout-graceful-shutdown", "20", "--no-access-log"]
