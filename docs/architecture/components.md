# Component Specifications

This document outlines the detailed responsibilities, internal architecture, and boundaries of each component in **ArogyaRakshak**.

---

## 1. Kadi — Shared Intelligence & Context Layer (`packages/kadi`)

Kadi (कड़ी — "link in a chain") is the connective infrastructure that enables multi-module interoperability without requiring duplicate patient uploads.

### Core Responsibilities
- **Document Normalization**: Parses unstructured bills, prescriptions, policy wordings, and denial letters into a standard JSON schema:
  - Patient demographics (name, age, gender).
  - Hospital metadata (facility name, admission/discharge dates).
  - Diagnoses & procedure codes (ICD-10 mapping).
  - Medications (brand, active ingredient, dosage, quantity).
  - Billing line items (room rent, ICU, procedures, consultations, consumables).
- **Entity Resolution** (`kadi/resolution/`, ADR-006):
  - Catches spelling and qualifier variations via edit distance and fuzzy token overlap, with deterministic conflict guards for strength, dosage form, laterality, variant letters and opposite prefixes (#28).
  - Matches names across Latin and Devanagari scripts with rule-based romanization and Indic phonetic keys (#89). **IndicXlit** (AI4Bharat) is *not used*: its fairseq dependency has no Python 3.11 wheels (#29, open).
  - Optionally matches cross-lingual translated concepts (e.g. *Fever* ↔ *बुखार*) with **IndicSBERT** (L3Cube). Off by default (`KADI_SEMANTIC_MATCHING`, #30); semantic similarity can lead to an ask, never to a merge.
  - Merge / ask-user / new-entity branching (#31); thresholds are recalibrated from user answers with a bounded deterministic procedure — not RLHF (#88). Evaluated on a hand-curated synthetic pair set (`docs/evaluation/entity-resolution.md`).
- **Case Knowledge Graph** (`kadi/graph.py`, #86): on-request node-link projection of a case's entities with evidence on every edge. There is no graph database, and no clinical relationships are inferred.
- **ABDM Record Import** (`kadi/fhir_import.py`, #54): parses a client-supplied FHIR R4 bundle into case context through entity resolution. There is no live ABDM gateway pull (sandbox registration is pending) and no NRCeS profile validation.
- **Auto-Triggering** (`kadi/triggers.py`, `apps/api/app/auto_triggers.py`, #32): consent-bounded, read-only module checks run when a case has enough context; DaaviSetu claims are never auto-run.
- **Consent Boundary**: Enforces patient opt-in (`consent_opt_in`) before sharing extracted context across modules. Federated / zero-knowledge consent verification across nodes is a design only (ADR-007).
- **In-Memory Vector Search** *(planned)*: `kadi/vector_store.py` is a scaffold for FAISS/pgvector indexes. It contains no FAISS and is not wired into any endpoint.
- **Direct-Identifier Redaction**: `kadi/redaction.py` strips names, contact details and government IDs from any text retained after extraction (ADR-003).

---

## 2. BillNyay — Hospital Bill Auditing (`packages/billnyay`)

BillNyay audits itemized hospital bills against government benchmarks and clinical necessity guidelines.

### Core Responsibilities
- **CGHS Rate Benchmarking**: Compares line items against official Central Government Health Scheme (CGHS) price caps for NABH-accredited and non-NABH hospitals across Tier-1, Tier-2, and Tier-3 cities.
- **Billing Anomaly Heuristics**: Flags unbundled procedures, excessive room rent compounding, and non-allowable consumable charges.
- **5-Agent Multi-Agent Chain**:
  1. `DocumentAuditor`: Categorizes and benchmarks bill charges against CGHS codes.
  2. `ClinicalReviewer`: Audits medical necessity and identifies duplicate charges.
  3. `RegulatoryAdvisor`: Flags violations of hospital pricing notifications and Consumer Protection regulations.
  4. `AppealDrafter / Barrister`: Formats an evidence-backed overcharge representation letter addressed to hospital billing management.
  5. `QAJudge`: Evaluates factual precision, eliminates hallucinations, and ensures consensus before outputting the final PDF report.

---

## 3. DaaviSetu — Claim Application Form Automation (`packages/daavisetu`)

DaaviSetu governs the **pre-claim submission lifecycle** for private commercial health insurance.

### Core Responsibilities
- **Cashless Pre-Authorization Pre-Filling**: Ingests patient details, treating doctor diagnosis, and estimated hospitalization costs from Kadi and auto-populates standardized cashless pre-auth request templates.
- **Reimbursement Claim Assembler**: Maps patient bills and diagnostic summaries into insurer reimbursement claim schemas (Star Health, Care Health, HDFC Ergo, ICICI Lombard, etc.).
- **Boundary**: DaaviSetu only generates initial claim application packages. If an insurer subsequently rejects or reduces the claim, the case is handed off to **BimaNyay**.

---

## 4. BimaNyay — Claim Denial Appeals & Grievance Tracking (`packages/bimanyay`)

BimaNyay governs the **post-denial dispute and grievance escalation lifecycle**.

### Core Responsibilities
- **Repudiation Letter OCR & Clause Matching**: Ingests insurance rejection letters and policy schedules, extracting cited exclusion codes.
- **IRDAI Regulatory Violation Audit**: Audits repudiations against the **IRDAI Master Circular (May 29, 2024)**:
  - **5-Year Moratorium Rule**: Bars contesting pre-existing conditions after 5 continuous policy years.
  - **Claims Review Committee (CRC) Mandate**: Ensures repudiation had formal CRC approval.
  - **Cashless Turnaround Times**: Checks if pre-auth (1 hour) or final discharge (3 hours) exceeded statutory SLAs.
- **3-Tier Statutory Appeal Drafter**:
  - **Tier 1**: Formal appeal to Insurer Grievance Redressal Officer (GRO).
  - **Tier 2**: Pre-formatted 2,000-character complaint for IRDAI Bima Bharosa portal.
  - **Tier 3**: Standardized Insurance Ombudsman Form VI (Rule 14(1)(b)) petition package.
- **Grievance SLA Tracking Engine**: Self-reported progress tracker with automated countdowns for the 15-day GRO window, 15-day Bima Bharosa SLA, and 1-year Ombudsman limitation deadline.

---

## 5. SchemeSetu — Healthcare Welfare Scheme Advisor (`packages/schemesetu`)

SchemeSetu connects underprivileged citizens with public healthcare coverage.

### Core Responsibilities
- **Eligibility Reasoning Agent**: Evaluates household income, ration card category (Yellow/Orange/White), and medical needs against:
  - **PMJAY** (Ayushman Bharat, national safety net up to ₹5 Lakh/family/year).
  - **MJPJAY** (Mahatma Jyotirao Phule Jan Arogya Yojana, Maharashtra state scheme).
- **Local Embedding Fallback** *(scaffold, unwired)*: `schemesetu/embeddings.py` provides an offline SentenceTransformer fallback. It contains no ONNX runtime and is not used by eligibility checking.
- **Empanelled Hospital Directory**: Identifies nearby public and private hospitals empanelled under PMJAY and MJPJAY.

---

## 6. DawaCheck — Medicine Pricing & Generic Alternatives (`packages/dawacheck`)

DawaCheck empowers patients to reduce recurring pharmaceutical expenses.

### Core Responsibilities
- **NPPA Schedule-I Price Verification**: Compares retail drug MRP against ceiling prices fixed by the National Pharmaceutical Pricing Authority (NPPA) under the Drugs (Prices Control) Order (DPCO).
- **Active Ingredient Normalization**: Maps branded formulations to their active chemical salt and dosage strength.
- **Jan Aushadhi Generic Substitutes**: Suggests bioequivalent generic alternatives available at Pradhan Mantri Bhartiya Janaushadhi Kendras (PMBJP), typically saving 50% to 90%.

---

## 7. Apps & User Interfaces

### `apps/api` (FastAPI Backend)
- Exposes versioned `/api/v1` REST endpoints for all modules.
- Provides real-time Server-Sent Events (SSE) progress streams via `/api/v1/kadi/cases/{case_id}/stream`.
- Manages asynchronous PostgreSQL sessions and startup schema synchronization.

### `apps/web` (Next.js 15 Client)
- Responsive web portal built with Next.js App Router and React 19.
- Subscribes to live SSE status events to render multi-agent reasoning progress in real time.
- Trilingual scaffolding supporting English, Hindi, and Marathi.

### `apps/mobile` (React Native / Expo Client)
- Native mobile application designed for patients at hospital billing desks.
- Edge-detection camera scanner with perspective correction for crumpled receipts and prescription strips.
- Plain-language dispute cards and background push notification alerts for statutory grievance SLAs.

---

## 8. Zero-Overlap Boundary Matrix

| Module | Primary Scope (What It OWNS) | Out of Scope (What It DOES NOT DO) |
|---|---|---|
| **Kadi** | Shared entity extraction, entity resolution (incl. rule-based cross-script), case graph projection, ABDM bundle import, auto-triggers, consent. (Vector store: unwired scaffold.) | No legal rules, no pricing benchmarks. |
| **BillNyay** | Hospital bill line items vs CGHS rates; hospital overcharge appeals. | Does not audit insurance denials or check drug MRPs. |
| **DaaviSetu** | Pre-claim cashless pre-auth & reimbursement application forms. | Does not handle denials, appeals, or hospital rates. |
| **BimaNyay** | Post-denial insurance repudiation audit, IRDAI appeals, SLA tracking. | Does not audit hospital bills vs CGHS (leaves to BillNyay). |
| **SchemeSetu** | PMJAY & MJPJAY government welfare eligibility and hospital directory. | Does not handle commercial health insurance. |
| **DawaCheck** | Medicine MRP vs NPPA ceiling prices; Jan Aushadhi generic alternatives. | Does not audit hospital procedures or claim forms. |
