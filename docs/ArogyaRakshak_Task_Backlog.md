# ArogyaRakshak — Task Backlog

Derived from `ArogyaRakshak_Technical_Documentation.md`. Each item below is sized to be one GitHub issue. Labels suggested per item: **module** (`kadi` / `billnyay` / `schemesetu` / `dawacheck` / `infra` / `frontend` / `data-qa`) and **role** (see Technical Documentation §10 — `orchestration`, `ocr-data`, `frontend`, `infra`, `data-qa`).

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

### Infra
- [ ] **[infra]** Docker Compose: Postgres+pgvector, FAISS, FastAPI, Next.js services wired together
- [ ] **[infra]** SSE streaming endpoint scaffold
- [ ] **[infra]** Basic CI: lint + test on PR (GitHub Actions)

### Data ingestion (can run in parallel across data sources)
- [ ] **[billnyay] [data-qa]** CGHS rate schedule scraping/parsing into structured format
- [ ] **[schemesetu] [data-qa]** PMJAY eligibility rules + empanelled hospital list ingestion
- [ ] **[schemesetu] [data-qa]** MJPJAY (Maharashtra) eligibility rules ingestion
- [ ] **[dawacheck] [data-qa]** NPPA Schedule-I ceiling price list ingestion

---

## Phase 2 — Module builds (parallel per module)

### BillNyay
- [ ] **[billnyay] [ocr-data]** Port existing hackathon OCR pipeline into monorepo `packages/billnyay`
- [ ] **[billnyay] [orchestration]** Re-verify 5-agent pipeline (Auditor → Reviewer → Advisor → Drafter → QA Judge) against new stack
- [ ] **[billnyay] [orchestration]** Integrate BillNyay with Kadi (write extracted entities, read shared context)
- [ ] **[billnyay] [frontend]** Appeal PDF generation + download flow

### SchemeSetu
- [ ] **[schemesetu] [orchestration]** Build eligibility reasoning agent over PMJAY/MJPJAY RAG index
- [ ] **[schemesetu] [frontend]** Intake form UI (income, location, category, medical need)
- [ ] **[schemesetu] [orchestration]** Integrate with Kadi (read context from BillNyay/DawaCheck uploads)

### DawaCheck
- [ ] **[dawacheck] [ocr-data]** Medicine strip / prescription photo OCR
- [ ] **[dawacheck] [orchestration]** MRP vs NPPA ceiling price benchmarking logic
- [ ] **[dawacheck] [orchestration]** Brand ↔ generic active-ingredient mapping (shared dependency with Kadi entity resolution — see below, don't build twice)
- [ ] **[dawacheck] [orchestration]** Integrate with Kadi

---

## Phase 3 — Entity resolution & cross-module integration

- [ ] **[kadi] [orchestration]** String similarity scoring (edit distance / token overlap)
- [ ] **[kadi] [orchestration]** Integrate IndicXlit for transliteration matching (`pip install ai4bharat-transliteration`)
- [ ] **[kadi] [orchestration]** Integrate IndicSBERT for cross-lingual semantic matching (`l3cube-pune/indic-sentence-similarity-sbert` via `sentence-transformers`)
- [ ] **[kadi] [orchestration]** Combine signals into confidence score; implement merge / ask-user / new-entity branching
- [ ] **[kadi] [orchestration]** Auto-triggering: fire relevant module checks automatically when Kadi has enough context
- [ ] **[kadi] [frontend]** Consent UI — per-case opt-in for cross-module data sharing
- [ ] **[frontend]** Cross-module insight display (e.g. "you may also be eligible under SchemeSetu" surfaced from a BillNyay upload)

---

## Phase 4 — Multilingual & QA

- [ ] **[data-qa]** Build Devanagari OCR test set (real + synthetic self-donated documents)
- [ ] **[data-qa]** Build labeled entity-pair dataset to tune entity-resolution confidence thresholds
- [ ] **[data-qa]** Terminology QA pass on generated appeal letters and scheme explanations (Hindi + Marathi)
- [ ] **[frontend]** Trilingual UI pass across all screens (English/Hindi/Marathi)
- [ ] **[billnyay/schemesetu/dawacheck] [orchestration]** LLM output generation in Hindi/Marathi per module (where source data is English-only, per Phase 0 finding)

---

## Phase 5 — Polish & submission prep

- [ ] **[infra]** Deployment target decided and set up (college server / cloud free-tier / local demo)
- [ ] **[frontend]** End-to-end demo flow polish (one bill upload → three module insights, for the live demo)
- [ ] **[data-qa]** Blackbook / final report drafting (once guide sign-off on final scope confirmed)
- [ ] **[all]** Ask guide if anything additional is expected, once core build is stable ahead of schedule

---

## Notes for Saturday's meeting

- Phase 0 should ideally be closed *before* Saturday, or be the first thing assigned.
- Assign Phase 1–2 by role first (matches Technical Documentation §10), not by module — Kadi and infra need dedicated owners since every module depends on them.
- Don't assign Phase 3 (entity resolution) until Phase 1's Kadi schema and Phase 2's module integrations are stable — it depends on both.
