# Agent Configuration & Operational Manual — ArogyaRakshak

**Project Name:** "ArogyaRakshak (आरोग्यरक्षक)"  
**Stack:** FastAPI + Next.js (App Router) + PostgreSQL/pgvector + FAISS + Groq API  
**Environment:** Monorepo (`apps/`, `packages/`, `data/`, `docs/`)  

---

## 0. Living Project Context System & Mandatory Agent Lifecycle

Every AI coding agent operating in this repository must treat [`PROJECT_CONTEXT.md`](PROJECT_CONTEXT.md) as the repository's **living engineering memory and operational state**.

### Mandatory Agent Lifecycle
```text
1. READ AGENTS.md & PROJECT_CONTEXT.md
        ↓
2. Inspect relevant source code (Code is ultimate truth if docs conflict)
        ↓
3. Understand current state, assigned task & constraints
        ↓
4. Implement focused change (preserve architecture, minimal targeted diff)
        ↓
5. Test & validate (pytest, npm lint, endpoint verification)
        ↓
6. UPDATE PROJECT_CONTEXT.md (Current Work, Recent Changes, Next Tasks, Handoff)
        ↓
7. UPDATE RELEVANT DOCUMENTATION (Docs as code)
        ↓
8. Review final diff & report completed work + next action
```

### The Implementation → Documentation Gate
An agent must **never** consider an implementation complete until the corresponding documentation and `PROJECT_CONTEXT.md` have been updated:
> *"Did the implementation change anything that another developer or AI agent needs to know? If yes, update documentation and PROJECT_CONTEXT.md before closing."*

| Change Type | Documentation Required |
|---|---|
| New feature / agent pipeline | Feature docs + update `PROJECT_CONTEXT.md` |
| API route / schema change | API docs (`docs/api/`) + update `PROJECT_CONTEXT.md` |
| Architectural decision | Add ADR (`docs/architecture/decisions/`) + context |
| New environment variable | `docs/configuration/environment-variables.md` + `.env.example` |
| Bug fix / failure mode | Update `docs/development/troubleshooting.md` |
| New dependency | Update `requirements.txt` / `package.json` + `docs/development/setup.md` |

---

## 1. Ground Rules (Mandatory for Every AI Agent & Every Task)

- **Source of Truth**: Read `PROJECT_CONTEXT.md`, `docs/academic/reports/ArogyaRakshak_Technical_Documentation.md`, and `docs/ArogyaRakshak_Task_Backlog.md` before starting any task. These are the source of truth for architecture, naming, and scope — do not deviate from them without flagging it back first.
- **Model Grounding**: Never call the Groq model `llama3-70b` or `llama-3.3-70b-versatile` — both are deprecated. Always read the model name from the `GROQ_MODEL` environment variable, default `openai/gpt-oss-120b`.
- **Fixed Naming Conventions**:
  - Module package directories are strictly lowercase: `billnyay`, `daavisetu`, `bimanyay`, `schemesetu`, `dawacheck`, `kadi`.
  - Database tables MUST prefix with module scope: `kadi_*`, `billnyay_*`, `daavisetu_*`, `bimanyay_*`, `schemesetu_*`, `dawacheck_*`.
  - API routes follow versioning: `/api/v1/<module>/...`.
- **Kadi Layer Exclusivity**: Kadi (`packages/kadi`) is shared infrastructure, not an isolated module. Any feature that touches document OCR ingestion, entity extraction, phonetic transliteration (IndicXlit), cross-lingual entity resolution (IndicSBERT), or cross-module case context belongs strictly in `packages/kadi`, never duplicated inside a module package.
- **Zero Document Retention (BYOD)**: This is a **bring-your-own-document** app. No persistent storage of uploaded patient documents (PDFs, prescription photos, bills, rejection letters) beyond the active case session. Uploaded files must be processed in transient memory and expunged. Never add persistent file retention "for convenience."
- **Verification Rule**:
  - After any backend change, verify with `curl http://localhost:8000/health` (or the affected endpoint) and run targeted unit tests before declaring the task done.
  - After any frontend change, launch the dev server and verify the page in the browser — never declare a task done simply because code compiles.
- **No Guessing**: If a task is ambiguous or you have to guess at scope, stop and ask rather than guessing silently.
- **Network Boundaries**: Do not install or invoke any package or tool that communicates with network endpoints outside Groq, the local Postgres container, and the official package registries (PyPI / npm) without flagging it first.

---

## 2. Repository Architecture & Directory Orientation

