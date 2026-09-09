# Repository Structure & Restructuring Migration Record

**Project:** ArogyaRakshak (आरोग्यरक्षक)  
**Standard:** Production Monorepo  
**Stack:** FastAPI + Next.js (App Router) + PostgreSQL/pgvector + FAISS + Groq API  

---

## 1. Executive Summary & Purpose

This document serves as the official restructuring migration record for the ArogyaRakshak repository. It details the structural reorganization, naming conventions, architectural boundaries, and mobile responsiveness standards codified across the monorepo.

---

## 2. Target Repository Architecture

```text
arogyarakshak/
├── apps/
│   ├── api/                     # FastAPI backend application
│   │   ├── app/
│   │   │   ├── api/v1/          # Versioned REST endpoints
│   │   │   │   ├── endpoints/   # Domain route handlers (kadi, billnyay, bimanyay, etc.)
│   │   │   │   └── api.py       # Central v1 router aggregator
│   │   │   ├── config.py        # Pydantic Settings (GROQ_MODEL, DATABASE_URL)
│   │   │   ├── database.py      # Async SQLAlchemy engine & session factory
│   │   │   ├── main.py          # FastAPI application entrypoint & middleware
│   │   │   └── models.py        # SQLAlchemy ORM models (kadi_*, bimanyay_*, etc.)
│   │   ├── Dockerfile           # Backend production container definition
│   │   ├── requirements.txt     # Runtime dependencies
│   │   └── tests/               # Backend integration and endpoint tests
│   ├── web/                     # Next.js 16 (React 19) frontend application
│   │   ├── app/                 # App Router pages and layout
│   │   │   ├── components/      # UI components and module views
│   │   │   │   ├── modules/     # Feature-specific views (BillNyay, BimaNyay, etc.)
│   │   │   │   ├── Header.tsx   # Trilingual navigation & BYOD privacy badge
│   │   │   │   ├── Footer.tsx   # Statutory citations & DPDP compliance note
│   │   │   │   ├── DocumentUploader.tsx # BYOD drag/drop & camera input
│   │   │   │   └── AgentStreamVisualizer.tsx # SSE live pipeline streamer
│   │   │   ├── globals.css      # Mobile-first design tokens, fluid typography
│   │   │   ├── layout.tsx       # Viewport & semantic metadata
│   │   │   ├── page.tsx         # Central multi-agent dashboard
│   │   │   └── translations.ts  # Trilingual dictionary (EN, HI, MR)
│   │   ├── Dockerfile           # Frontend container definition
│   │   └── package.json         # React 19 / Next.js scripts
│   └── mobile/                  # React Native / Expo client (planned)
├── packages/                    # Independent domain logic libraries (pip -e)
│   ├── kadi/                    # Shared context: OCR, IndicXlit, IndicSBERT, FAISS
│   ├── billnyay/                # Hospital bill line-item audit vs CGHS tariffs (5 agents)
│   ├── bimanyay/                # Insurance denial audit, IRDAI appeals & SLA tracker
│   ├── daavisetu/               # Cashless pre-authorization form automation
│   ├── schemesetu/              # PMJAY/MJPJAY eligibility assessment & RAG
│   └── dawacheck/               # NPPA Schedule-I ceiling price & generic mapping
├── data/                        # Ingestion scripts & raw public government data
├── docs/                        # Complete technical documentation, backlog, and ADRs
│   ├── architecture/            # Architectural decisions, data flow, structure
│   ├── api/                     # REST API reference
│   ├── configuration/           # Environment variables & runtime settings
│   └── development/             # Developer workflow, setup, and testing guides
├── .github/                     # Issue templates, PR templates, CODEOWNERS, CI
└── docker-compose.yml           # PostgreSQL 16 + pgvector, API, and Web services
```

---

## 3. Strict Naming Conventions

To eliminate ambiguity and ensure seamless developer and AI agent navigation, the following naming rules are strictly enforced:

| Scope | Convention | Examples | Anti-Patterns (Forbidden) |
|---|---|---|---|
| **Packages (`packages/`)** | Strict lowercase, single word or joined | `billnyay`, `bimanyay`, `daavisetu`, `kadi` | `BillNyay`, `bima-nyay`, `misc`, `helpers` |
| **Database Tables** | Module prefix with underscore | `kadi_cases`, `bimanyay_cases`, `dawacheck_generic_mappings` | `cases`, `claims`, `table1`, `data` |
| **API Endpoints** | RESTful kebab/noun under `/api/v1/<module>` | `/api/v1/bimanyay/analyze`, `/api/v1/kadi/cases` | `/api/getStuff`, `/v2/new/audit` |
| **React Components** | PascalCase matching file basename | `DocumentUploader.tsx`, `BimaNyayView.tsx` | `uploader.tsx`, `comp2.tsx`, `index2.tsx` |
| **CSS Variables** | Kebab-case semantic tokens | `--brand-cyan`, `--radius-md`, `--min-touch-target` | `--c1`, `--blue2`, `--my-style` |

---

## 4. Architectural Boundaries & Dependency Direction

The codebase enforces unidirectional dependency flow:

```text
Next.js UI (apps/web)
       ↓ (HTTP REST / SSE Streaming)
FastAPI Endpoints (apps/api)
       ↓ (Python editable imports)
Domain Packages (packages/billnyay, bimanyay, etc.)
       ↓ (Internal library dependency)
Shared Infrastructure (packages/kadi)
       ↓
PostgreSQL / pgvector + FAISS + Groq API
```

### Critical Invariants
1. **Kadi Exclusivity**: OCR parsing, Devanagari transliteration (`IndicXlit`), and cross-lingual embeddings (`IndicSBERT`) live strictly in `packages/kadi`. No domain module may implement its own private OCR or embedding layer.
2. **Zero Document Retention (BYOD)**: Uploaded hospital bills and insurance letters are processed purely in transient memory and expunged after entity extraction. No raw documents are persisted to disk.
3. **Structured Pydantic Models**: Communication across agents and API boundaries uses strictly typed Pydantic models.

---

## 5. Mobile-First & Touch Usability System

The frontend overhaul introduces comprehensive mobile-first design:
- **Responsive Viewports**: Tested and fluid across `320px`, `375px`, `390px`, `412px`, `768px`, `1024px`, and `1280px+`.
- **Minimum Touch Targets**: All interactive elements (buttons, tab selectors, language switchers, form inputs) satisfy `--min-touch-target: 44px` per WCAG 2.1 Success Criterion 2.5.5.
- **Camera Document Intake**: `<input type="file" capture="environment" />` enables single-tap camera capture of paper bills and denial letters on mobile devices.
- **Table Horizontal Wrappers**: Data-heavy audit tables (BillNyay, DawaCheck) wrap in dedicated scrolling containers (`.table-wrapper`) to eliminate viewport horizontal overflow.
- **Fluid Typography**: Uses CSS `clamp()` for headings and body copy to ensure comfortable readability on small viewports without artificial zoom.

---

## 6. Migration History & Status

| Milestone | Scope | Status | Notes |
|---|---|---|---|
| **Phase 1** | Monorepo scaffolding, Kadi, BillNyay, SchemeSetu, DawaCheck, DaaviSetu | Completed | Base modules and API wiring established |
| **Phase 2** | Repository Documentation Overhaul & Living Project Context | Completed | Master `AGENTS.md`, `PROJECT_CONTEXT.md`, structured `docs/` |
| **Phase 3** | BimaNyay Insurance Denial Module Implementation | Completed | Clause auditor (Moratorium, CRC), 3-tier drafter, SLA tracker |
| **Phase 4** | Mobile-First Trilingual Frontend Overhaul (`apps/web`) | Completed | Next.js App Router, responsive design tokens, live SSE streamer |
