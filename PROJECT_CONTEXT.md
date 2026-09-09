# Project Context — ArogyaRakshak (आरोग्यरक्षक)

> **The single authoritative, continuously updated engineering context, living memory, and operational state for human developers and AI coding agents.**

---

## 1. Project Identity

- **Project Name:** ArogyaRakshak (आरोग्यरक्षक — "Healthcare Protector")
- **Purpose:** A patient-facing, decision-support platform designed to protect Indian citizens from hospital bill overcharging, wrongful insurance claim repudiations, scheme unawareness, and pharmaceutical price gouging.
- **Academic Context:** B.E. Computer Engineering Final Year Project | PES Modern College of Engineering, Pune | SPPU 2019 Pattern.
- **Team Lead:** Viraj Jadhao | Team of 5.
- **Core Mission:** Empower patients at hospital billing desks and insurance claim stages with immediate, plain-language legal/medical audits, automated appeal packages, and scheme discovery in **English, Hindi, and Marathi**.
- **Repository Purpose:** Production-grade modular monorepo containing backend services (`apps/api`), web client (`apps/web`), cross-platform mobile client (`apps/mobile`), shared intelligence layer (`packages/kadi`), and domain reasoning packages (`billnyay`, `daavisetu`, `bimanyay`, `schemesetu`, `dawacheck`).

---

## 2. Current Project Status

- **Current Phase:** Product Phase 1 Audit & System Hardening Complete (All P0, P1, P2 audit findings resolved and runtime-verified; Product Phase 2 not yet started).
- **Overall Status:** Production Engineering & System Hardening.
- **System Stability:** Functional Production Alpha (All 5 user-facing domain modules fully wired to real backend endpoints on both Web and Mobile; 36 backend pytest tests passing; 17 mobile tests passing; 10 web tests passing; Next.js 16 production build passing with 0 errors; Mobile TypeScript check passing with 0 errors; CI guardrails 100% passing).
- **Primary Focus:** Ready for Product Phase 2 (IndicXlit / IndicSBERT cross-lingual entity resolution in `packages/kadi`).
- **Last Major Milestone:** Remaining Product Phase 1 Audit Fixes Completed & Verified:
  1. `kadi.py` background session resolved via `get_background_session()` with FastAPI dependency override and eager relationship loading (`selectinload`), guaranteeing end-to-end entity persistence in test, local, and Docker environments.
  2. `CameraScanScreen.tsx` routing updated so `documentType === "general"` routes to `BillNyay` with `caseId` preserved.
  3. Web `page.tsx` dummy document fallback completely removed; real file selection strictly required.
  4. CGHS rate schedule resolution made robust with `billnyay.__file__` package path lookup, verified by automated test (`len(CGHS_RATES) > 20`).
  5. `useOfflineQueue` wired into all statutory mobile screen actions (`BENCHMARK_MEDICINE`, `CHECK_SCHEME`, `SUBMIT_PREAUTH`, `ANALYZE_DENIAL`).
  6. EasyOCR / Torch / OpenCV compatibility resolved on supported development environment (`torchvision==0.18.1+cpu`, `numpy<2.0.0`), verified with real image OCR extraction and persistence.
- **Active Blockers:** None.

---

## 3. Product / System Overview

ArogyaRakshak addresses five critical healthcare friction points through non-overlapping, harmonized modules connected by **Kadi**:

```mermaid
flowchart TD
    Doc["Patient Documents<br/>(Bill / Prescription / Denial Letter / Policy)"] --> Kadi["KADI Shared Intelligence Layer<br/>OCR · Entity Extraction · IndicXlit/IndicSBERT Resolution"]
    
    Kadi <--> BN["1. BillNyay<br/>Hospital Bill Audit vs CGHS"]
    Kadi <--> DS["2. DaaviSetu<br/>Pre-Claim Form Automation"]
    Kadi <--> BMN["3. BimaNyay<br/>Denial Dispute & IRDAI Appeal Tracker"]
    Kadi <--> SS["4. SchemeSetu<br/>PMJAY / MJPJAY Welfare Eligibility"]
    Kadi <--> DC["5. DawaCheck<br/>Medicine Pricing & Generic Substitutes"]
```

1. **BillNyay (`packages/billnyay`)**: Audits hospital bills line-by-line against Central Government Health Scheme (CGHS) benchmark rates; drafts dispute representation letters to hospital billing management.
2. **DaaviSetu (`packages/daavisetu`)**: Pre-claim automation pre-populating cashless pre-authorization forms and reimbursement claim packages for major private insurers.
3. **BimaNyay (`packages/bimanyay`)**: Post-denial dispute engine auditing claim repudiations against the **IRDAI Master Circular (May 29, 2024)**; auto-generates 3-tier appeals (GRO, Bima Bharosa, Ombudsman Form VI) and tracks statutory SLAs.
4. **SchemeSetu (`packages/schemesetu`)**: Matches low-income demographics and clinical diagnoses against **PMJAY** (national) and **MJPJAY** (Maharashtra) eligibility rules; locates empanelled network hospitals.
5. **DawaCheck (`packages/dawacheck`)**: Verifies medicine MRP against NPPA Schedule-I price control caps; recommends low-cost bioequivalent generic substitutes at PMBJP Jan Aushadhi Kendras.
6. **Kadi (`packages/kadi`)**: Central shared intelligence layer providing unified document parsing, phonetic transliteration (**IndicXlit**), and cross-lingual semantic matching (**IndicSBERT**).

---

## 4. Architecture Snapshot

- **Backend Gateway (`apps/api`)**: FastAPI async application running under Uvicorn. Implements versioned `/api/v1` routing, async database engine (`asyncpg`), and real-time Server-Sent Events (SSE) status streams.
- **Database & Search**: PostgreSQL 16 with `pgvector` extension for persistent storage and vector embeddings. In-memory `FAISS` indexes in `kadi/vector_store.py` for rapid candidate blocking.
- **LLM Reasoning**: Groq API cloud client (Target model: `openai/gpt-oss-120b`). Deprecated models (`llama3-70b`) are strictly barred.
- **Frontend Clients**:
  - `apps/web`: Next.js 16 App Router, React 19, TypeScript, Vanilla CSS design tokens (Mobile-first, 320px–1280px+, WCAG 2.1 AA).
  - `apps/mobile`: React Native with Expo (TypeScript), client-side document scanner camera.