```text
arogyarakshak/
├── apps/
│   ├── api/                     # FastAPI backend application
│   │   ├── app/
│   │   │   ├── api/v1/          # Versioned REST endpoints (kadi, billnyay, schemesetu, etc.)
│   │   │   ├── config.py        # Pydantic Settings (GROQ_MODEL, DATABASE_URL)
│   │   │   ├── database.py      # Async SQLAlchemy engine & session factory
│   │   │   ├── main.py          # FastAPI application entrypoint & error handlers
│   │   │   └── models.py        # SQLAlchemy ORM models (kadi_cases, kadi_entities, etc.)
│   │   ├── Dockerfile           # Backend container definition
│   │   ├── requirements.txt     # Backend runtime dependencies
│   │   └── tests/               # pytest test suite for API endpoints
│   ├── web/                     # Next.js frontend application (App Router)
│   │   ├── app/                 # Next.js pages, layouts, globals.css
│   │   ├── package.json         # React 19, Next.js dependencies
│   │   └── tsconfig.json        # TypeScript configuration
│   └── mobile/                  # React Native / Expo cross-platform mobile client (planned)
├── packages/                    # Independent domain logic libraries (installed via pip -e)
│   ├── kadi/                    # Shared context: extraction, OCR, FAISS vector store
│   ├── billnyay/                # Hospital bill line-item audit vs CGHS benchmarks (5-agent chain)
│   ├── daavisetu/               # Pre-claim cashless pre-authorization form filler
│   ├── bimanyay/                # Post-denial insurance claim audit, IRDAI appeals & SLA tracker
│   ├── schemesetu/              # PMJAY/MJPJAY RAG reasoning agent & semantic embeddings
│   └── dawacheck/               # NPPA Schedule-I medicine pricing & generic mapping
├── data/                        # Ingestion scripts & raw public government data (CGHS, NPPA, PMJAY)
├── docs/                        # Complete technical documentation, backlog, and ADRs
├── .github/                     # Workflows (ci.yml), templates, CODEOWNERS
└── docker-compose.yml           # PostgreSQL 16 + pgvector, API, and Web service definitions
```

---

## 3. Development Workflow & Commands

### 3.1 Local Environment Setup
```bash
# 1. Activate virtual environment (Python 3.11)
source .venv/bin/activate  # Or on Windows: .venv\Scripts\Activate.ps1

# 2. Install dependencies and register editable packages
pip install -r apps/api/requirements.txt
pip install -e packages/kadi
pip install -e packages/billnyay
pip install -e packages/daavisetu
pip install -e packages/schemesetu
pip install -e packages/dawacheck
pip install pytest pytest-asyncio aiosqlite httpx

# 3. Frontend dependencies
cd apps/web && npm install && cd ../..
```

### 3.2 Running the Application
```bash
# Option A: Full stack via Docker Compose
docker-compose up --build

# Option B: Run API locally
cd apps/api
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Option C: Run Web locally
cd apps/web
npm run dev
```

### 3.3 Running Tests & Validation
```bash
# Run API integration tests
cd apps/api
python -m pytest

# Run all package unit tests
cd ../..
python -m pytest packages/

# Run frontend lint
cd apps/web
npm run lint
```

---

## 4. Coding Conventions

### 4.1 Multi-Agent Pipeline Architecture
- When building multi-agent chains (e.g. BillNyay's 5-agent auditing pipeline or BimaNyay's dispute reasoning engine), **keep each agent's prompt and responsibility in a separate function or file**. Do not collapse them into a single mega-prompt.
- **Strictly prefer structured Pydantic models** over free text for inter-agent communication, so downstream agents parse inputs with 100% reliability.

### 4.2 Error Handling & Logging
- Use standard Python `logging.getLogger("arogyarakshak.<subsystem>")`. Never use raw `print()` statements in production package code.
- Return standard HTTP error payloads: `{"detail": "...", "message": "..."}` matching `apps/api/app/main.py`.

### 4.3 Database Migrations & Models
- All database tables must live in `apps/api/app/models.py` subclassing SQLAlchemy `Base`.
- Never run manual `ALTER TABLE` queries ad hoc. Any schema change must be codified in models.

---

## 5. Agent Roles & Responsibilities

| Role | Scope & Ownership | Instructions |
|---|---|---|
| **orchestration-agent** | Multi-agent reasoning chains & Kadi's entity resolution pipeline | Owns `packages/kadi`, agent pipelines in each module package. Enforces structured JSON between agents. |
| **ocr-data-agent** | Document ingestion, OCR (incl. Devanagari), RAG ingestion | Owns `data/` and `ocr.py` / ingestion files in packages. Flags non-standard source document formats early. |
| **frontend-agent** | Next.js interface & trilingual UI | Owns `apps/web` and `apps/mobile`. Default to English-first UI with i18n scaffolding; stub Hindi/Marathi copy for human review. |
| **infra-agent** | Docker, database, SSE streaming, hosting | Owns `docker-compose.yml`, `apps/api` app-level wiring, CI workflows. Ensures reproducible environments. |
| **data-qa-agent** | Government data structuring, IRDAI/scheme rules, multilingual QA | Owns data quality scripts, labeled entity-pair datasets. Cites verifiable public sources for every rate/rule record. |

---

## 6. AI Agent Validation Checklist (Run Before Submitting Work)

Before declaring any task or issue complete, execute this sequence:
1. **Lint Check**: Run `npm run lint` (if frontend touched).
2. **Backend Unit Tests**: Run `python -m pytest apps/api` and `python -m pytest packages/`.
3. **Endpoint Smoke Test**: Verify health and affected route with `curl`.
4. **Docs as Code Gate**: Update `PROJECT_CONTEXT.md` (Current Work, Recent Changes, Next Tasks, Handoff Notes) and any touched architecture/API docs.
5. **Diff Inspection**: Run `git diff` to ensure no accidental files or unintended edits exist.
6. **No Persistent Files**: Verify no temporary document uploads were left behind in the filesystem.
