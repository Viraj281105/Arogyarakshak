# ArogyaRakshak — Task Backlog

Derived from `ArogyaRakshak_Technical_Documentation.md`. Each item below is sized to be one GitHub issue. Labels suggested per item: **module** (`kadi` / `billnyay` / `schemesetu` / `dawacheck` / `daavisetu` / `infra` / `frontend` / `data-qa`) and **role** (see Technical Documentation §10 — `orchestration`, `ocr-data`, `frontend`, `infra`, `data-qa`).

Phased for a 2–3 month build. Phases can overlap once Phase 0 clears — they're sequenced by dependency, not by calendar week.

---

## Phase 0 — Blockers (do first, before or at Saturday's meeting)

These block everything downstream. Nobody should start Phase 1 work until these are closed.

- [x] **[infra]** Scaffold the monorepo per Technical Documentation §9 (`apps/`, `packages/`, `data/`, `docs/`, `docker-compose.yml`)
- [x] **[infra]** Push `ArogyaRakshak_Technical_Documentation.md` and this backlog into `docs/`
- [x] **[billnyay] [orchestration]** Re-point Groq model from deprecated `llama3-70b` to `openai/gpt-oss-120b` — blocks every module that calls the LLM pipeline
- [x] **[data-qa]** Confirm with guide: can hackathon-built BillNyay code carry over directly, or must it be framed as new work?
- [x] **[data-qa]** Confirm SPPU Phase-I review date
- [x] **[data-qa]** Check whether PMJAY/MJPJAY/CGHS/NPPA source documents exist natively in Hindi/Marathi, or need LLM-generated translation — determines real scope of §5 work per data source

---

## Phase 1 — Foundations

### Kadi (shared layer — build before modules depend on it)
- [ ] **[kadi] [orchestration]** Design and migrate `cases` / `entities` / `case_entities` schema in Postgres
- [ ] **[kadi] [orchestration]** Build the shared extraction agent (any document → common entity schema)
- [ ] **[kadi] [infra]** Set up FAISS + pgvector indexes for Kadi's entity store
- [ ] **[kadi] [data-qa]** Register for ABDM Developer Sandbox & complete initial HIU flow walkthrough
- [ ] **[kadi] [data-qa]** KADI: Develop ABDM M2/M3 Sandbox FHIR-compliant resource converter (HL7 FHIR JSON mapping)

### Infra
- [ ] **[infra]** Docker Compose: Postgres+pgvector, FAISS, FastAPI, Next.js services wired together
- [ ] **[infra]** SSE streaming endpoint scaffold
- [ ] **[infra]** Basic CI: lint + test on PR (GitHub Actions)
- [ ] **[infra]** Configure monorepo build setup in Docker & setup local editable packages
- [ ] **[infra]** KADI: Develop Real-Time SSE patient document processing status stream

### Data Ingestion / Scraping
- [ ] **[billnyay] [data-qa]** CGHS rate schedule scraping/parsing into structured format
- [ ] **[schemesetu] [data-qa]** PMJAY eligibility rules + empanelled hospital list ingestion
- [ ] **[schemesetu] [data-qa]** MJPJAY (Maharashtra) eligibility rules ingestion
- [ ] **[schemesetu] [infra]** SchemeSetu: Implement local offline fallback embedding model (ONNX SentenceTransformers runtime)
- [ ] **[schemesetu] [data-qa]** SchemeSetu: Create automated web-scraping crawler for real-time PMJAY circular/policy changes
- [ ] **[dawacheck] [data-qa]** NPPA Schedule-I ceiling price list ingestion
- [ ] **[dawacheck] [infra]** DawaCheck: Create database tables for brand-to-generic formulation mappings
- [ ] **[dawacheck] [data-qa]** DawaCheck: Design automated NPPA Schedule-I PDF ceiling price list scraper and parser

---

## Phase 2 — Module builds (parallel per module)

### BillNyay (Hospital Bill Audit)
- [ ] **[billnyay] [ocr-data]** Port existing hackathon OCR pipeline into monorepo `packages/billnyay`
- [ ] **[billnyay] [orchestration]** Re-verify 5-agent pipeline (Auditor → Reviewer → Advisor → Drafter → QA Judge) against CGHS benchmarks
- [ ] **[billnyay] [orchestration]** Integrate BillNyay with Kadi (write extracted entities, read shared context)
- [ ] **[billnyay] [frontend]** Hospital overcharge audit report + representation letter PDF download flow
- [ ] **[billnyay] [orchestration]** BillNyay: Develop Auto-Audit heuristic engine matching ICD-10 codes with procedures to flag billing anomalies
- [ ] **[billnyay] [orchestration]** BillNyay: Design Multi-Agent consensus voting protocol with dynamic weights
- [ ] **[billnyay] [infra]** BillNyay: Implement hospital representation letter PDF digital signature verification and hashing
- [ ] **[billnyay] [orchestration]** BillNyay: Design self-correcting representation letter drafter feedback loops (Judge-to-Drafter auto-triggering)
- [ ] **[billnyay] [data-qa]** BillNyay: Implement clinical guideline checks using National Formulary of India (NFI)