- **Privacy Architecture**: **Bring-Your-Own-Document (BYOD)**. Uploaded documents exist only in temporary RAM during extraction and are immediately expunged. Zero persistent storage of raw patient documents.

---

## 5. Repository Map

```text
arogyarakshak/
├── apps/
│   ├── api/                     # FastAPI backend application
│   │   ├── app/api/v1/          # Versioned REST endpoints (kadi, billnyay, bimanyay, etc.)
│   │   ├── app/config.py        # Pydantic Settings (DATABASE_URL, GROQ_MODEL)
│   │   ├── app/database.py      # SQLAlchemy async session management
│   │   ├── app/main.py          # FastAPI lifespan, CORS, and error handlers
│   │   ├── app/models.py        # Database ORM models (kadi_cases, bimanyay_cases, etc.)
│   │   └── tests/               # Backend integration test suite (test_api.py)
│   ├── web/                     # Next.js 16 App Router frontend application
│   │   ├── app/components/      # Mobile-first components & module views
│   │   ├── app/globals.css      # Design tokens, fluid typography, touch targets
│   │   ├── app/page.tsx         # Trilingual dashboard with BYOD intake & SSE stream
│   │   └── package.json         # React 19, Next.js dependencies
│   └── mobile/                  # React Native / Expo client (Expo SDK 52, TypeScript, BYOD scanner)
│       ├── App.tsx              # Root component (SafeArea, Theme, Navigation)
│       ├── src/api/             # Shared REST API client matching backend
│       ├── src/components/      # Accessible UI primitives (>= 44px)
│       ├── src/navigation/      # BottomTab + RootStack navigators
│       ├── src/screens/         # HomeScreen, CameraScanScreen, module shells
│       ├── src/services/        # Scanner service & BYOD upload payload
│       ├── src/theme/           # WCAG AA light/dark design tokens
│       └── src/translations/    # Trilingual dictionary (EN, HI, MR)
├── packages/                    # Python domain libraries (installed via pip -e)
│   ├── kadi/                    # Shared context: extraction, vector store, OCR
│   ├── billnyay/                # Hospital bill audit (5-agent reasoning chain)
│   ├── daavisetu/               # Pre-claim cashless pre-auth form generator
│   ├── bimanyay/                # Claim denial dispute & IRDAI appeal tracker
│   ├── schemesetu/              # PMJAY/MJPJAY RAG reasoning & ONNX embeddings
│   └── dawacheck/               # NPPA Schedule-I price verification & generics
├── data/                        # Government rate schedules (CGHS) and raw test sets
├── docs/                        # Complete documentation portal (architecture, guides, ADRs)
│   ├── architecture/            # Repository structure, components, data flow
│   └── ...                      # Development, API, and configuration guides
├── .github/                     # Workflows (ci.yml), templates, CODEOWNERS
├── PROJECT_CONTEXT.md           # Authoritative living engineering memory (this file)
├── AGENTS.md                    # Master operational manual for AI coding agents
├── CONTRIBUTING.md               # Contributor onboarding & lifecycle guide
├── docker-compose.yml           # Multi-service container orchestration
└── .env.example                 # Environment variable template
```

---

## 6. Technology Stack

| Layer | Component | Version / Provider | Notes |
|---|---|---|---|
| **Language Runtime** | Python | `3.11.x` | Production runtime & CI standard. |
| **Language Runtime** | Node.js | `>= 18.x / 20.x` | Frontend runtime for Next.js & Expo. |
| **Backend Framework** | FastAPI | `0.115.12` | Asynchronous REST & SSE endpoints. |
| **Database ORM** | SQLAlchemy | `2.0.38` | Async sessions with `asyncpg`. |
| **Database** | PostgreSQL | `pg16` | Containerized with `pgvector/pgvector:pg16`. |
| **Vector Engine** | FAISS | In-memory | Candidate blocking & similarity scoring. |
| **LLM Inference** | Groq API | `openai/gpt-oss-120b` | High-throughput cloud inference. |
| **Transliteration** | IndicXlit | AI4Bharat | Phonetic mapping across Indic scripts. |
| **Embeddings** | IndicSBERT | L3Cube Pune | Cross-lingual sentence similarity. |
| **Web Client** | Next.js | `16.3.0` / React `19.2.4` | App Router, mobile-first, trilingual UI. |
| **Mobile Client** | Expo / React Native | TypeScript | Document scanner & SLA push alerts. |

---

## 7. Implemented Features

| Feature | Status | Location | Documentation | Automated Tests |
|---|---|---|---|---|
| **Kadi Entity Extraction** | Complete | `packages/kadi/kadi/extraction.py` | `packages/kadi/README.md` | Yes (`test_api.py`) |
| **Kadi Vector Store** | Complete | `packages/kadi/kadi/vector_store.py` | `docs/architecture/components.md` | Yes (`test_ocr.py`) |
| **Kadi OCR Engine** | Complete | `packages/kadi/kadi/ocr/ocr_parser.py` | `packages/kadi/README.md` | Yes (`test_ocr.py`) |
| **BillNyay 5-Agent Pipeline** | Complete | `packages/billnyay/billnyay/agents/`| `packages/billnyay/README.md` | Yes (`test_agents.py`) |
| **DaaviSetu Pre-Auth Generator** | Complete | `packages/daavisetu/daavisetu/generator.py` | `packages/daavisetu/README.md` | Yes (`test_daavisetu.py`) |
| **SchemeSetu RAG Agent** | Complete | `packages/schemesetu/schemesetu/agent.py` | `packages/schemesetu/README.md` | Yes (`test_schemesetu.py`) |
| **SchemeSetu ONNX Fallback** | Complete | `packages/schemesetu/schemesetu/embeddings.py`| `packages/schemesetu/README.md` | Yes (`test_schemesetu.py`) |
| **DawaCheck NPPA Benchmarking** | Complete | `packages/dawacheck/dawacheck/checker.py` | `packages/dawacheck/README.md` | Yes (`test_dawacheck.py`) |
| **SSE Real-Time Stream** | Complete | `apps/api/app/api/v1/endpoints/kadi.py` | `docs/architecture/data-flow.md` | Yes (`test_api.py`) |
| **FastAPI Gateway & Models** | Complete | `apps/api/app/` | `apps/api/README.md` | Yes (`test_api.py`) |
| **BimaNyay IRDAI Engine** | Complete | `packages/bimanyay/` | `packages/bimanyay/README.md` | Yes (`test_bimanyay.py`, `test_api.py`) |
| **Mobile-First Trilingual Web App**| Complete | `apps/web/` | `docs/architecture/repository-structure.md` | Yes (`npm run lint`, `npm run build`) |
| **ArogyaRakshak Mobile App** | Complete | `apps/mobile/` | `docs/architecture/bimanyay-and-mobile.md` | Yes (`npm test`) |


