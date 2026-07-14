# ArogyaRakshak

Patient-facing bill audit, scheme eligibility & medicine pricing platform — English/Hindi/Marathi.

**B.E. Computer Engineering FYP | PES Modern College of Engineering, Pune | SPPU 2019 Pattern**

## Modules

| Module | Purpose |
|---|---|
| **BillNyay** | Hospital bill audit + IRDAI appeal generation |
| **SchemeSetu** | PMJAY/MJPJAY scheme eligibility reasoning |
| **DawaCheck** | Medicine pricing vs NPPA Schedule-I ceiling prices |
| **Kadi** | Shared context layer — extraction, entity resolution, orchestration |

## Quick Start

```bash
# 1. Copy environment template
cp .env.example .env

# 2. Build and start all services
docker-compose up --build

# 3. Verify
curl http://localhost:8000/health    # → {"status":"ok"}
# Open http://localhost:3000         # → Next.js frontend
```

### Services

| Service | URL | Description |
|---|---|---|
| API | http://localhost:8000 | FastAPI backend |
| Web | http://localhost:3000 | Next.js 15 frontend |
| PostgreSQL | localhost:5432 | PostgreSQL 16 + pgvector |

## Documentation

- [Technical Documentation](docs/ArogyaRakshak_Technical_Documentation.md)
- [Task Backlog](docs/ArogyaRakshak_Task_Backlog.md)

## Stack

FastAPI · Next.js 15 · PostgreSQL/pgvector · FAISS · Groq
