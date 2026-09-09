# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- Comprehensive repository-wide documentation overhaul, including structured `/docs` architecture, ADRs, and contributor manuals.
- Scoped AI coding agent manuals (`AGENTS.md`, `apps/api/AGENTS.md`, `apps/web/AGENTS.md`, `packages/kadi/AGENTS.md`, `.github/AGENTS.md`).
- Architectural specification for `BimaNyay` (insurance claim denial dispute analysis & IRDAI 3-tier grievance escalation engine).
- Architectural roadmap for cross-platform mobile application (`apps/mobile`) in React Native / Expo.
- Dedicated GitHub issue templates (Bug Report, Feature Request) and PR Template.
- Open-source governance files (`CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, `.gitattributes`).

---

## [0.2.0] - 2026-08-20

### Added
- **Phase 1 Foundations**:
  - Implemented Kadi core extraction engine (`packages/kadi/kadi/extraction.py`) and vector store indexer (`packages/kadi/kadi/vector_store.py`).
  - Added shared OCR parser (`packages/kadi/kadi/ocr/ocr_parser.py`).
  - Integrated SchemeSetu RAG eligibility agent (`packages/schemesetu/schemesetu/agent.py`) and ONNX sentence transformer embedding fallback (`embeddings.py`).
  - Implemented DawaCheck NPPA Schedule-I ceiling price benchmarking (`packages/dawacheck/dawacheck/checker.py`).
  - Implemented DaaviSetu cashless pre-authorization form generator (`packages/daavisetu/daavisetu/generator.py`).
  - Built BillNyay 5-agent auditing chain (`auditor.py`, `clinician.py`, `regulatory.py`, `barrister.py`, `judge.py`).
  - Added real-time Server-Sent Events (SSE) patient document processing status stream (`/api/v1/kadi/cases/{case_id}/stream`).
  - Implemented PostgreSQL database models with pgvector support (`apps/api/app/models.py`).
  - Ingested raw datasets under `data/raw` (CGHS rate PDFs, handwritten prescriptions, invoice OCRs, synthetic claims).
- **CI / Testing**:
  - Configured GitHub Actions CI workflow running PostgreSQL 16 + pgvector (`.github/workflows/ci.yml`).
  - Added unit test suites across all packages and API endpoints (`test_api.py`, `test_agents.py`, `test_ocr.py`, `test_schemesetu.py`, `test_dawacheck.py`, `test_daavisetu.py`).

### Fixed
- Added missing test and serialization dependencies (`httpx`, `aiosqlite`, `python-multipart`) to ensure seamless CI execution.

---

## [0.1.0] - 2026-07-15

### Added
- Initial monorepo scaffolding (`apps/api`, `apps/web`, `packages/kadi`, `packages/billnyay`, `packages/schemesetu`, `packages/dawacheck`, `packages/daavisetu`).
- Docker Compose configuration for multi-container development (PostgreSQL + pgvector, FastAPI, Next.js).
- Technical documentation, SPPU project brief, and atomized task backlog in `docs/`.