---

## 8. Current Work

### Active Task
Product Phase 1 Final Audit Fixes & Verification Complete.

### Objective
Resolve remaining adversarial audit findings for Product Phase 1 across Kadi background session DB persistence, CameraScan navigation, web file uploader validation, CGHS rates JSON path resolution, mobile offline action queueing, and EasyOCR runtime compatibility without entering Product Phase 2.

### Relevant Areas
- `apps/api/app/api/v1/endpoints/kadi.py` & `apps/api/app/database.py`
- `apps/mobile/src/screens/CameraScanScreen.tsx` & `apps/mobile/src/navigation/types.ts`
- `apps/web/app/page.tsx` & `apps/web/app/components/DocumentUploader.tsx`
- `apps/api/app/api/v1/endpoints/billnyay.py` & `packages/billnyay/billnyay/data/cghs_rates.json`
- `apps/mobile/src/screens/` (`DawaCheckScreen`, `SchemeSetuScreen`, `DaaviSetuScreen`, `BimaNyayScreen`)
- `packages/kadi/kadi/ocr/ocr_parser.py` & `packages/kadi/pyproject.toml`

### Current Progress
- [x] P0: `kadi.py` background session resolved via `get_background_session()` with FastAPI dependency override and eager relationship loading (`selectinload`), guaranteeing end-to-end entity persistence in test, local, and Docker environments.
- [x] P0: `CameraScanScreen.tsx` routing updated so `documentType === "general"` routes to `BillNyay` with `caseId` preserved.
- [x] P1: Web `page.tsx` dummy document fallback completely removed; real file selection strictly required.
- [x] P2: CGHS rate schedule resolution made robust with `billnyay.__file__` package path lookup, verified by automated test (`len(CGHS_RATES) > 20`).
- [x] P2: `useOfflineQueue` wired into all statutory mobile screen actions (`BENCHMARK_MEDICINE`, `CHECK_SCHEME`, `SUBMIT_PREAUTH`, `ANALYZE_DENIAL`).
- [x] OCR: EasyOCR / Torch / OpenCV compatibility resolved on supported development environment (`torchvision==0.18.1+cpu`, `numpy<2.0.0`), verified with real image OCR extraction and persistence.
- [x] Full regression validation suite executed: 36 backend tests, 17 mobile tests, 10 web tests, web/mobile builds, and CI guardrails all passing (0 failures).

### Current Blockers
None. Ready for Product Phase 2 when directed by user.

---

## 9. Next Tasks

### P0 — Critical (Immediate Sprints)
- [x] **Scaffold BimaNyay Package**: Created `packages/bimanyay` with Pydantic schemas for denial reasons, policy clauses, and appeal outputs.
- [x] **Migrate `bimanyay_*` Tables**: Added `bimanyay_cases`, `bimanyay_grievances`, and `bimanyay_timeline_events` to `apps/api/app/models.py`.
- [x] **Implement IRDAI 3-Tier Drafter**: Built appeal letter templates for Insurer GRO, IRDAI Bima Bharosa complaint narrative, and Ombudsman Form VI.
- [x] **Implement Grievance SLA Tracker**: Built timeline engine calculating 15-day GRO, 15-day Bima Bharosa, and 1-year Ombudsman statutory deadlines.
- [x] **Overhaul Web Frontend (`apps/web`)**: Built mobile-first (320px–1280px+), WCAG 2.1 AA trilingual dashboard with BYOD camera intake and live SSE stream.
- [ ] **Scaffold Mobile App (`apps/mobile`)**: Initialize Expo React Native TypeScript project with camera document scanner (`react-native-document-scanner-plugin`).

### P1 — High (Core Integration)
- [ ] **Devanagari OCR Hardening**: Validate Tesseract / vision OCR pipeline on handwritten Marathi/Hindi prescriptions and faded dot-matrix hospital bills.
- [ ] **IndicXlit & IndicSBERT Integration in Kadi**: Connect entity resolution scoring formula combining string distance, transliteration, and embeddings.
- [ ] **Mobile Push SLA Alerts**: Local notifications for 15-day GRO and Bima Bharosa statutory deadlines.

### P2 — Medium (Evaluation & QA)
- [ ] **Implement Benchmark Mapping Accuracy (BMA) Harness**: Build automated evaluation test comparing hospital bills against CGHS codes.
- [ ] **Implement Claim Rejection Mapping Accuracy (CRMA) Harness**: Evaluate BimaNyay against 25 synthetic insurance repudiation scenarios.
- [ ] **Trilingual Copy Polish**: Native speaker review of generated Hindi and Marathi appeal templates.

### P3 — Low (Polish & Presentation)
- [ ] **PDF Digital Signature & Watermarking**: Implement cryptographic hash verification for generated dispute PDFs.
- [ ] **Jan Aushadhi Store Geolocation API**: Embed interactive map of registered PMBJP stores in web and mobile clients.

---

## 10. Prioritized Roadmap

```text
Phase 1: Foundations (COMPLETED)
├── Monorepo scaffolding, Docker Compose, CI pipeline
├── Kadi shared extraction, FAISS vector store, OCR parser
├── BillNyay 5-agent chain, DaaviSetu pre-auth generator
├── SchemeSetu RAG & ONNX embedding fallback, DawaCheck NPPA price checker
└── Repository-wide documentation & test infrastructure overhaul

Phase 2: Module Builds & BimaNyay (ACTIVE)
├── Scaffold packages/bimanyay and 5-agent dispute pipeline
├── Build self-reported Grievance SLA escalation tracker
├── Mount /api/v1/bimanyay endpoints in FastAPI
└── Scaffold apps/mobile (Expo React Native) with camera edge detection

Phase 3: Entity Resolution & Cross-Module Intelligence (NEXT)
├── Integrate IndicXlit (transliteration) and IndicSBERT (cross-lingual)
├── Implement confidence-scored merge/ask-user branching in Kadi
├── Auto-triggering: one document upload surfaces insights across all modules
└── Mobile app multi-module screen assembly (BillNyay, BimaNyay, DaaviSetu, SchemeSetu, DawaCheck)

Phase 4: Multilingual & Evaluation (LATER)
├── Devanagari OCR validation on real/synthetic self-donated documents
├── Terminology QA pass on Hindi & Marathi appeal drafts
└── Quantitative evaluation execution (PEA >= 92%, BMA >= 88%, CRMA >= 90%, WER < 8%)

Phase 5: Submission & Demo Polish (FUTURE)
├── Final deployment (college server / staging host)
├── Live end-to-end demo hardening (1 bill upload -> 5 module insights)
└── SPPU academic final project blackbook & documentation sign-off
```