### SchemeSetu
- [ ] **[schemesetu] [orchestration]** Build eligibility reasoning agent over PMJAY/MJPJAY RAG index
- [ ] **[schemesetu] [frontend]** Intake form UI (income, location, category, medical need)
- [ ] **[schemesetu] [orchestration]** Integrate with Kadi (read context from BillNyay/DawaCheck uploads)
- [ ] **[schemesetu] [orchestration]** SchemeSetu: Build predictive future eligibility estimator using demographic trend lines
- [ ] **[schemesetu] [orchestration]** SchemeSetu: Implement automatic Scheme-to-Scheme transition adviser (PMJAY ↔ MJPJAY)

### DawaCheck
- [ ] **[dawacheck] [ocr-data]** Medicine strip / prescription photo OCR
- [ ] **[dawacheck] [orchestration]** MRP vs NPPA ceiling price benchmarking logic
- [ ] **[dawacheck] [orchestration]** Brand ↔ generic active-ingredient mapping (shared dependency with Kadi entity resolution — see below, don't build twice)
- [ ] **[dawacheck] [orchestration]** Integrate with Kadi
- [ ] **[dawacheck] [orchestration]** DawaCheck: Implement Fuzzy Matching Brand name to Generic Formulation (Double Metaphone)
- [ ] **[dawacheck] [orchestration]** DawaCheck: Develop active-ingredient dosage normalization logic (dose proportionality matching)
- [ ] **[dawacheck] [frontend]** DawaCheck: Integrate Jan Aushadhi Store APIs and geographic store search
- [ ] **[dawacheck] [ocr-data]** DawaCheck: Implement medicine strip expiration and authenticity visual classification model
- [ ] **[dawacheck] [data-qa]** DawaCheck: Develop real-time pricing variance statistics calculator (MRP vs Ceiling curves)
- [ ] **[dawacheck] [ocr-data]** DawaCheck: Design pill shape and color verification model using OpenCV

### DaaviSetu (NEW)
- [ ] **[daavisetu] [ocr-data]** Ingest blank insurance claim and pre-authorization form templates
- [ ] **[daavisetu] [orchestration]** Map KADI patient context into cashless pre-authorization form schema
- [ ] **[daavisetu] [frontend]** Output submission-ready package (PDF + structured summary) for user review
- [ ] **[daavisetu] [ocr-data]** DaaviSetu: Ingest blank insurance claim and pre-authorization form templates for 5 major insurers
- [ ] **[daavisetu] [orchestration]** DaaviSetu: Design JSON Schema definitions for universal claim form data mapping
- [ ] **[daavisetu] [infra]** DaaviSetu: Implement automated PDF form-field coordinate mapping tool
- [ ] **[daavisetu] [infra]** DaaviSetu: Build claim package assembler zipping pre-auth PDF and bill copies
- [ ] **[daavisetu] [data-qa]** DaaviSetu: Implement OCR validation check on filled PDF fields prior to download
- [ ] **[daavisetu] [frontend]** DaaviSetu: Develop claim pre-population progress tracker UI
- [ ] **[daavisetu] [orchestration]** DaaviSetu: Implement automatic policy limit validation against estimated costs

### BimaNyay (Insurance Denials & IRDAI Appeals)
- [ ] **[bimanyay] [ocr-data]** Build OCR ingestion pipeline for insurance rejection letters and policy schedule documents
- [ ] **[bimanyay] [orchestration]** Implement ClauseAuditorAgent matching repudiation codes against IRDAI 2024 Master Circular
- [ ] **[bimanyay] [orchestration]** Implement ClinicalGroundsReviewer verifying medical necessity against discharge summaries
- [ ] **[bimanyay] [orchestration]** Build 3-tier appeal draft engine (Insurer GRO, IRDAI Bima Bharosa, Ombudsman Form VI)
- [ ] **[bimanyay] [infra]** Migrate `bimanyay_*` database tables and API endpoints (/api/v1/bimanyay)
- [ ] **[bimanyay] [frontend]** Develop BimaNyay claim denial audit dashboard and Ombudsman Form VI export
- [ ] **[bimanyay] [orchestration]** Implement self-reported Grievance SLA escalation tracker (15d GRO -> 15d Bima Bharosa -> 1y Ombudsman)
- [ ] **[bimanyay] [data-qa]** Curate synthetic dataset of 25 insurance claim denial cases with ground-truth IRDAI circular citations

### Mobile App (React Native / Expo — Fully Functional Suite)
- [ ] **[mobile] [infra]** Scaffold Expo React Native app in `apps/mobile` with TypeScript and shared API client
- [ ] **[mobile] [frontend]** Implement native edge-detection document scanner for camera bill and rejection letter capture
- [ ] **[mobile] [frontend]** Mobile BillNyay: Hospital bill camera audit, CGHS benchmark comparison, and overcharge flags
- [ ] **[mobile] [frontend]** Mobile DaaviSetu: Claim pre-auth & reimbursement auto-fill form wizard with PDF sharing
- [ ] **[mobile] [frontend]** Mobile BimaNyay: Repudiation letter audit, 3-tier appeal generator, and SLA countdown alerts
- [ ] **[mobile] [frontend]** Mobile SchemeSetu: 4-step eligibility intake questionnaire & empanelled hospital locator
- [ ] **[mobile] [frontend]** Mobile DawaCheck: Medicine strip / prescription OCR scanner & Jan Aushadhi generic locator
- [ ] **[mobile] [frontend]** Build plain-language trilingual card viewer (English, Hindi, Marathi) with audio prompt assistance
- [ ] **[mobile] [frontend]** Build one-tap portal copy helper for Bima Bharosa 2,000-character complaint field

### Shared Context / OCR Hardening
- [ ] **[kadi] [ocr-data]** KADI: Implement Self-Healing OCR Correction Loop (LLM-based spelling check)
- [ ] **[kadi] [ocr-data]** KADI: Implement Multi-Modal Document Extraction using open vision models (LLaVA/Qwen-VL)

---

## Phase 3 — Entity resolution & cross-module integration

- [ ] **[kadi] [orchestration]** String similarity scoring (edit distance / token overlap)
- [ ] **[kadi] [orchestration]** Integrate IndicXlit for transliteration matching (`pip install ai4bharat-transliteration`)
- [ ] **[kadi] [orchestration]** Integrate IndicSBERT for cross-lingual semantic matching (`l3cube-pune/indic-sentence-similarity-sbert` via `sentence-transformers`)
- [ ] **[kadi] [orchestration]** Combine signals into confidence score; implement merge / ask-user / new-entity branching
- [ ] **[kadi] [orchestration]** Auto-triggering: fire relevant module checks automatically when Kadi has enough context
- [ ] **[kadi] [frontend]** Consent UI — per-case opt-in for cross-module data sharing
- [ ] **[frontend]** Cross-module insight display (e.g. "you may also be eligible under SchemeSetu" surfaced from a BillNyay upload)
- [ ] **[kadi] [orchestration]** ABDM: Connect pulled medical history with Kadi shared case context
- [ ] **[daavisetu] [orchestration]** Integrate with Kadi context layer (read case entities to pre-fill claim forms)
- [ ] **[kadi] [ocr-data]** KADI: Implement Real-Time Clinical Named Entity Recognition utilizing localized BioBERT
- [ ] **[kadi] [orchestration]** KADI: Develop Cross-Lingual Patient Semantic Knowledge Graph using GraphDB/Neo4j
- [ ] **[kadi] [infra]** KADI: Design Federated Privacy-Preserving Case Context Sharing via Zero-Knowledge Proofs
- [ ] **[kadi] [orchestration]** KADI: Build Self-Tuning Entity Resolution Confidence Thresholds using online RLHF
- [ ] **[kadi] [orchestration]** KADI: Implement Cross-Script Soundex/Metaphone matching for Indian regional names
- [ ] **[bimanyay] [orchestration]** BimaNyay: Implement predictive outcome estimation model for IRDAI appeals
- [ ] **[dawacheck] [data-qa]** DawaCheck: Develop generic medicines awareness delivery statistics logging
- [ ] **[schemesetu] [orchestration]** SchemeSetu: Design consent-bounded scheme recommendation triggers

---

## Phase 4 — Multilingual & QA

- [ ] **[data-qa]** Build Devanagari OCR test set (real + synthetic self-donated documents)
- [ ] **[data-qa]** Build labeled entity-pair dataset to tune entity-resolution confidence thresholds
- [ ] **[data-qa]** Terminology QA pass on generated appeal letters and scheme explanations (Hindi + Marathi)
- [ ] **[frontend]** Trilingual UI pass across all screens (English/Hindi/Marathi)
- [ ] **[all-modules] [orchestration]** LLM output generation in Hindi/Marathi per module (where source data is English-only, per Phase 0 finding)
- [ ] **[kadi] [data-qa]** KADI: Design Differential Privacy noise addition for aggregate health statistics export
- [ ] **[billnyay] [data-qa]** BillNyay: Develop Hindi & Marathi custom prompt injection sanitization layer for Devanagari
- [ ] **[schemesetu] [orchestration]** SchemeSetu: Design automated regional dialect normalization agent
- [ ] **[schemesetu] [data-qa]** SchemeSetu: Develop Devanagari-grounded RAG retrieval verification agent
- [ ] **[dawacheck] [orchestration]** DawaCheck: Implement interactive prescription translator (parse abbreviations to instructions)

---

## Phase 4.5 — Evaluation & Metrics Integration Testing

- [ ] **[billnyay] [data-qa]** Eval: Implement automated pipeline for calculating Procedure Extraction Accuracy (PEA) on BillNyay mock bills
- [ ] **[billnyay] [data-qa]** Eval: Implement evaluation harness for Benchmark Mapping Accuracy (BMA) comparing hospital procedures to CGHS codes
- [ ] **[billnyay] [data-qa]** Eval: Measure Billing Anomaly Precision, Recall, and F1-score on synthetic overcharged bill data
- [ ] **[daavisetu] [data-qa]** Eval: Establish evaluation framework for DaaviSetu Claim Form Field Mapping Accuracy (CFMA) on insurer templates
- [ ] **[bimanyay] [data-qa]** Eval: Implement validation suite for BimaNyay Claim Rejection Mapping Accuracy (CRMA) against IRDAI guidelines
- [ ] **[bimanyay] [data-qa]** Eval: Implement automated completeness scoring for generated IRDAI appeal drafts using a weighted checklist
- [ ] **[dawacheck] [data-qa]** Eval: Implement testing harness for DawaCheck Medicine Recognition Accuracy comparing prescription OCR to ground truth
- [ ] **[dawacheck] [data-qa]** Eval: Measure DawaCheck NPPA price mapping accuracy and price deviation detection rates
- [ ] **[schemesetu] [data-qa]** Eval: Implement ranking evaluation (MRR - Mean Reciprocal Rank) for SchemeSetu recommendation engine
- [ ] **[schemesetu] [data-qa]** Eval: Implement RAG precision and recall evaluation for SchemeSetu recommendations
- [ ] **[kadi] [data-qa]** Eval: Build KADI integration metrics suite to measure Context Reuse Ratio (CRR) and Duplicate Processing Reduction (DPR)
- [ ] **[kadi] [data-qa]** Eval: Implement testing harness for KADI Entity Resolution Accuracy (ERA) using fuzzy matched names
- [ ] **[kadi] [data-qa]** Eval: Implement OCR benchmark suite calculating Word Error Rate (WER) and Character Error Rate (CER)
- [ ] **[billnyay] [data-qa]** Eval: Develop validation suite to calculate AI Hallucination Rate and Grounding Scores on generated legal letters
- [ ] **[infra]** Eval: Implement system-level latency monitoring to verify End-to-End Processing Time (< 10 seconds)

---

## Phase 5 — Polish & submission prep

- [ ] **[infra]** Deployment target decided and set up (college server / cloud free-tier / local demo)
- [ ] **[frontend]** End-to-end demo flow polish (one bill upload → three module insights, for the live demo)
- [ ] **[data-qa]** Blackbook / final report drafting (once guide sign-off on final scope confirmed)
- [ ] **[all]** Ask guide if anything additional is expected, once core build is stable ahead of schedule
- [ ] **[billnyay] [frontend]** BillNyay: Develop interactive conversational audit walkthrough UI
- [ ] **[billnyay] [frontend]** BillNyay: Design real-time billing anomalies visualization dashboard (HSL colors)
- [ ] **[schemesetu] [frontend]** SchemeSetu: Develop eligibility RAG citation tracing UI (inline PDF views)
- [ ] **[daavisetu] [infra]** DaaviSetu: Design secure client-side document package encryption using Web Crypto API

---

## Notes for Saturday's meeting

- Phase 0 should ideally be closed *before* Saturday, or be the first thing assigned.
- Assign Phase 1–2 by role first (matches Technical Documentation §10), not by module — Kadi and infra need dedicated owners since every module depends on them.
- Don't assign Phase 3 (entity resolution) until Phase 1's Kadi schema and Phase 2's module integrations are stable — it depends on both.
