# ArogyaRakshak API (`apps/api`)

The backend service for **ArogyaRakshak**, built with **FastAPI**, **SQLAlchemy 2.0 (async)**, and **pgvector**. Exposes unified REST endpoints and real-time Server-Sent Events (SSE) streams for document auditing, scheme eligibility, and medicine pricing.

---

## Features
- **Asynchronous Architecture**: Fully async request pipeline using `asyncpg` and `uvicorn`.
- **Server-Sent Events (SSE)**: Real-time progress updates for multi-agent reasoning chains via `/api/v1/kadi/cases/{case_id}/stream`.
- **Centralized Lifespan Management**: Automatic database schema synchronization on startup (`app/database.py`).
- **Bring-Your-Own-Document Handling**: Transient processing of multipart document uploads with zero persistent file retention.

---

## Directory Layout
```text
apps/api/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── endpoints/
│   │       │   ├── kadi.py          # Document intake, case session, SSE stream
│   │       │   ├── billnyay.py      # Hospital bill line-item audit
│   │       │   ├── daavisetu.py     # Cashless pre-auth claim generator
│   │       │   ├── schemesetu.py    # PMJAY / MJPJAY eligibility matching
│   │       │   └── dawacheck.py     # NPPA medicine price check
│   │       └── api.py               # Aggregates V1 sub-routers
│   ├── config.py                    # Pydantic Settings (GROQ_MODEL, DATABASE_URL)
│   ├── database.py                  # Async engine and session maker
│   ├── main.py                      # FastAPI app entrypoint, CORS & error handlers
│   └── models.py                    # SQLAlchemy ORM definitions
├── tests/
│   ├── conftest.py                  # Pytest fixtures and mock client
│   └── test_api.py                  # Integration tests across all endpoints
├── Dockerfile                       # Python 3.11 container definition
└── requirements.txt                 # Core backend dependencies
```

---

## Local Development

### Prerequisites
- Python 3.11+
- Running PostgreSQL container with pgvector (via `docker-compose up postgres -d` or local Postgres)

### Installation
```bash
# 1. Install requirements
pip install -r requirements.txt

# 2. Install monorepo packages in editable mode
pip install -e ../../packages/kadi
pip install -e ../../packages/billnyay
pip install -e ../../packages/daavisetu
pip install -e ../../packages/schemesetu
pip install -e ../../packages/dawacheck
pip install pytest pytest-asyncio aiosqlite httpx
```

### Running the Dev Server
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Interactive API documentation is accessible at:
- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

### Running Tests
```bash
python -m pytest tests/
```