---

## 11. Known Issues

### 1. Global Python 3.14 Path Priority on Windows Host
- **Problem:** Running `python` without activating the virtual environment invokes Python 3.14, which lacks `pytest` and `fastapi`.
- **Impact:** Command fails with `No module named pytest`.
- **Workaround:** Always activate `.venv\Scripts\Activate.ps1` or run directly with `C:\Users\VIRAJ\AppData\Local\Programs\Python\Python311\python.exe`.
- **Status:** Documented in `docs/development/troubleshooting.md`.

### 2. Pytest Asyncio Default Fixture Loop Scope Warning (RESOLVED)
- **Problem:** Deprecation warning during pytest run: `asyncio_default_fixture_loop_scope is unset`.
- **Resolution:** Configured `asyncio_default_fixture_loop_scope = "function"` in root `pytest.ini`.
- **Status:** Closed / Resolved.

---

## 12. Technical Debt

1. **`apps/api/tests/conftest.py` Module Resolution (RESOLVED)**:
   - *Issue*: `from app.main import app` requires pytest to be invoked from inside `apps/api/` or with `PYTHONPATH=apps/api`.
   - *Resolution*: Configured `pythonpath = apps/api` and `testpaths = packages apps/api/tests` in root `pytest.ini`. Root `pytest` command now runs all 29 tests seamlessly.
   - *Status*: Closed / Resolved.
2. **Mock Groq API in Unit Tests**:
   - *Issue*: Some package tests use static mocked responses rather than a unified VCR.py or httpx mock fixture.
   - *Resolution*: Consolidate mock LLM fixtures into a shared test utility in `packages/kadi`.

---

## 13. Important Decisions (ADR Summary)

- **ADR-001 (Monorepo Architecture):** Unified monorepo with editable packages (`pip install -e`) chosen over 7+ fragmented micro-repos for atomic PRs and zero publishing overhead.
- **ADR-002 (Kadi as Shared Infrastructure):** Kadi is the central data extraction and entity resolution foundation, not an isolated 4th module. Document parsing is de-duplicated.
- **ADR-003 (Bring-Your-Own-Document Privacy):** Zero persistent storage of patient health documents. Raw files exist only in transient memory during extraction.
- **ADR-004 (Groq Model Selection):** Hardcoded deprecation ban on `llama3-70b`. All calls dynamically load from `GROQ_MODEL` (default: `openai/gpt-oss-120b`).
- **ADR-005 (DaaviSetu vs BimaNyay Division):** Clean lifecycle separation: DaaviSetu owns pre-claim application filing; BimaNyay owns post-denial repudiation disputes and IRDAI appeals.

---

## 14. Constraints & Non-Negotiables

1. **Zero Retention Rule**: Never persist uploaded patient bills, prescription images, or claim denial PDFs to disk or permanent database tables beyond the active extraction session.
2. **Model Grounding**: Never call `llama3-70b` or `llama-3.3-70b-versatile`. Always read from `GROQ_MODEL`.
3. **Fixed Naming Conventions**:
   - Python package names: strictly lowercase (`billnyay`, `daavisetu`, `bimanyay`, `schemesetu`, `dawacheck`, `kadi`).
   - Database tables: prefix with module namespace (`kadi_*`, `billnyay_*`, `daavisetu_*`, `bimanyay_*`, `schemesetu_*`, `dawacheck_*`).
   - API endpoints: `/api/v1/<module>/...`.
4. **Network Boundaries**: Do not introduce dependencies that communicate with network endpoints outside Groq Cloud, the local Postgres container, and official package registries (PyPI, npm).
5. **Multi-Agent Pipeline Separation**: Multi-agent chains must keep each agent's logic and prompt in a separate function/file. Inter-agent communication must use typed Pydantic models.

---

## 15. Testing Status

- **Unified Pytest Test Runner (`pytest.ini`)**: **36 passed in 5.70s (100% pass rate)**.
  - **Package Unit Suites (`packages/*/tests/`)**: 23 passed.
    - `packages/billnyay`: 4 tests passed (`test_agents.py`)
    - `packages/daavisetu`: 1 test passed (`test_daavisetu.py`)
    - `packages/dawacheck`: 3 tests passed (`test_dawacheck.py`)
    - `packages/kadi`: 6 tests passed (`test_ocr.py` - hardened assertions for line items, amounts, rupee symbols, multi-page PDFs, noise filtering, and summary line exclusions)
    - `packages/schemesetu`: 2 tests passed (`test_schemesetu.py`)
    - `packages/bimanyay`: 7 tests passed (`test_bimanyay.py` - clause auditor, drafter, timeline tracker, and Hindi/Marathi statutory appeal copy validation)
  - **API Integration Suite (`apps/api/tests/test_api.py`)**: 13 passed in 3.65s.
    - `test_health_endpoint`
    - `test_create_and_get_case` (covers case creation, upload, background session, entity persistence, retrieval)
    - `test_dawacheck_benchmark`
    - `test_schemesetu_eligibility`
    - `test_bimanyay_analyze`
    - `test_bimanyay_analyze_multilingual`
    - `test_bimanyay_timeline`
    - `test_daavisetu_claim`
    - `test_billnyay_audit`
    - `test_daavisetu_pdf_download`
    - `test_dawacheck_mobile_samples`
    - `test_cghs_rates_loaded_from_json` (proves full CGHS dataset loaded from JSON, > 20 items)
    - `test_real_image_ocr_upload_and_persistence` (proves real image EasyOCR pipeline executes and persists entities to DB)
