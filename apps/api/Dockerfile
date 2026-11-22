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

# OCR weights are baked in at BUILD time. The API builds its EasyOCR readers with
# download_enabled=False, so an upload can never trigger a network download (Wave 2, stream A).
# OCR_BAKE_LANGUAGES chooses what is downloaded now (network to the official EasyOCR release
# host, during the build only): `en` (default, ~100 MB: detector + English recogniser) or
# `en,hi,mr` (adds the ~215 MB Devanagari model). Running with OCR_LANGUAGES=hi,mr,en needs the
# Devanagari weights baked in, otherwise the parser reports "OCR models not installed".
# Both directories are created here so the read-only runtime user can use them.
ARG OCR_BAKE_LANGUAGES=en
COPY scripts/fetch_ocr_models.py /tmp/fetch_ocr_models.py
RUN mkdir -p /opt/easyocr/model /opt/easyocr/user_network \
    && if [ -n "$OCR_BAKE_LANGUAGES" ]; then \
         python /tmp/fetch_ocr_models.py --download --languages "$OCR_BAKE_LANGUAGES" --dest /opt/easyocr/model; \
       fi

# ── runtime ────────────────────────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/home/app/.cache/huggingface \
    EASYOCR_MODULE_PATH=/opt/easyocr

# Unprivileged runtime user. Code and site-packages stay root-owned (read-only to the
# app); only /home/app is writable, which is where the Hugging Face cache (HF_HOME)
# downloads its model at runtime. EasyOCR weights are NOT downloaded at runtime: they are
# baked into /opt/easyocr (read-only) at build time. HF_HOME is created here so an
# empty named volume mounted over it (docker-compose.yml) inherits app's ownership.
RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --home-dir /home/app --create-home \
       --shell /usr/sbin/nologin app \
    && mkdir -p "$HF_HOME" \
    && chown -R app:app /home/app

WORKDIR /app

COPY --from=build /opt/venv /opt/venv
COPY --from=build /app/packages /app/packages
COPY --from=build /opt/easyocr /opt/easyocr

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
