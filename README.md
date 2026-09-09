<div align="center">

# ArogyaRakshak (आरोग्यरक्षक)

[![CI Pipeline](https://github.com/Viraj281105/Arogyarakshak/actions/workflows/ci.yml/badge.svg)](https://github.com/Viraj281105/Arogyarakshak/actions/workflows/ci.yml)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-15%2F16-000000.svg?logo=next.js&logoColor=white)](https://nextjs.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16%2Bpgvector-4169E1.svg?logo=postgresql&logoColor=white)](https://github.com/pgvector/pgvector)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![BYOD Privacy](https://img.shields.io/badge/Privacy-BYOD%20Zero--Retention-success.svg)](#-privacy--zero-retention-byod-architecture)

**An intelligent, multi-agent healthcare decision-support platform designed to protect Indian patients from hospital overbilling, wrongful insurance claim repudiation, scheme unawareness, and inflated medicine prices.**

*B.E. Computer Engineering Final Year Project | PES Modern College of Engineering, Pune | SPPU 2019 Pattern*  
*Team Lead: Viraj Jadhao | Status: Active Engineering & Evaluation*

[Explore Docs](docs/README.md) · [System Architecture](docs/architecture/overview.md) · [API Reference](docs/api/overview.md) · [Quickstart](#-quickstart--local-development) · [Contributing](CONTRIBUTING.md)

</div>

---

## 📖 Table of Contents
1. [The Problem ArogyaRakshak Solves](#-the-problem-arogyarakshak-solves)
2. [Core Capabilities & Modules](#-core-capabilities--modules)
3. [Zero-Overlap Architecture & Kadi Layer](#-zero-overlap-architecture--kadi-layer)
4. [Technology Stack](#-technology-stack)
5. [Repository Monorepo Layout](#-repository-monorepo-layout)
6. [Quickstart & Local Development](#-quickstart--local-development)
7. [Testing & Evaluation Benchmarks](#-testing--evaluation-benchmarks)
8. [Configuration & Environment Variables](#-configuration--environment-variables)
9. [Troubleshooting & Common Failure Modes](#-troubleshooting--common-failure-modes)
10. [Privacy & Zero-Retention BYOD Architecture](#-privacy--zero-retention-byod-architecture)
11. [Contributing & Development Community](#-contributing--development-community)
12. [Documentation Hub](#-documentation-hub)

---

## 🚨 The Problem ArogyaRakshak Solves

Every day across India, patients and families face catastrophic healthcare expenses compounded by institutional friction:
- **Hospital Overcharging**: Opaque hospital bills charging 2x to 5x above government benchmark rates for basic procedures and consumables.
- **Wrongful Insurance Claim Repudiations**: Insurers rejecting valid claims under arbitrary clauses (e.g. citing pre-existing conditions on policies active for more than 5 years, violating the **IRDAI 2024 Master Circular**).
- **Government Welfare Disconnect**: Millions of low-income families are entitled to free tertiary healthcare under **PMJAY** (national) or **MJPJAY** (Maharashtra), but lack visibility into eligibility or empanelled network hospitals.
- **Pharmaceutical Markups**: Branded medicines are purchased at retail MRP when identical bioequivalent generic formulations exist at **PMBJP Jan Aushadhi Kendras** for 50% to 90% less.

**ArogyaRakshak** solves this through a unified, patient-centric AI platform accessible via web and mobile in **English, Hindi, and Marathi**.

---

## ⚡ Core Capabilities & Modules

ArogyaRakshak coordinates five specialized domain modules through a central intelligence layer:

```mermaid
flowchart TD
    Doc["Patient Document Upload<br/>(Bill / Prescription / Denial Letter / Policy)"]
    
    subgraph KadiLayer ["Kadi Shared Intelligence Layer"]
        OCR["Multilingual OCR (Devanagari + Latin)"]
        Extract["Entity Normalization (ICD-10, Meds, Procedures)"]
        Resolve["Entity Resolution (IndicXlit + IndicSBERT)"]
    end

    Doc --> OCR --> Extract --> Resolve

    Resolve --> BN["1. BillNyay<br/>Hospital Bill Audit vs CGHS"]
    Resolve --> DS["2. DaaviSetu<br/>Claim Application & Pre-Auth Filler"]
    Resolve --> BMN["3. BimaNyay<br/>Denial Audit & IRDAI Appeal Tracker"]
    Resolve --> SS["4. SchemeSetu<br/>PMJAY / MJPJAY Welfare Eligibility"]
    Resolve --> DC["5. DawaCheck<br/>NPPA Price Check & Jan Aushadhi Generics"]
```

| Module | Core Purpose | Ground-Truth Benchmark | Primary Outputs |
|---|---|---|---|
| **[BillNyay](packages/billnyay)** | **Hospital Bill Audit** | **CGHS Rate Schedules** | Line-item overcharge audit report; formal overcharge dispute representation letter to hospital billing. |
| **[DaaviSetu](packages/daavisetu)** | **Claim Application Automation** *(Pre-Claim)* | **Standard Insurer Templates** | Pre-populated cashless pre-authorization form; reimbursement claim package ready for portal submission. |
| **[BimaNyay](packages/bimanyay)** | **Denial Disputes & Appeals** *(Post-Denial)* | **IRDAI 2024 Master Circular** | Legal audit of repudiation codes (5-yr moratorium, TAT breaches); 3-tier appeals (GRO, Bima Bharosa, Ombudsman Form VI); statutory SLA countdown tracker. |
| **[SchemeSetu](packages/schemesetu)** | **Healthcare Scheme Advisor** | **PMJAY & MJPJAY Rules** | 4-question eligibility determination; benefit guides; nearby empanelled network hospital locator. |
| **[DawaCheck](packages/dawacheck)** | **Medicine Pricing & Generics** | **NPPA Schedule-I Price Orders** | MRP overcharge detection against price caps; bioequivalent generic substitutes; nearest Jan Aushadhi store map. |

---

## 🧩 Zero-Overlap Architecture & Kadi Layer

To preserve maintainability, no two modules perform overlapping tasks:
- **Kadi (`packages/kadi`)** is pure shared infrastructure. It contains zero pricing or legal rules; it solely extracts, normalizes, and shares entities.
- **BillNyay** audits hospital bills against CGHS rates and leaves insurance to DaaviSetu/BimaNyay.
- **DaaviSetu** handles pre-claim application filing, handing off denied claims to BimaNyay.
- **BimaNyay** handles post-denial appeals and IRDAI grievance tracking.
- **SchemeSetu** handles government welfare schemes and leaves private commercial insurance to DaaviSetu/BimaNyay.
- **DawaCheck** handles retail pharmacy pricing and leaves hospital procedure bills to BillNyay.

---

## 💻 Technology Stack

- **Backend**: [FastAPI](https://fastapi.tiangolo.com) 0.115 with asynchronous request pipeline (`uvicorn`, `asyncpg`, `pydantic-settings`).
- **Database & Search**: [PostgreSQL 16](https://www.postgresql.org) with [pgvector](https://github.com/pgvector/pgvector) extension, plus in-memory [FAISS](https://github.com/facebookresearch/faiss) similarity indexes.
- **LLM Reasoning**: [Groq Cloud](https://groq.com) high-speed inference engine (Default model: `openai/gpt-oss-120b`).
- **Indic NLP**: **IndicXlit** (AI4Bharat phonetic transliteration) and **IndicSBERT** (L3Cube Pune multilingual embeddings).
- **Web Frontend**: [Next.js 15/16](https://nextjs.org) App Router, React 19, TypeScript, Vanilla CSS design tokens.
- **Mobile App**: [React Native](https://reactnative.dev) with Expo, native edge-detection document scanner.
- **Containerization**: Docker Compose v2.

---

## 📂 Repository Monorepo Layout

```text
arogyarakshak/
├── apps/
│   ├── api/                     # FastAPI backend application
│   │   ├── app/api/v1/          # Versioned REST endpoints (kadi, billnyay, etc.)
│   │   ├── app/main.py          # App lifespan, CORS, and global error handlers
│   │   ├── app/models.py        # SQLAlchemy models (kadi_cases, kadi_entities)
│   │   └── tests/               # Backend integration test suite
│   ├── web/                     # Next.js 15 App Router web client
│   └── mobile/                  # React Native / Expo cross-platform mobile application
├── packages/                    # Python domain libraries (installed via pip -e)
│   ├── kadi/                    # Shared context: OCR, extraction, FAISS vector store
│   ├── billnyay/                # 5-agent hospital bill auditing chain
│   ├── daavisetu/               # Claim pre-authorization form generator
│   ├── bimanyay/                # Claim denial dispute analysis & IRDAI appeals
│   ├── schemesetu/              # RAG eligibility agent & local embedding fallback
│   └── dawacheck/               # NPPA Schedule-I medicine pricing & generic mapping
├── data/                        # Government rate schedules (CGHS) and raw benchmarks
├── docs/                        # Complete technical specifications, ADRs & guides
│   ├── architecture/            # System overview, component breakdown, and ADRs
│   ├── development/             # Setup, workflow, testing, and troubleshooting
│   └── configuration/           # Environment variable reference
├── .github/                     # Workflows (ci.yml), templates, CODEOWNERS
└── docker-compose.yml           # PostgreSQL+pgvector, API, and Web container spec
```

---

## 🚀 Quickstart & Local Development

### Prerequisites
- **Git**
- **Python 3.11+**
- **Node.js 18+** or **20+**
- **Docker Desktop** (with Docker Compose v2)

### Step 1: Clone Repository
```bash
git clone https://github.com/Viraj281105/Arogyarakshak.git
cd Arogyarakshak
```

### Step 2: Configure Environment Variables
```bash
cp .env.example .env
```
Populate `.env` with your credentials:
```env
GROQ_API_KEY=gsk_your_groq_key_here
GROQ_MODEL=openai/gpt-oss-120b
DATABASE_URL=postgresql://arogyarakshak:arogyarakshak@postgres:5432/arogyarakshak
```

### Step 3: Run with Docker Compose
```bash
docker-compose up --build
```
Once initialized, access services at:
- **Web Application**: [http://localhost:3000](http://localhost:3000)
- **FastAPI Gateway**: [http://localhost:8000](http://localhost:8000)
- **Interactive Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Check**: [http://localhost:8000/health](http://localhost:8000/health)

### Running Locally Outside Docker
For rapid development without container builds, see the [Developer Setup Guide](docs/development/setup.md).

---

## 🧪 Testing & Evaluation Benchmarks

Run unit and integration test suites:

```bash
# Run all package unit tests (12 tests)
python -m pytest packages/

# Run API integration tests (4 tests)
cd apps/api
python -m pytest tests/
cd ../..

# Run frontend linting
cd apps/web
npm run lint
cd ../..
```

For evaluation benchmark targets (PEA, BMA, CFMA, CRMA, WER/CER), see the [Testing Guide](docs/development/testing.md).

---

## ⚙️ Configuration & Environment Variables

Key runtime environment variables:

| Variable | Required | Default Value | Description |
|---|---|---|---|
| `GROQ_API_KEY` | Yes (for AI agents) | `""` | Groq inference API key. |
| `GROQ_MODEL` | No | `openai/gpt-oss-120b` | Model ID. Never use deprecated `llama3-70b`. |
| `DATABASE_URL` | Yes | `postgresql://...` | Full async PostgreSQL connection URI. |
| `CORS_ORIGINS` | No | `*` | Allowed origins for browser client requests. |

Complete configuration specifications are in the [Environment Variables Guide](docs/configuration/environment-variables.md).

---

## 🛠️ Troubleshooting & Common Failure Modes

- **`ModuleNotFoundError: No module named 'kadi'`**: Run `pip install -e packages/kadi` (and other packages) in your active virtualenv.
- **`OperationalError: could not translate host name "postgres"`**: When running `apps/api` outside Docker, update `DATABASE_URL` to point to `localhost:5432`.
- **`Model 'llama3-70b' is deprecated`**: Set `GROQ_MODEL=openai/gpt-oss-120b` in `.env`.

See the full [Troubleshooting Guide](docs/development/troubleshooting.md) for detailed diagnostics.

---

## 🔒 Privacy & Zero-Retention BYOD Architecture

ArogyaRakshak operates on a strict **Bring-Your-Own-Document (BYOD)** privacy principle:
1. **No Persistent Document Storage**: Patient bills, discharge summaries, and prescriptions are processed strictly in transient memory (RAM) and immediately purged upon extraction completion.
2. **Consent Boundary**: Cross-module data sharing through Kadi requires explicit per-case patient opt-in (`consent_opt_in`).
3. **De-Identified Entities**: Persistent database records retain only de-identified clinical metadata (procedure codes, medicines, pricing line items) linked to an ephemeral session UUID.

Read our full [Security Policy](SECURITY.md) and [ADR-003](docs/architecture/decisions/ADR-003-bring-your-own-document-privacy.md).

---

## 🤝 Contributing & Development Community

We welcome contributions from developers, researchers, and healthcare professionals!
- Review the [Contributing Guidelines](CONTRIBUTING.md).
- Adhere to the [Code of Conduct](CODE_OF_CONDUCT.md).
- AI coding agents must follow [AGENTS.md](AGENTS.md).
- See our historical progress in [CHANGELOG.md](CHANGELOG.md).

---

## 📚 Documentation Hub

Explore our structured documentation in the [`docs/`](docs/) directory:
- **[Documentation Portal Index](docs/README.md)**
- **[System Architecture Overview](docs/architecture/overview.md)**
- **[Component Specifications & Non-Overlap Matrix](docs/architecture/components.md)**
- **[Data Flow & SSE Streaming Protocol](docs/architecture/data-flow.md)**
- **[Architecture Decision Records (ADRs)](docs/architecture/decisions/)**
- **[Developer Setup Guide](docs/development/setup.md)**
- **[Git Workflow & Commit Standards](docs/development/workflow.md)**
- **[Testing & Evaluation Guide](docs/development/testing.md)**
- **[Troubleshooting Guide](docs/development/troubleshooting.md)**
- **[Environment Variables Reference](docs/configuration/environment-variables.md)**
- **[REST API Reference](docs/api/overview.md)**
- **[BimaNyay & Mobile App Blueprint](docs/BimaNyay_and_Mobile_Architecture.md)**
- **[Project Task Backlog](docs/ArogyaRakshak_Task_Backlog.md)**

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