- **Frontend Test Suite (`apps/web`)**: `npm test` passed with **10/10 tests passed** (contracts, versioning, routing boundaries, mandatory file upload invariant, trilingual dictionaries).
- **Frontend Linter & Build (`apps/web`)**: `npm run lint` passed with 0 errors, 0 warnings; `npm run build` compiled cleanly in 924ms (Next.js 16.2.10 / Turbopack; 100% static routes).
- **Mobile Client Test Suite (`apps/mobile`)**: `npm test` (`tsx --test`) passed with **17/17 passed in 185ms** (BYOD invariant guard, Kadi upload routing, createCase consent opt-in, multilingual BimaNyay API mapping, scanner payload validation, trilingual dictionary keys, documentType "general" routing with caseId preserved, all 4 statutory offline queue action types).
- **Mobile Client Type-Check (`apps/mobile`)**: `npm run type-check` (`tsc --noEmit`) passed with **0 errors** across all navigation, screens, API types, hooks, and design system components.
- **CI Guardrails (`scripts/ci_guardrails.py`)**: **5/5 checks passed** (BYOD zero-retention invariants, deprecated model ban, package directory lowercase, DB table prefixes, secret leak detection).


---

## 16. Documentation Map

| Area | Primary Document |
|---|---|
| **Portal Sitemap** | [`docs/README.md`](docs/README.md) |
| **System Architecture** | [`docs/architecture/overview.md`](docs/architecture/overview.md) |
| **Component Specifications** | [`docs/architecture/components.md`](docs/architecture/components.md) |
| **Data Flow & Streaming** | [`docs/architecture/data-flow.md`](docs/architecture/data-flow.md) |
| **Architectural Decisions** | [`docs/architecture/decisions/`](docs/architecture/decisions/) |
| **Developer Setup** | [`docs/development/setup.md`](docs/development/setup.md) |
| **Git & Commit Workflow** | [`docs/development/workflow.md`](docs/development/workflow.md) |
| **Testing Strategy** | [`docs/development/testing.md`](docs/development/testing.md) |
| **Troubleshooting Guide** | [`docs/development/troubleshooting.md`](docs/development/troubleshooting.md) |
| **Environment Variables** | [`docs/configuration/environment-variables.md`](docs/configuration/environment-variables.md) |
| **API Endpoints** | [`docs/api/overview.md`](docs/api/overview.md) |
| **BimaNyay & Mobile Blueprint** | [`docs/architecture/bimanyay-and-mobile.md`](docs/architecture/bimanyay-and-mobile.md) |
| **Agile Planning & Sprints** | [`docs/planning/weekly-sprint-playbook.md`](docs/planning/weekly-sprint-playbook.md) |
| **Academic & Research Portfolio** | [`docs/academic/README.md`](docs/academic/README.md) |
| **Task Backlog** | [`docs/ArogyaRakshak_Task_Backlog.md`](docs/ArogyaRakshak_Task_Backlog.md) |

---

## 17. Recent Changes

### 2026-09-09
- **Documentation Directory Restructuring & Modernization**:
  - Restructured `docs/` into distinct engineering, planning, and academic directories (`architecture/`, `api/`, `configuration/`, `development/`, `planning/`, `academic/`).
  - Pruned obsolete, duplicate, and unrelated assets (`IndiaAI_Student_User_Manual.docx.pdf`, empty `docs/final/`, legacy duplicate PDFs and outdated decks from `v1/` and `v2/`).
  - Relocated and consolidated academic deliverables, presentations, viva defense notes, and research papers under `docs/academic/` with a comprehensive index.
  - Organized sprint playbooks, team division strategy, and futuristic roadmap under `docs/planning/`.
  - Moved BimaNyay and Mobile architecture specification to `docs/architecture/bimanyay-and-mobile.md` and diagrams to `docs/architecture/diagrams/`.
  - Updated developer guides (`setup.md`, `testing.md`) to include `bimanyay` and `apps/mobile` testing (42 tests passing across backend and mobile).
