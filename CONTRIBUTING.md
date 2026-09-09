# Contributing to ArogyaRakshak (आरोग्यरक्षक)

Thank you for your interest in contributing to **ArogyaRakshak**! This repository is a patient-facing decision-support monorepo built using FastAPI, Next.js, PostgreSQL/pgvector, FAISS, and Groq.

We welcome contributions from developers, healthcare researchers, data scientists, and UI/UX designers. Please take a few minutes to review these guidelines before getting started.

---

## Table of Contents
1. [Core Ground Rules](#core-ground-rules)
2. [Monorepo Architecture Overview](#monorepo-architecture-overview)
3. [Prerequisites & Development Environment](#prerequisites--development-environment)
4. [Local Setup Guide](#local-setup-guide)
5. [Development Workflow & Git Guidelines](#development-workflow--git-guidelines)
6. [Testing & Validation Requirements](#testing--validation-requirements)
7. [Coding Standards & Conventions](#coding-standards--conventions)
8. [Pull Request Process](#pull-request-process)
9. [Reporting Bugs & Proposing Features](#reporting-bugs--proposing-features)

---

## 1. Core Ground Rules

Every contributor must adhere strictly to the project's foundational constraints:

- **Bring-Your-Own-Document (BYOD) Privacy**: ArogyaRakshak has a **zero-retention policy** for patient documents. Never persistently store uploaded patient PDFs or images on disk or database beyond the active session. All OCR buffers are processed in transient memory.
- **Model Grounding**: Never hardcode or call deprecated Groq models (`llama3-70b` or `llama-3.3-70b-versatile`). Always read from `GROQ_MODEL` environment variable (default: `openai/gpt-oss-120b`).
- **Naming Conventions**:
  - Python packages are strictly lowercase: `kadi`, `billnyay`, `daavisetu`, `bimanyay`, `schemesetu`, `dawacheck`.
  - Database tables use module prefixes: `kadi_*`, `billnyay_*`, `daavisetu_*`, `bimanyay_*`, `schemesetu_*`, `dawacheck_*`.
  - API endpoints follow versioned routing: `/api/v1/<module>/...`.
- **Kadi Layer Exclusivity**: Cross-module entity extraction, phonetic transliteration (IndicXlit), and semantic cross-lingual matching (IndicSBERT) belong **exclusively in `packages/kadi`**. Do not duplicate extraction pipelines inside individual module packages.

---

## 2. Monorepo Architecture Overview

The repository is organized as a unified monorepo:

```text
arogyarakshak/
├── apps/
│   ├── api/             # FastAPI asynchronous backend application
│   ├── web/             # Next.js 15 App Router web client
│   └── mobile/          # React Native / Expo mobile application (planned)
├── packages/            # Domain logic libraries (editable python packages)
│   ├── kadi/            # Shared context, entity resolution, vector stores
│   ├── billnyay/        # Hospital bill audit vs CGHS rates
│   ├── daavisetu/       # Pre-authorization & claim form filling
│   ├── bimanyay/        # Insurance claim denial audit, IRDAI appeals & SLA tracking
│   ├── schemesetu/      # PMJAY & MJPJAY eligibility reasoning
│   └── dawacheck/       # NPPA Schedule-I medicine pricing & generic mapping
├── data/                # Ingestion scripts and public government reference data
├── docs/                # Architecture specifications, guides, and ADRs
└── docker-compose.yml   # Orchestrates PostgreSQL+pgvector, API, and Web
```

---

## 3. Prerequisites & Development Environment

Ensure your development machine has:
- **Python 3.11+** (Python 3.11 is used in production and CI)
- **Node.js 18+** or **Node.js 20+** with `npm`
- **Docker Desktop** (with Docker Compose v2)
- **Git**

---

## 4. Local Setup Guide

### 4.1 Clone Repository
```bash
git clone https://github.com/Viraj281105/Arogyarakshak.git
cd Arogyarakshak
```

### 4.2 Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Populate your `.env` file with your Groq API key and database credentials:
```env
GROQ_API_KEY=gsk_your_groq_api_key_here
GROQ_MODEL=openai/gpt-oss-120b
DATABASE_URL=postgresql://arogyarakshak:arogyarakshak@localhost:5432/arogyarakshak
```

### 4.3 Python Environment & Editable Packages Setup
We strongly recommend creating a virtual environment:
```bash
python -m venv .venv
# On Windows (PowerShell):
.venv\Scripts\Activate.ps1
# On Linux/macOS:
source .venv/bin/activate
```

Install backend dependencies and register all monorepo packages as editable (`-e`):
```bash
python -m pip install --upgrade pip
pip install -r apps/api/requirements.txt
pip install -e packages/kadi
pip install -e packages/billnyay
pip install -e packages/daavisetu
pip install -e packages/schemesetu
pip install -e packages/dawacheck
pip install pytest pytest-asyncio aiosqlite httpx
```

### 4.4 Frontend Setup
```bash
cd apps/web
npm install
cd ../..
```

---

## 5. Development Workflow & Git Guidelines

### 5.1 Branch Naming Conventions
- `feature/<module>-<description>` (e.g., `feature/bimanyay-sla-tracker`)
- `fix/<module>-<description>` (e.g., `fix/kadi-ocr-cropping`)
- `docs/<description>` (e.g., `docs/update-architecture-overview`)
- `refactor/<description>` (e.g., `refactor/api-lifespan`)

### 5.2 Commit Message Standards
Follow [Conventional Commits](https://www.conventionalcommits.org/):
- `feat(bimanyay): add IRDAI Ombudsman Form VI generator`
- `fix(billnyay): resolve rounding error in CGHS procedure benchmark`
- `docs(kadi): update entity resolution confidence threshold formulas`
- `test(dawacheck): add test cases for Schedule-I NPPA ceiling checks`

---

## 6. Testing & Validation Requirements

Before pushing or opening a PR, ensure all automated validation steps pass:

### 6.1 Run Backend & Package Tests
```bash
# Run API integration tests
cd apps/api
python -m pytest

# Run all package unit tests from root
cd ../..
python -m pytest packages/
```

### 6.2 Run Frontend Linter
```bash
cd apps/web
npm run lint
```

### 6.3 Verify Local API Endpoint
With services running (via `docker-compose up` or local `uvicorn app.main:app --reload`):
```bash
curl http://localhost:8000/health
# Expected: {"status":"ok","version":"1.0.0"}
```

---

## 7. Coding Standards & Conventions

### 7.1 Python Standards
- Adhere to **PEP 8** formatting.
- Use explicit Python type hints (`typing` / Pydantic models).
- Multi-agent pipelines (such as BillNyay and BimaNyay) must keep each agent's logic and prompt in a **separate function or file**—do not collapse them into a single monolithic prompt.
- Communicate between agent stages using structured **Pydantic models / JSON schemas**, not unstructured free-form text.

### 7.2 Frontend Standards
- Built on Next.js 15/16 App Router.
- Write modular, semantic HTML components.
- Prepare all user-facing strings for i18n localization (English, Hindi, Marathi).

---

## 8. Pull Request Process

1. Fork the repository and create your branch from `main`.
2. Ensure new features are accompanied by tests.
3. Update relevant documentation in `docs/` and package `README.md`.
4. Open a Pull Request referencing the related issue or task backlog item.
5. Complete the PR checklist defined in `.github/PULL_REQUEST_TEMPLATE.md`.
6. Await code review and approval from repository maintainers (`@Viraj281105`).

---

## 9. Reporting Bugs & Proposing Features

- **Bug Reports**: Use the [Bug Report template](.github/ISSUE_TEMPLATE/bug_report.md) with complete logs and reproduction steps.
- **Feature Requests**: Use the [Feature Request template](.github/ISSUE_TEMPLATE/feature_request.md), ensuring any government rates or circulars cited include verifiable public provenance.
- **Security Vulnerabilities**: Please review [SECURITY.md](SECURITY.md) for responsible disclosure procedures.
