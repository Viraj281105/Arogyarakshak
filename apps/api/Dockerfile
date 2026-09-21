FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

COPY apps/api/requirements.txt apps/api/constraints-cpu.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy and install local packages. Kadi pulls EasyOCR, which transitively depends on
# torch/torchvision; -c constraints-cpu.txt pins those to the CPU-only build (see that
# file for why — EasyOCR always runs with gpu=False in this codebase).
# kadi[semantic] adds sentence-transformers for the optional IndicSBERT entity-resolution
# signal (#30). It stays off unless KADI_SEMANTIC_MATCHING=true; the model itself is not
# baked into the image and downloads from the Hugging Face Hub on first use.
COPY packages/ /app/packages/
RUN pip install --no-cache-dir -c constraints-cpu.txt \
    -e "/app/packages/kadi[semantic]" \
    -e /app/packages/billnyay \
    -e /app/packages/schemesetu \
    -e /app/packages/dawacheck \
    -e /app/packages/daavisetu \
    -e /app/packages/bimanyay

# Unprivileged runtime user. Code and site-packages stay root-owned (read-only to the
# app); only /home/app is writable, which is where the Hugging Face cache (HF_HOME) and
# EasyOCR (~/.EasyOCR) download model weights at runtime. HF_HOME is created here so an
# empty named volume mounted over it (docker-compose.yml) inherits app's ownership.
ENV HF_HOME=/home/app/.cache/huggingface
RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --home-dir /home/app --create-home \
       --shell /usr/sbin/nologin app \
    && mkdir -p "$HF_HOME" \
    && chown -R app:app /home/app

# Copy app code
COPY apps/api/app/ /app/app/

# Copy test configuration
COPY pytest.ini apps/api/conftest.py /app/

# Copy API tests
COPY apps/api/tests/ /app/tests/

RUN mkdir -p /app/testdata && \
    chown -R app:app /app/testdata

USER app

EXPOSE 8000

# Production default: no --reload. docker-compose.yml overrides this for local dev.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