- **Repository Documentation & Agent Readiness Overhaul**:
  - Authored comprehensive root `README.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, `CHANGELOG.md`, `LICENSE`, and `.gitattributes`.
  - Created `.github` templates (Bug Report, Feature Request, PR Template, CODEOWNERS, `.github/AGENTS.md`).
  - Structured `/docs` hierarchy into `architecture/`, `development/`, `configuration/`, `api/`, and `decisions/` (ADR-001 through ADR-005).
  - Modernized READMEs across `apps/api`, `apps/web`, `packages/kadi`, `billnyay`, `daavisetu`, `schemesetu`, `dawacheck`, and `data`.
- **BimaNyay & Mobile Architecture Locked**:
  - Codified the IRDAI 3-tier escalation ladder (GRO 15d -> Bima Bharosa 15d -> Insurance Ombudsman Form VI up to ₹50L).
  - Formulated the Zero-Overlap Boundary Matrix separating DaaviSetu (pre-claim) and BimaNyay (post-denial).
  - Designed the fully functional 5-module mobile client architecture (`apps/mobile`).
  - Updated task backlog with discrete GitHub issues for BimaNyay and Mobile App.
- **BimaNyay Insurance Denial Engine Implemented**:
  - Built `packages/bimanyay` with `clause_auditor.py` (5-Year Moratorium, unapproved exclusions, room rent capping, delayed intimation audit).
  - Built `drafter.py` generating Level 1 GRO appeal, Level 2 Bima Bharosa (2,000-char compliant text), and Level 3 Ombudsman Form VI statement of facts.
  - Built `tracker.py` computing statutory SLA timeline milestones (15d GRO, 15d Bima Bharosa, 365d Ombudsman).
  - Wired ORM models (`bimanyay_cases`, `bimanyay_grievances`, `bimanyay_timeline_events`) into `apps/api/app/models.py`.
  - Registered `/api/v1/bimanyay` endpoints in `apps/api/app/api/v1/endpoints/bimanyay.py` and `api.py`.
- **Mobile-First Trilingual Web Dashboard Overhauled**:
  - Overhauled `apps/web` with responsive design tokens in `globals.css` (320px–1280px+, WCAG 2.1 AA contrast, touch targets >= 44px).
  - Implemented trilingual UI dictionary in `translations.ts` supporting English, Hindi (हिंदी), and Marathi (मराठी).
- **Verification Audit P1 Fixes, Touch-Target Hardening & OCR Rigor**:
  - Hardened mobile touch targets in `apps/web/app/globals.css`: added `min-width: var(--min-touch-target)` (44px x 44px) to `.lang-btn` and `.tab-btn`, `min-height: var(--min-touch-target)` to `.brand-logo`, and introduced `.consent-wrapper` for full 44px checkbox tap area meeting WCAG 2.1 SC 2.5.5 / WCAG 2.2 SC 2.5.8.
  - Eliminated all Pydantic deprecation warnings: converted `apps/api/app/config.py` to `SettingsConfigDict` and confirmed zero schema warnings.
  - Hardened OCR test suite in `packages/kadi/kadi/ocr/tests/test_ocr.py` with 6 exhaustive unit tests asserting exact item names, float prices, rupee symbol formatting, multi-page PDFs, noise filtering, and summary exclusions.
  - Fixed summary filtering bug in `packages/kadi/kadi/ocr/ocr_parser.py` (preventing `Total Bill` from parsing as a billable hospital line item while preserving clinical procedure names like `Total Knee Replacement`).
  - Added root `pytest.ini` resolving `apps/api` pythonpath (resolving Technical Debt #1) and setting `asyncio_default_fixture_loop_scope = "function"` (resolving Known Issue #2).
  - Clean unified test execution: `pytest` runs all 29 tests (21 package + 8 API) with 0 warnings in 2.45s.
- **Verification Audit P2 Improvements, Theme Switcher & Trilingual BimaNyay Polish**:
  - **Accessible Light/Dark Theme Switcher**:
    - Implemented WCAG 2.1 AA compliant `[data-theme="light"]` token overrides in `apps/web/app/globals.css` covering surface, borders, high-contrast text, brand accents, and elevated cards.
    - Added dedicated theme switcher button (`.theme-toggle-btn`) in `apps/web/app/components/Header.tsx` meeting the minimum 44px x 44px touch target (`--min-touch-target: 44px`) with accessible `aria-label` and `title`.
    - Wired state management in `apps/web/app/page.tsx` with lazy initialization checking `localStorage` and `prefers-color-scheme`, synchronizing cleanly to `document.documentElement` without hydration flicker or React 19 linter warnings.
  - **Vetted Hindi & Marathi Statutory Legal Drafter in BimaNyay**:
    - Enhanced `packages/bimanyay/bimanyay/drafter.py` to produce authentic Indian statutory copy across all 3 escalation tiers in English, Hindi (`hi`), and Marathi (`mr`):
      - *Level 1 (GRO Appeal)*: विधिक सांविधिक अपील / वैधानिक अपील citing IRDAI Master Circular (May 29, 2024) Clause 16 (5-Year Moratorium rule) and mandatory 3-member Claims Review Committee (CRC) approval.
      - *Level 2 (Bima Bharosa IGMS)*: Structured regulatory grievance narrative bounded strictly within the 2,000-character portal limit.
      - *Level 3 (Insurance Ombudsman Form VI)*: Formal Statement of Facts (हकीकतीचे निवेदन / तथ्यों का विवरण) under Rule 14(1)(b) of Insurance Ombudsman Rules, 2017.
    - Extended `analyze_insurance_denial(input_data, language: str = "en")` in `packages/bimanyay/bimanyay/__init__.py` and API endpoint `POST /api/v1/bimanyay/analyze` to support `language` query parameter.
    - Wired `apps/web/app/components/modules/BimaNyayView.tsx` to dynamically request and render vetted legal documents according to the active language (`currentLang`).
  - **Comprehensive Test Suite & CI Validation**:
    - Added unit tests `test_drafter_hindi_output` and `test_drafter_marathi_output` in `packages/bimanyay/tests/test_bimanyay.py` (7/7 tests passing).
    - Added integration test `test_bimanyay_analyze_multilingual` in `apps/api/tests/test_api.py` (9/9 tests passing).
    - Unified test execution: **32/32 tests passing with 0 warnings in 2.49s**.
    - Frontend verification: `npm run lint` (0 errors, 0 warnings) and `npm run build` (compiled in 865ms, 100% static routes).
  - **GitHub Issue Tracking**:
    - Updated issues #122, #123, #126, and #127 with verification test logs and implementation details.

- **Mobile App Foundation (`apps/mobile`) Scaffolded & Foundation Gaps Closed**:
  - Scaffolded cross-platform mobile client with **Expo SDK 52**, **React Native 0.76 (New Architecture enabled)**, and strict **TypeScript** (`tsconfig.json` with `@/*` aliases).
  - Built **Design System** in `src/theme/` mirroring web app tokens: dark base (`#0a0e17`), light base (`#f8fafc`), brand cyan (`#06b6d4`), fluid typography, and strictly enforced 44px touch targets (`--min-touch-target: 44px` / WCAG 2.1 SC 2.5.5).
  - Implemented **Trilingual Dictionary** in `src/translations/` supporting English, Hindi (`हिंदी`), and Marathi (`मराठी`).
  - Built **React Navigation Foundation** in `src/navigation/` with `BottomTabNavigator` (Home, BillNyay, DaaviSetu, BimaNyay, SchemeSetu, DawaCheck) and `RootNavigator` with modal camera presentation.
  - Implemented **Shared API Gateway Client** in `src/api/` with timeouts, normalized error payloads, and strongly typed routes mapped to all 5 domain endpoints and Kadi context layer.
  - Built **Real `expo-camera` Hardware Capture** in `src/screens/CameraScanScreen.tsx` with native `CameraView`, `useCameraPermissions()` reactive permission card, flash toggle, high-resolution `takePictureAsync({ quality: 0.85 })`, and graceful simulator/headless fallback.
  - Implemented **Kadi Case Creation & Multipart Ingestion Pipeline** in `src/services/scanner.ts` and `src/api/endpoints.ts`: `processScanAndUpload()` creates a case via `api.kadi.createCase({ consent_opt_in: true })` and posts multipart document data to `/api/v1/kadi/cases/{caseId}/upload`.
  - Enforced strict **BYOD Zero-Retention Invariant**: raw documents exist only in transient memory during extraction and are immediately expunged; persistent offline storage explicitly rejects raw medical records.
  - Implemented **Offline-First Architecture Hooks** in `src/hooks/`: `useNetworkStatus`, `useOfflineStorage` (with secure storage and BYOD guard), and `OfflineBanner`.
  - Scaffolded **Accessible UI Primitives** in `src/components/`: `Header` (with BYOD badge, language and theme toggles), `Button` (>= 44px), `Card`, `Badge`, and `OfflineBanner`.
  - Built **Foundational Screen Shells** in `src/screens/`: `HomeScreen`, `BillNyayScreen`, `DaaviSetuScreen`, `BimaNyayScreen`, `SchemeSetuScreen`, and `DawaCheckScreen`.
  - Authored **Automated Mobile Test Suite** in `tests/`: 10 tests across 4 suites covering BYOD invariant guard, Kadi upload routing contracts, consent opt-in, multilingual BimaNyay API mapping, scanner payload validation, and trilingual dictionary integrity (`npm test` via native `tsx --test`).
  - Authored comprehensive developer documentation in `apps/mobile/README.md`.
  - Created GitHub Issue [#134](https://github.com/Viraj281105/Arogyarakshak/issues/134) and documented verification results and gap closures in comment [#5599098873](https://github.com/Viraj281105/Arogyarakshak/issues/134#issuecomment-5599098873).
  - Validated with `npm run type-check` (`tsc --noEmit` passing with 0 errors) and `npm test` (10/10 passed).

- **Product Phase 1: Full-Stack Web & Mobile Module API Integration Complete**:
  - **Universal Web Module Wiring (`apps/web`)**:
    - Created unified `useApi` hook in `apps/web/app/hooks/useApi.ts` providing standardized async lifecycle handling (loading, error, data states, AbortController timeout).
    - Updated `page.tsx` to pass active `caseId` across all module views.
    - Replaced all static/client-side string templates in module views with live backend endpoints:
      - `BillNyayView.tsx`: Calls `POST /api/v1/billnyay/cases/{caseId}/audit`, rendering live CGHS benchmark deviations, room rent capping, unbundled charges, and audit item breakdown.
      - `DawaCheckView.tsx`: Calls `POST /api/v1/dawacheck/benchmark`, verifying brand MRP against NPPA Schedule-I ceiling rates and surfacing PMBJP Jan Aushadhi generic equivalents.
      - `SchemeSetuView.tsx`: Calls `POST /api/v1/schemesetu/eligibility`, sending income, state, category, and medical procedure to retrieve PMJAY/MJPJAY eligibility scores and step-by-step claim guides.
      - `BimaNyayView.tsx`: Calls `POST /api/v1/bimanyay/analyze` (with language parameter) and `POST /api/v1/bimanyay/timeline`, displaying regulatory violations, reversal probability, multi-tier appeal drafts (GRO, Bima Bharosa, Ombudsman), and statutory SLA tracking.
      - `DaaviSetuView.tsx`: Calls `POST /api/v1/daavisetu/cases/{caseId}/claim`, retrieving auto-populated cashless pre-authorization claim packages.
    - Verified `apps/web`: `npm run lint` (0 errors, 0 warnings) and `npm run build` (Next.js 16 production build succeeded).
  - **Universal Mobile Module Wiring (`apps/mobile`)**:
    - Aligned mobile API request/response types in `src/api/types.ts` and route bindings in `src/api/endpoints.ts` with FastAPI schemas.
    - Implemented full API integration across all 5 mobile module screens:
      - `BillNyayScreen.tsx`: Kadi case creation, document upload, and `api.billnyay.audit` execution with live charged vs CGHS benchmark stats.
      - `BimaNyayScreen.tsx`: Policy repudiation intake form, `api.bimanyay.analyze` with trilingual support, 3-tier appeal tabs, native `Share.share` draft export, and SLA timeline.
      - `DaaviSetuScreen.tsx`: Pre-auth form generation via `api.daavisetu.submitClaim` with live claim ID and field breakdown.
      - `SchemeSetuScreen.tsx`: Demographics & procedure intake form, `api.schemesetu.checkEligibility` evaluation, match confidence badges, and claim guide steps.
      - `DawaCheckScreen.tsx`: NPPA ceiling rate audit form via `api.dawacheck.benchmark`, quick sample pill selectors, generic substitute locator, and camera scan integration.
    - Replaced external clipboard dependency with native `Share.share` in `BimaNyayScreen.tsx` (zero additional native dependencies required).
    - Verified `apps/mobile`: `npm run type-check` (`tsc --noEmit` passed with 0 errors) and `npm test` (10/10 tests passed).

- **CI/CD Pipeline Production Hardening (`.github/workflows/ci.yml` & `scripts/ci_guardrails.py`)**:
  - Replaced basic 56-line test script with an enterprise multi-stage CI/CD pipeline featuring **6 parallel, specialized stages**:
    1. **Architectural Invariants & Security Guard** (`governance-and-invariants`): Standalone Python scanner (`scripts/ci_guardrails.py`) validating BYOD zero-retention (zero persistent document directories), model grounding (prohibiting deprecated Groq models `llama3-70b` and `llama-3.3-70b-versatile`), lowercase monorepo package hygiene, database table prefix conventions (`kadi_*`, `billnyay_*`, etc.), and accidental API key leak prevention.
    2. **Backend Integration & Domain Matrix** (`backend-ci`): PostgreSQL 16 + `pgvector` service container with health checks, pip caching, install of all 6 local packages (`kadi`, `billnyay`, `daavisetu`, `bimanyay`, `schemesetu`, `dawacheck`), Ruff static analysis, full pytest execution with term/XML coverage reporting, and coverage artifact upload.
    3. **Web Client Production Gate** (`web-ci`): Node.js 20 with npm caching, Next.js build cache restoration, ESLint check (`npm run lint`), and Next.js 16 production build verification (`npm run build`).
    4. **Mobile Client Production Gate** (`mobile-ci`): Node.js 20 with npm caching, TypeScript type-check (`npm run type-check`), and complete test suite execution (`npm test`).
    5. **Docker Infrastructure Verification** (`docker-verification`): Docker Compose configuration validation (`docker compose config --quiet`), Buildx layer caching via GitHub Actions cache (`type=gha`), and dry-run container builds for `apps/api/Dockerfile` (fixed missing `bimanyay` package) and `apps/web/Dockerfile`.
    6. **Unified Branch Protection Gate** (`ci-gate`): Aggregates all upstream job results into a rich markdown GitHub Step Summary table and outputs a single green checkmark for GitHub branch protection rule enforcement.
  - Configured concurrency cancellation (`cancel-in-progress: true`) to automatically kill obsolete runs on branch updates and prevent compute exhaustion.

---

- **Product Phase 1: Independent Audit Fixes Completed**:
  - **P0: Mobile Camera → Kadi → Module Flow & Real Entity Extraction**:
    - Fixed `CameraScanScreen.tsx` to automatically route back to destination modules (`BillNyay`, `BimaNyay`, `DawaCheck`) passing `{ caseId, scanCompleted: true }`.
    - Updated `BottomTabParamList` to accept route parameters.
    - Eliminated all dummy `data:text/plain;base64,` base64 uploads from `BillNyayScreen.tsx` and `DaaviSetuScreen.tsx`.
    - Connected Kadi background document ingestion (`apps/api/app/api/v1/endpoints/kadi.py`) to real `extract_entities_from_text` (Groq API or regex/heuristic fallback), persisting clinical entities (`hospital`, `patient`, `diagnosis`, `procedure`, `medicine`) in addition to billing line items.
    - Updated `packages/kadi/kadi/ocr/ocr_parser.py` with UTF-8/plain-text decoding fallback prior to PyMuPDF to gracefully handle text document uploads without crashes.
  - **P1: Configured Groq Inference & Trilingual Form Localization**:
    - Replaced hardcoded Groq fallback in `apps/api/app/api/v1/endpoints/billnyay.py` with real `GroqClient` instantiated using `settings.groq_model` and `settings.groq_api_key`.
    - Expanded `apps/mobile/src/translations/strings.ts` with comprehensive form labels, placeholders, buttons, statutory badges, and audit results across English, Hindi, and Marathi.
    - Localized all mobile screens (`BillNyayScreen`, `DaaviSetuScreen`, `BimaNyayScreen`, `SchemeSetuScreen`, `DawaCheckScreen`).
  - **P1: Mobile SSE Streaming & Real-Time Feedback**:
    - Created `useSSEStream` hook in `apps/mobile/src/hooks/useSSEStream.ts` supporting standard EventSource and fetch-based streaming from `/api/v1/kadi/cases/{caseId}/stream`.
    - Implemented `AgentStreamVisualizer` component in `apps/mobile/src/components/AgentStreamVisualizer.tsx` displaying live multi-agent stage indicators, progress percentage, and log messages.
  - **P1: Meaningful Web UI & Mobile User-Flow Tests**:
    - Created web test suite in `apps/web/tests/` (`translations.test.ts`, `useApi.test.ts`, `contracts.test.ts`) running via `npm test` with 9 passing tests.
    - Created mobile test suite in `apps/mobile/tests/screen_and_flow.test.ts` verifying camera scan routing contracts, screen params, trilingual dictionary parity, SSE stream parsing, and offline queue serialization with 15 passing tests.
  - **P2: DawaCheck 404s, CGHS 2024 Rates, DaaviSetu PDF & Offline Queue**:
    - Added NPPA Schedule-I ceiling rates for all 4 mobile sample medicines (`Dolo 650mg`, `Augmentin 625 Duo`, `Metformin 500mg SR`, `Meropenem 1g`) plus fuzzy alias matching in `packages/dawacheck/dawacheck/checker.py`.
    - Created comprehensive CGHS 2024 rate schedule in `packages/billnyay/billnyay/data/cghs_rates.json` and dynamically loaded in `billnyay.py`.
    - Implemented real IRDAI Standard Pre-Authorization Form (Annexure-B) PDF generation in `packages/daavisetu/daavisetu/generator.py` via ReportLab and exposed `GET /api/v1/daavisetu/cases/{case_id}/claim/pdf` with web and mobile download buttons.
    - Implemented `useOfflineQueue` hook in `apps/mobile/src/hooks/useOfflineQueue.ts` leveraging secure storage with automatic queue draining on network reconnect, strictly adhering to BYOD zero-retention.

---

## 18. Agent Handoff Notes

### Last Completed Work
Successfully fixed and verified all Product Phase 1 issues based on the independent audit across P0, P1, and P2 priority levels:
1. **Camera → Kadi → Module Flow**: Real flow established; dummy base64 strings removed; caseId routed cleanly.
2. **Kadi Entity Extraction**: Real entity extraction wired into background pipeline with clinical entity persistence.
3. **Inference Grounding**: Configured Groq inference used in `billnyay.py`.
4. **Mobile Localization**: All 5 mobile module forms localized in English, Hindi, and Marathi.
5. **Mobile SSE Streaming**: Live status stream connected with `AgentStreamVisualizer`.
6. **DaaviSetu PDF Generation**: Live IRDAI Annexure-B PDF generated and downloadable on Web and Mobile.
7. **DawaCheck Sample 404s**: Fully resolved with expanded NPPA Schedule-I rates and alias matching.
8. **BillNyay CGHS Dataset**: Benchmark dataset codified in `cghs_rates.json` and wired to audit endpoint.
9. **Mobile Offline Action Queue**: Enqueue and automatic replay implemented via `useOfflineQueue`.
10. **Validation Suite Results**:
    - Backend: `pytest` passed **34/34 tests** (100%).
    - Web: `npm test` passed **9/9 tests**; `npm run lint` passed **0 errors**; `npm run build` passed.
    - Mobile: `npm test` passed **15/15 tests**; `npm run type-check` passed **0 errors**.
    - CI Guardrails: `python scripts/ci_guardrails.py` passed **5/5 checks**.

### Current State
Product Phase 1 audit fixes are 100% complete and verified. Product Phase 2 has NOT been started.

### Recommended Next Action
When authorized by the user, begin Product Phase 2:
1. Advance IndicXlit phonetic transliteration & IndicSBERT cross-lingual semantic matching in `packages/kadi`.
2. Expand entity graph and cross-module context sharing in Kadi.

---

## 19. Definition of Done & Pre-Commit Agent Checklist

Before any AI coding agent considers a task or session complete, it must execute the **Implementation → Documentation Gate**:

```markdown
- [ ] Implementation completed adhering to module boundaries
- [ ] Relevant unit & integration tests added or updated
- [ ] Backend tests executed: `python -m pytest apps/api` and `python -m pytest packages/`
- [ ] Frontend linter executed: `npm run lint` in `apps/web` (if frontend touched)
- [ ] BYOD zero-retention verified (no persistent document storage introduced)
- [ ] Model grounding verified (uses GROQ_MODEL, no deprecated llama models)
- [ ] Relevant documentation updated (READMEs, docs/architecture, docs/api, etc.)
- [ ] PROJECT_CONTEXT.md updated (Current Work, Recent Changes, Agent Handoff Notes)
- [ ] Git diff inspected to verify no unintended or temporary files remain
```
