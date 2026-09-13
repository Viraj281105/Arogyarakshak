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
COPY packages/ /app/packages/
RUN pip install --no-cache-dir -c constraints-cpu.txt \
    -e /app/packages/kadi \
    -e /app/packages/billnyay \
    -e /app/packages/schemesetu \
    -e /app/packages/dawacheck \
    -e /app/packages/daavisetu \
    -e /app/packages/bimanyay

# Copy app code
COPY apps/api/app/ /app/app/

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
