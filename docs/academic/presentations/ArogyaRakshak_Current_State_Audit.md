# ArogyaRakshak — Current State Audit

**Audit date:** 2026-09-11
**Commit audited:** `ec93e3a` (`viraj-dev`, 4 commits behind `origin/main`; 0 ahead — all local work is merged)
**Repository:** https://github.com/Viraj281105/Arogyarakshak
**Method:** Direct source inspection, local execution of every test/build/lint/guardrail suite, live probing of the FastAPI application, and cross-checking of all documentation claims against code. Nothing in this report is taken from README or `PROJECT_CONTEXT.md` without independent verification.

**Evidence convention used throughout:**
- **Verified** — I executed it or read the code path end to end.
- **Unverified** — could not be exercised in this environment; explicitly flagged, never assumed working.

---

## 1. Executive Summary

ArogyaRakshak is a real, coherently structured monorepo, not a shell. The architecture is genuinely clean: six lowercase Python domain packages with zero circular dependencies, a versioned FastAPI gateway, a Next.js 16 web client, an Expo mobile client, and a six-job CI pipeline with a custom architectural-invariants scanner. All 63 automated tests across three runtimes pass, both front-end builds are clean, and CI is green on `main`.

The gap is between that structure and what the system actually *does*.

**The headline defect:** `POST /api/v1/billnyay/cases/{id}/appeal` — the flagship "5-agent IRDAI appeal pipeline", the project's central research claim — **returns HTTP 500 on every call**. The endpoint calls `run_barrister_agent()` with keyword arguments that do not match its signature. It has no test, and no web or mobile client ever calls it, which is why the failure has gone unnoticed. It is also not a 5-agent pipeline: two of the five agents are exported but invoked by nothing, and the "judge" is a hardcoded scorer that ignores all its evidence inputs and grades on string length.

**The second-order problem is fidelity, not crashes.** The parts that do run, run on weak data. With `GROQ_API_KEY` unset — which is the *default and only* state today, because `.env.example` omits the key entirely and `docker-compose.yml` never passes it to the API container — every LLM path silently degrades to regex heuristics. Across two independent end-to-end probes the reported bill total was off by **92% and 89%**: an ₹18,500 ICU line was silently dropped (filtered out because `"ICU"` is three characters), `Dolo 650: 33` was parsed with the *dosage* as the price, "Total Amount" was classified as a medical procedure, and the hospital name came out as `'Hospital\nPatient Name'`. Worse, because unmatched line items default their benchmark to the charged amount, an unrecognised medicine was affirmatively reported to the user as **"✓ Fair"**. For a tool built to detect overcharges, defaulting unknown items to "fair" is the wrong direction to fail in. The tests pass because they assert shapes, not values.

**Third: several public claims are not backed by code.** The README advertises FAISS similarity indexes (no FAISS anywhere), IndicXlit/IndicSBERT entity resolution (absent — yet displayed to users as a live pipeline step in the UI), native edge-detection document scanning (a plain camera capture), and a consent boundary (`consent_opt_in` is write-only; every client hardcodes `true` and nothing ever reads it). The de-identification claim is contradicted by the code, which persists 1,000 characters of raw OCR text — patient name and diagnosis included — into the database.

**Fourth: 53 open Dependabot alerts (5 critical, 34 high),** including two unauthenticated-RCE advisories against the pinned `next` version in `apps/web`.

**Honest maturity assessment.** This is a solid **late-Phase-2 engineering skeleton with Phase-1 data depth**, not the "Functional Production Alpha / Phase 1 Complete, Active Blockers: None" that `PROJECT_CONTEXT.md` claims. Two of five modules (BimaNyay, SchemeSetu) are genuinely complete within their rule-based scope. DawaCheck works against 7 hardcoded drugs of a stated 800–900. BillNyay audits but cannot appeal. DaaviSetu generates a PDF that does not contain the data the user submitted.

**Of 102 open issues, 4 were closed** on mechanical evidence. All four are governance/architecture/testing-infrastructure issues whose deliverables are verifiable artifacts. **Zero functional or module issues were closed** — none met their acceptance criteria cleanly enough to justify it.

---

## 2. Component / Module Status

Status vocabulary: **Complete** (implemented, integrated, tested) · **Partial** · **Scaffold** (code exists, not wired) · **Broken** · **Absent**.

### 2.1 Kadi — Shared Intelligence Layer (`packages/kadi`)

| Sub-component | Status | Evidence |
|---|---|---|
| OCR parser (`ocr/ocr_parser.py`) | **Partial** | Real PDF (PyMuPDF), image (EasyOCR) and text paths. 6 unit tests pass. But every failure mode is swallowed into the same placeholder string, and the line-item regex drops any item name ≤ 3 chars. |
| Extraction agent (`extraction.py`) | **Partial** | Real Groq call with a strict JSON schema + `ExtractedEntities` Pydantic model. **Zero unit tests.** The regex fallback — the only path that runs today — produces demonstrably wrong output (§3.3). |
| Vector store (`vector_store.py`) | **Scaffold / dead** | No FAISS (not a dependency anywhere in the repo). `query_similarity_faiss` returns hardcoded `score: 1.0` over a plain list. `setup_pgvector_index` is never called. `KadiVectorStore` is imported by nothing outside its own `__init__.py`. |
| Entity resolution (IndicXlit / IndicSBERT) | **Absent** | Zero matches repo-wide for `indicxlit`, `indicsbert`, `levenshtein`, `jaro`, `fuzzy`, `soundex`, `metaphone`, `rapidfuzz`. Issues #28–#31 correctly open. |
| Persistence (`kadi_cases` / `kadi_entities`) | **Complete** | Async SQLAlchemy, association table, `selectinload` eager loading. Verified end to end. |
| SSE status stream | **Complete (single-process only)** | Works; web and mobile both consume it correctly. See §3.5 for the scaling caveat. |

### 2.2 BillNyay (`packages/billnyay`)

| Sub-component | Status | Evidence |
|---|---|---|
| CGHS benchmark audit | **Partial — runs, but under-reports** | `POST /cases/{id}/audit` works and loads all 27 rates from `cghs_rates.json` (4-candidate path resolution + `billnyay.__file__` lookup). Tested (`test_billnyay_audit`, `test_cghs_rates_loaded_from_json`). But unmatched items default `cghs_benchmark = charged`, so every line absent from the 27-entry table is reported as "✓ Fair" rather than "not benchmarked" (§3.3, defect 7). |
| Auditor agent | **Complete** | Strict JSON + brace-balanced recovery parser. 2 tests. |
| Clinician agent | **Scaffold / dead** | Implemented; called by **no endpoint and no test**. |
| Regulatory agent | **Scaffold / dead** | Called by nothing. Also does not retrieve: builds `query_text` then ignores it and returns the first 4 of 5 statutes unconditionally. |
| Barrister agent | **Broken at call site** | Signature is `(client, denial_details, clinical_evidence, regulatory_evidence, critique, **kwargs)`; `billnyay.py:260` passes `denial_code=`/`procedure_denied=`/strings. `client` is a required positional → `TypeError`. |
| Judge agent | **Placeholder** | Ignores `denial_details`, `clinical_evidence`, `regulatory_evidence` entirely. Scores on `len(appeal_letter)` with four hardcoded sub-scores. Every letter >500 chars gets an identical scorecard. |
| Appeal endpoint | **Broken — HTTP 500** | Reproduced live (§4.4). |
| Grievance / Bima Bharosa draft | **Partial** | Returns 200 with complaint text + portal deep link. No UI consumes it, no test covers it. |
| Appeal PDF compiler | **Scaffold / dead** | `compile_appeal_packet` referenced only by its own `__init__.py`. No route exists. |

### 2.3 BimaNyay (`packages/bimanyay`) — strongest module

**Complete** within its declared rule-based scope. `clause_auditor.py` implements five real IRDAI rules (5-year moratorium, investigation-only, room-rent proportionate deduction, delayed intimation, Claims Review Committee) with genuine statutory citations. `drafter.py` produces 3-tier appeals in English/Hindi/Marathi. `tracker.py` computes 15/15/365-day statutory SLAs. Both endpoints persist to correctly-prefixed tables. 7 package tests + 3 API tests. Fully wired to web and mobile.

Caveat: `reversal_probability_score` values (0.95, 0.90, 0.88, 0.85, 0.70) are **hand-assigned constants**, not a trained or calibrated model. Presenting them as a predictive score in a viva would not survive scrutiny — #90 (predictive outcome model) is correctly still open.

### 2.4 DaaviSetu (`packages/daavisetu`)

**Partial.** The Annexure-B PDF generator is real and well-formatted. But `generate_claim_package()` renders no PDF — it only returns a URL string. The POST and the GET build *different* `ClaimData` objects: the download route synthesises `policy_number=f"POL-{case_id[:6]}"` and defaults `patient_name="Patient"`, discarding what the user actually submitted. `test_daavisetu_pdf_download` passes because it only checks for `%PDF` magic bytes. A patient who submits their real policy number receives a signable insurer form containing a fabricated one.

### 2.5 SchemeSetu (`packages/schemesetu`)

**Complete but shallow.** `check_eligibility` is two income thresholds (₹2.5L PMJAY, ₹1.5L MJPJAY + Maharashtra check). It **ignores `category` and `medical_need` entirely** — both are collected by the UI and transmitted, then discarded. `OfflineEmbedder` is dead code (never instantiated by `check_eligibility` or any endpoint); its fallback uses Python's per-process-salted `hash()`, so the "deterministic" embeddings are not reproducible across runs. No RAG index, no empanelled-hospital data. The README's "RAG eligibility agent" and "empanelled network hospital locator" are not implemented.

### 2.6 DawaCheck (`packages/dawacheck`)

**Partial (~1% of stated data scope).** 7 hardcoded drugs in a Python dict against a stated target of 800–900. The `dawacheck_generic_mappings` table exists with exactly the right shape and is **never read or written**. Matching is bidirectional substring with first-hit `break` and no scoring — tolerable at 7 entries, actively dangerous at 800. Not Kadi-integrated: takes `brand_name`+`mrp` from the client and never reads the `type="medicine"` entities Kadi already extracts. The inline comment claims "Comprehensive NPPA Schedule-I database lookup"; the docstring honestly says "mock database check".

### 2.7 API Gateway (`apps/api`)

**Complete as plumbing.** Clean async SQLAlchemy, correct lifespan, CORS, three global exception handlers, versioned router aggregation, all seven tables correctly module-prefixed. 13 integration tests. Concerns in §3.5 and §6.

### 2.8 Web (`apps/web`)

**Complete for 4 of 5 modules.** Next.js 16 / React 19, all five module views, real `fetch` + SSE wiring, trilingual, clean build and lint, 10 tests. BillNyay view calls only `/audit` — never `/appeal` or `/grievance`. Example/placeholder data is present but **explicitly labelled** ("ⓘ Example — Upload a real document to see live audit results") and correctly suppressed once a case is active — this is honest UI, not fake functionality.

One real bug: `useApi.execute`'s duplicate-submission guard does not work. It returns `prev` from inside the `setState` updater, but the enclosing async function continues regardless — so concurrent submissions are not actually prevented, contrary to the hook's own docstring.

### 2.9 Mobile (`apps/mobile`)

**Complete as source; runtime UNVERIFIED.** 7 screens, typed API client, offline queue with retry/replay, SSE hook with EventSource→fetch fallback, trilingual strings, design system. `tsc --noEmit` clean, 17 tests pass. **I could not run this on a device or emulator** — Expo was not launched. Type-checking and unit tests are *not* evidence that the app renders or that camera capture works. Treat mobile runtime as unverified.

Minor: `useOfflineStorage` rejects values over 50,000 chars, but `expo-secure-store` itself caps entries near 2,048 bytes on device — a moderately sized offline queue will fail to persist silently, below the guard's threshold.

---

## 3. Architecture Findings

### 3.1 Dependency direction is genuinely clean — verified

No file under `packages/` imports `app.*` or `apps.*`. No domain package imports another domain package (the only intra-package imports are `bimanyay.* → bimanyay.models`). Zero cycles. This invariant is real and worth defending.

### 3.2 The documented layering is one level optimistic

Documentation says `UI → FastAPI → Domain Packages → Kadi Shared Layer → DB`. In reality **no domain package imports `kadi`**. Kadi integration happens one layer up, inside `apps/api/app/api/v1/endpoints/*`, which query `KadiEntity` rows directly. The direction is still acyclic and correct — the diagram just shows a dependency edge that does not exist.

### 3.3 The Kadi → domain → client flow works structurally but not numerically

This was the specific focus requested. I probed it live against the running app (`GROQ_API_KEY` unset — the default and only configured state).

**Input:**
```
Lifeline Multispeciality Hospital
Patient Name: Ramesh Kulkarni
Diagnosis: Acute Appendicitis
Consultation: 900
ICU: 18500
Blood Test: 750
Total Amount: 20150
```

**Persisted entities:**
```
billing_item    'Consultation'              900.0
billing_item    'Blood Test'                750.0
hospital        'Hospital\nPatient Name'    <- regex garbage
procedure       'Total Amount'              20150.0   <- summary line misclassified
document_text   'Document Text Excerpt'     <raw text, name + diagnosis verbatim>
case.total_charged = 1650.0                 <- actual bill Rs 20,150
```

**Resulting audit:** `charged=1650, benchmark=600, deviations=2`.

Five distinct defects in one pass:

1. **`ICU: 18500` silently dropped.** `ocr_parser.parse_document` requires `len(item_name) > 3`; `"ICU"` is 3. ICU charges are the single most commonly overcharged hospital line item — precisely the thing this project exists to catch.
2. **92% of the bill unaccounted for**, reported to the user as the total with no warning.
3. **`"Total Amount"` classified as a `procedure`.** The summary-term exclusion list exists in `ocr_parser.py` but was never mirrored into `extraction.py`'s fallback.
4. **Hospital name is regex garbage.**
5. **`patient_name` and `diagnosis` missed** by the fallback, while the raw text containing both is persisted verbatim.

**A second probe, with one extra line (`Dolo 650: 33`, a tablet), reproduced all five and exposed two more:**

```
billing_item    'Blood Test'    750.0
billing_item    'Dolo'          650.0     <- dosage parsed as the price
billing_item    'Consultation'  900.0
hospital        'Hospital\nPatient Name'
procedure       'Total Amount'  20183.0
procedure       'Dolo 650'      33.0      <- same line, different answer
case.total_charged = 2300.0               <- actual bill Rs 20,183

AUDIT: charged=2300, benchmark=1250, deviations=2
  {'item_name':'Blood Test',   'charged':750.0, 'cghs_benchmark':250.0, 'deviation_percentage':200.0,  'is_deviation':True}
  {'item_name':'Dolo',         'charged':650.0, 'cghs_benchmark':650.0, 'deviation_percentage':0.0,    'is_deviation':False}
  {'item_name':'Consultation', 'charged':900.0, 'cghs_benchmark':350.0, 'deviation_percentage':157.14, 'is_deviation':True}
```

6. **Dosage parsed as price.** `Dolo 650: 33` became `item="Dolo", charged=650.0`. The regex `([A-Za-z\s]+)[\s:]+₹?(\d+\.?\d*)` stops the name at the first digit, so the strength (`650mg`) is captured as the amount and the real price (₹33) is discarded. Any medicine written `<name> <strength>: <price>` — i.e. most Indian hospital pharmacy lines — is mis-parsed this way. The medicine was also typed as a `procedure`, not `medicine`, because the fallback's keyword list does not match `"Dolo"`.

7. **Unknown items are silently declared fair — a systematic blind spot.** In `audit_bill`, when no CGHS entry matches: `matched_rate = charged  # default to charged if unknown`. Benchmark then equals the charged amount, deviation is 0%, and `is_deviation` is `False`. That is exactly what happened to `Dolo` above: an unrecognised line was reported to the user as **"✓ Fair"**. With only 27 CGHS entries, most real bill lines will miss — and every miss is presented as a clean result rather than as "not benchmarked". For a tool whose entire purpose is detecting overcharges, defaulting unknown items to "fair" is the wrong direction to fail in.

Note also that the OCR parser and the extraction fallback both processed the same source line and **disagreed** (`billing_item 'Dolo' 650.0` vs `procedure 'Dolo 650' 33.0`), and both rows were persisted. Nothing reconciles them.

**Verdict: the flow is wired end to end and does not crash. It is not numerically trustworthy.** In two independent probes, the reported bill total was off by 92% and 89% respectively, and in the second, an unrecognised line was affirmatively labelled fair. The 36 passing tests assert response shapes and key presence, never values — which is exactly why none of this was caught.

### 3.4 The LLM path is unreachable by default

`.env.example` contains **no `GROQ_API_KEY` line at all**. `docker-compose.yml` passes only `DATABASE_URL` and `GROQ_MODEL` to the `api` service — not the key. So a user following the README's Docker quickstart gets a system where **every LLM call falls back to regex**, silently. `docs/configuration/environment-variables.md` marks `GROQ_API_KEY` as **Required** and then quotes the compose block that omits it, reproducing the gap. Both `extraction.py` and `GroqClient` log a warning and degrade — no user-visible signal.

### 3.5 API concerns

- **No authentication or authorisation anywhere.** Any caller who guesses a `CASE-xxxxxxxx` id reads that patient's extracted entities via `GET /api/v1/kadi/cases/{id}`. 8 hex chars ≈ 4.3×10⁹, with no rate limiting.
- **`processing_status` is a module-level in-memory dict.** It grows unboundedly (never evicted) and is not shared across workers. Under any multi-worker deployment the SSE stream will poll a dict on a different process and hang forever.
- **The SSE generator has no timeout or client-disconnect check.** `while True` + `asyncio.sleep(0.3)`. A request for an unknown `case_id` holds a connection open indefinitely.
- **No upload size, MIME, or page-count limit.** `await file.read()` loads the whole body into RAM.
- **`CORS_ORIGINS` defaults to `*` with `allow_credentials=True`.**
- **Both Dockerfiles are dev-mode in production**: the API runs `uvicorn --reload`, the web runs `npm run dev`. Neither uses a non-root user. CI builds the images but never runs them.

### 3.6 Dead / unwired code inventory

Exported in `__all__`, referenced by no endpoint, test, or client:

| Symbol | Location |
|---|---|
| `KadiVectorStore` (+ `setup_pgvector_index`, `query_similarity_faiss`, `index_entity_faiss`) | `packages/kadi/kadi/vector_store.py` |
| `OfflineEmbedder` | `packages/schemesetu/schemesetu/embeddings.py` |
| `compile_appeal_packet` | `packages/billnyay/billnyay/tools/pdf_compiler.py` |
| `run_clinician_agent` | `packages/billnyay/billnyay/agents/clinician.py` |
| `run_regulatory_agent` | `packages/billnyay/billnyay/agents/regulatory.py` |
| `DawaCheckGenericMapping` ORM table | `apps/api/app/models.py` |
| `ENV.USE_MOCK_DATA` | `apps/mobile/src/config/env.ts` |
| `_wrap_session` / `StructuredDenial._SCHEMA` | partial-use leftovers |

### 3.7 Misleading UI labels

`apps/web/app/translations.ts` renders these as live pipeline stages during upload, in all three languages:

- `stepOcr`: *"Document OCR & Devanagari Transliteration"* — no transliteration exists.
- `stepEntities`: *"Cross-Lingual Entity Resolution (IndicSBERT)"* — **IndicSBERT is not in the repo.** This string is the only occurrence of "IndicSBERT" in the entire codebase.
- `stepAudit`: *"CGHS Rate Benchmark & Regulatory Clause Audit"* — the actual stage is `database_write`. No audit runs during upload.
- `stepComplete`: *"Dossier & Statutory Grievance Package Ready"* — nothing is generated.

A viva examiner watching the demo would see four capabilities asserted on screen that do not exist. This is the most presentation-risky finding in the report.

---

## 4. Testing / Build / CI Status

### 4.1 Everything I ran, and what it returned

| Suite | Command | Result |
|---|---|---|
| Backend (packages + API) | `python -m pytest` | ✅ **36 passed** in 7.70s |
| Web unit | `npm test` (`tsx --test`) | ✅ **10 passed** |
| Web lint | `npm run lint` | ✅ clean |
| Web production build | `npm run build` | ✅ compiled in 982ms, 3 static routes |
| Web type-check | `npx tsc --noEmit` | ✅ exit 0 |
| Mobile type-check | `npm run type-check` | ✅ 0 errors |
| Mobile unit | `npm test` | ✅ **17 passed** in 235ms |
| Architecture guardrails | `python scripts/ci_guardrails.py` | ✅ **5/5 passed** |
| Ruff, CI selection | `--select=E9,F63,F7,F82` | ✅ clean |
| Ruff, default ruleset | `ruff check apps/api packages` | ⚠️ **251 errors** (159 auto-fixable) |
| Docker Compose validation | `docker compose config` | ✅ exit 0 |
| Docker image builds | — | ⚠️ **Unverified locally** (multi-GB torch layer); CI green on `main` |
| Mobile on device/emulator | — | ⚠️ **Unverified** |

**Total: 63 automated tests, 100% pass rate.** GitHub Actions green on `main` and `viraj-dev`.

### 4.2 CI pipeline gaps

The six-job pipeline (`governance-and-invariants` → backend / web / mobile / docker → `ci-gate`) is well-built. Three real gaps:

1. **`apps/web` tests never run in CI.** `web-ci` executes `npm ci`, `npm run lint`, `npm run build` — **not `npm test`**. The 10 web tests are dead weight in the pipeline.
2. **Ruff is lint theatre.** `--select=E9,F63,F7,F82` catches only syntax errors and undefined names. The default ruleset reports 251 findings CI never sees.
3. **Coverage is measured but never gated.** `--cov` produces `coverage.xml` and uploads it; no threshold, no failure condition.

Also: `scripts/ci_guardrails.py::check_model_grounding` skips `config.py` — which is exactly the file where a model name lives (`apps/api/app/config.py` defines `groq_model`). A deprecated model set there would pass the guard.

### 4.3 What the tests do not cover

No tests exist for: `/billnyay/.../appeal`, `/billnyay/.../grievance`, `run_barrister_agent`, `run_clinician_agent`, `run_regulatory_agent`, `compile_appeal_packet`, `kadi/extraction.py` (the entire extraction agent), `KadiVectorStore`, `OfflineEmbedder`, CORS behaviour, or any error/failure path.

Assertion quality is the deeper issue. `test_real_image_ocr_upload_and_persistence` is documented as proving "real image EasyOCR pipeline executes"; it asserts only `len(entities) > 0`. Because `parse_document` catches every exception and substitutes a placeholder string — which still yields a `document_text` entity — **this test passes even if EasyOCR is absent or fails entirely.** Similarly `test_billnyay_audit` asserts only key presence, and `test_daavisetu_pdf_download` checks only `%PDF` bytes. This is why §3.3's defects went undetected.

### 4.4 The HTTP 500, reproduced

```
POST /api/v1/billnyay/cases/CASE-602647c3/appeal  ->  500
{"detail":"An unexpected server error occurred.",
 "message":"run_barrister_agent() missing 1 required positional argument: 'client'"}
```
Traceback terminates at `apps/api/app/api/v1/endpoints/billnyay.py:260`. Note that the response body also leaks the internal exception text to the client (§6.3).

---

## 5. Documentation Discrepancies

`docs/` is unusually thorough for a student project: 5 ADRs, 6 guides, 4 architecture docs, and **73 relative Markdown links with 0 broken** (verified). The problem is accuracy, not completeness.

### 5.1 `docs/api/overview.md` — 5 of 10 documented module routes are wrong

Compared against `app.routes` enumerated from the live application:

| Documented | Reality |
|---|---|
| `POST /api/v1/billnyay/audit` | actual: `/api/v1/billnyay/cases/{case_id}/audit` |
| `POST /api/v1/billnyay/generate-appeal` | does not exist (actual `/cases/{id}/appeal`, returns 500) |
| `POST /api/v1/daavisetu/pre-auth/generate` | actual: `/api/v1/daavisetu/cases/{case_id}/claim` |
| `POST /api/v1/bimanyay/generate-appeal-pdf` | **does not exist at all** |
| `POST /api/v1/bimanyay/grievances` | **does not exist** (actual `/api/v1/bimanyay/timeline`) |
| `GET /api/v1/bimanyay/grievances/{id}` | **does not exist** |

Live but undocumented: `POST /billnyay/cases/{id}/grievance`, `GET /daavisetu/cases/{id}/claim/pdf`.

### 5.2 SSE protocol documented wrong in two places

`docs/api/overview.md` §3 and `docs/architecture/data-flow.md` §3 both specify `{case_id, stage, progress, message, timestamp}` with stages `document_received/ocr_parsing/entity_extraction/domain_auditing/completed`. The actual emitter sends `{status, progress, log}` with `upload_received/ocr_start/extraction_start/database_write/completed/failed`. **Both clients consume the actual schema** — code is self-consistent; only the docs are wrong. `data-flow.md` also shows the BillNyay 5-agent chain firing during upload; it does not — domain analysis is a separate client-initiated POST.

### 5.3 `docs/development/testing.md`

- Mobile tests located at `apps/mobile/src/__tests__/` — actual: `apps/mobile/tests/`.
- "32 Tests" / "10 mobile tests" — actual: 36 / 17.
- Fixture described as `sqlite+aiosqlite:///:memory:` — `conftest.py` uses **file-based** `sqlite+aiosqlite:///test_temp.db`, with a code comment explicitly saying so.
- None of the six evaluation metrics (PEA, BMA, CFMA, CRMA, WER/CER, latency) has any harness — consistent with #102–#116 being open.

### 5.4 `README.md`

| Claim | Reality |
|---|---|
| "in-memory FAISS similarity indexes" | FAISS is not a dependency anywhere; `vector_store.py` returns hardcoded `1.0` over a list |
| "IndicXlit and IndicSBERT" in tech stack + architecture diagram | Zero code matches |
| "native edge-detection document scanner" | `CameraScanScreen.tsx` is plain `expo-camera` `takePictureAsync` — no edge/crop/perspective logic |
| "nearby empanelled network hospital locator" | Absent |
| "nearest Jan Aushadhi store map" | A static text string in a dict |
| "SchemeSetu RAG eligibility agent" | Two income `if` statements |
| "Run all package unit tests (12 tests)" / "(4 tests)" | 23 / 13 |
| "Next.js 15" (also in `docker-compose.yml` comment) | 16.2.10 installed |
| "de-identified ... only procedure codes, medicines, prices" | Raw text with patient name + diagnosis persisted (§6.1) |
| "cross-module sharing requires explicit per-case opt-in" | Never enforced; all clients hardcode `true` |

### 5.5 `docs/configuration/environment-variables.md`

Documents an `ENVIRONMENT` variable ("Controls error traceback verbosity") that **does not exist** — `Settings` defines only `groq_model`, `groq_api_key`, `database_url`, `cors_origins`. Traceback verbosity is not controlled by anything; the global handler always returns `str(exc)`.

### 5.6 `PROJECT_CONTEXT.md`

Quantitative claims are **accurate** — §15's 36/17/10 test counts, clean builds and 5/5 guardrails all re-verified correct. Credit where due. But §7 "Implemented Features" over-states three rows:

- *"BillNyay 5-Agent Pipeline — Complete"* → 3 of 5 wired, and the barrister link returns HTTP 500.
- *"Kadi Vector Store — Complete · Tests: Yes (test_ocr.py)"* → stub with no FAISS; `test_ocr.py` does not reference it.
- *"SchemeSetu ONNX Fallback — Complete · Tests: Yes (test_schemesetu.py)"* → no ONNX code exists; `test_schemesetu.py` does not import it.

Also stale: §2 "Active Blockers: None" (contradicted by the 500); §9 P0 shows `[ ] Scaffold Mobile App` unchecked though `apps/mobile` exists and #134 is closed; §12 refers to "all 29 tests".

---

## 6. Security & Privacy Concerns

### 6.1 The de-identification claim is false

README §Privacy and `data-flow.md` §2 both state persisted `kadi_entities` rows hold "only de-identified clinical metadata". Verified otherwise: `process_document_background` persists a `document_text` entity containing **the first 1,000 characters of raw OCR text verbatim**, and deliberately creates a `type="patient"` entity from `extracted.patient_name`. My probe stored `Patient Name: Ramesh Kulkarni` and `Diagnosis: Acute Appendicitis` in plaintext.

The narrower BYOD claim **does hold**: raw binary files are never written to disk, and `check_byod_zero_retention` enforces the absence of upload directories.

### 6.2 Consent is decorative

`consent_opt_in` is write-only across the whole repo. No UI to set it; all five client call sites hardcode `true`.

### 6.3 Internal exception text leaked to clients

`apps/api/app/main.py`'s handler docstring says "to avoid leaking internal trace details", then returns `"message": str(exc)`. Confirmed live — the 500 body contained the literal Python error including the internal function name and parameter.

### 6.4 No authentication, no rate limiting, no upload limits

See §3.5. Patient case data is retrievable by id alone.

### 6.5 53 open Dependabot alerts — 5 critical, 34 high, 11 medium, 3 low

| Severity | Package | Advisory |
|---|---|---|
| critical | `next` (web) | Unauthenticated RCE in Image Optimization API (AVIF) |
| critical | `next` (web) | Unauthenticated RCE on Windows-hosted servers |
| critical | `tar` (mobile) | Decompression/parse DoS |
| high ×13 | `@xmldom/xmldom` (mobile) | XML injection, ReDoS, quadratic memory |
| high | `postcss` (mobile) | Arbitrary file read via `sourceMappingURL` |
| high | `js-yaml`, `nanoid`, `browserslist`, `image-size` | DoS / prototype-write |

Note `apps/web/package.json` declares `next: 16.3.0` while the lockfile resolves **16.2.10** — the vulnerable version, and the one the build actually used.

### 6.6 Clean

`.env` is gitignored, untracked, and contains no real key. Guardrail check [5/5] found no `gsk_` leaks. No hardcoded credentials in source.

---

## 7. GitHub Issues Reviewed

**102 open, 25 closed** at audit start. All 102 open issues reviewed; the ~21 plausible completion candidates were individually fetched and verified against code.

| Classification | Count | Notes |
|---|---|---|
| **Completed** (closed by this audit) | **4** | #124, #131, #132, #133 — §8 |
| **Partially completed** | ~12 | #13, #19, #22, #24, #25, #26, #38, #49, #50, #51, #52, #130 |
| **Broken (regressed / never worked)** | 1 | **#18** — the 5-agent pipeline |
| **Not started** | ~85 | All of Phase 3/4/4.5/5 + all ABDM/scraper/advanced-ML issues |
| **Obsolete or duplicate** | 2 | **#48 and #78** are near-duplicates (both "DaaviSetu: ingest blank pre-auth form templates"); #78 scopes it to 5 insurers. Recommend closing #48 as a duplicate of #78 — flagged, **not actioned**, since deduplication is a scoping decision for the project owner. |
| **Blocked** | 3 | #46, #54, #56 — all gated on external ABDM Sandbox registration, outside the codebase |

Not-started verified by keyword sweep across `apps/`, `packages/`, `scripts/` — **0 files** match: `abdm`, `fhir`, `levenshtein`, `jaro`, `fuzzy`, `soundex`, `metaphone`, `rapidfuzz`, `scraper`, `scrape`, `crawler`, `graphdb`, `rlhf`, `biobert`, `zero-knowledge`, `differential privacy`.

---

## 8. Issues Closed and Evidence

Four closed. Every one is an issue whose deliverable is a **verifiable artifact set**, checkable mechanically, with nothing about system behaviour that could be silently wrong. Each received a detailed evidence comment before closing.

### #124 — [Architecture] Repository Restructuring, Naming Hardening & Migration Record

1. Six lowercase packages, each with `pyproject.toml` — `ci_guardrails.py` check [3/5] passing.
2. All seven `__tablename__` values correctly module-prefixed — check [4/5] passing.
3. Unidirectional dependency flow verified by source scan: no `packages/` file imports `app.*`/`apps.*`; no cross-package imports; zero cycles.
4. `docs/architecture/repository-structure.md` present (121 lines), tracked; 73/73 links resolve.
5. Zero ambiguous directories (`misc/`, `helpers/`, `stuff/`, `temp/`).
6. Zero regression: 36 backend + 10 web + 17 mobile tests, clean builds, guardrails 5/5.

Recorded in the comment: the `Domain Packages → Kadi` documented edge does not exist in code (§3.2).

### #131 — [Governance] Living Engineering Memory System & AI Agent Manuals

All six deliverables present and tracked: `PROJECT_CONTEXT.md` (529), `AGENTS.md` (187), `apps/api/AGENTS.md` (37), `apps/web/AGENTS.md` (26), `packages/kadi/AGENTS.md` (35), `.github/AGENTS.md` (15). The Implementation → Documentation Gate is codified at both claimed locations (`AGENTS.md:32`, `PROJECT_CONTEXT.md:517`). §15's quantitative claims independently re-verified correct.

Closed because the deliverable — the memory *system* — exists and works; keeping it accurate is the issue's own stated follow-up. The three over-stated §7 rows were documented in the closing comment for the next sync.

### #132 — [Governance] Community Health, Security Policies & Contributor Templates

All 11 files verified present and git-tracked: `CONTRIBUTING.md` (198), `CODE_OF_CONDUCT.md` (73), `SECURITY.md` (49), `CHANGELOG.md` (49), `LICENSE` (MIT header confirmed), `.gitattributes`, `.github/CODEOWNERS`, `PULL_REQUEST_TEMPLATE.md`, and three `ISSUE_TEMPLATE/` files. Templates are demonstrably in use — the open issues render from them. Pure artifact existence; nothing can be behaviourally wrong.

The 53 Dependabot alerts were flagged in the comment as a separate concern, not a blocker on this issue.

### #133 — [Testing] Automated Verification Suite Expansion

Claimed 23 tests; **36 actually pass**, all seven named files present. Exceeds its acceptance criteria.

| Suite | Claimed | Actual |
|---|---|---|
| billnyay / bimanyay / daavisetu / dawacheck / kadi / schemesetu | 4/5/1/3/2/2 | 4/7/1/3/6/2 |
| `apps/api/tests/test_api.py` | 6 | 13 |
| **Total** | **23** | **36** |

Closed on scope (test *infrastructure* expansion), with its own follow-up — "add API integration tests for `daavisetu` and `billnyay` endpoints" — carried forward explicitly in the comment, noting that the untested `billnyay` half is the endpoint that returns HTTP 500.

---

## 9. Issues Remaining Open (98)

### 9.1 Evidence comments posted (not closed)

| # | Title | Finding |
|---|---|---|
| **#18** | Re-verify 5-agent pipeline | **BROKEN** — HTTP 500 reproduced; 3 of 5 agents wired; judge is a length heuristic; regulatory agent does not retrieve; PDF compiler orphaned; no test; no client calls it |
| #19 | Integrate BillNyay with Kadi | Partial — audit path works and is tested; appeal path 500s; extraction fidelity failures documented |
| #20 | Appeal PDF generation + download | Not started — `compile_appeal_packet` orphaned, no route exists; blocked on #18 |
| #33 | Consent UI | Not started — `consent_opt_in` write-only, all 5 client sites hardcode `true` |
| #50 | DaaviSetu submission-ready package | Partial — PDF downloads but contains a fabricated policy number and `"Patient"` |
| #130 | Documentation Portal & ADRs | Structure complete (73/73 links); **kept open** — `api/overview.md` documents 5 nonexistent routes |
| #16 | NPPA Schedule-I ingestion | ~1% — 7 hardcoded drugs vs. 800–900; `dawacheck_generic_mappings` table dead |

### 9.2 Correctly open — not started (~85)

- **Data ingestion / external:** #14, #15, #46, #54, #56, #59, #61 (ABDM/FHIR and all scrapers absent)
- **Entity resolution (Phase 3):** #28–#32, #34, #85–#89 — no string similarity, transliteration, embeddings, graph, or auto-triggering
- **Multilingual & QA (Phase 4):** #35–#37, #39, #93–#97
- **Evaluation (Phase 4.5):** #102–#116 — **all 15 open; no harness exists for any metric**
- **Advanced module features:** #62–#84, #90–#92, #98–#101
- **Phase 5:** #40–#43

### 9.3 Duplicate flagged, not actioned

**#48 ≈ #78** — both "DaaviSetu: ingest blank pre-auth form templates". Recommend closing #48 in favour of the better-scoped #78. Left to the project owner.

---

## 10. Partial / Incomplete Work

Ranked by the size of the gap between claimed and actual state.

| Item | Claimed | Actual | Gap |
|---|---|---|---|
| BillNyay 5-agent pipeline | Complete | 3 of 5 wired; barrister call broken; judge is a heuristic | **Severe** |
| DawaCheck NPPA data | 800–900 drugs | 7 hardcoded | **Severe** |
| Kadi entity resolution | "IndicXlit + IndicSBERT" | Absent; label shown in UI anyway | **Severe** |
| Kadi vector store | "FAISS + pgvector" | No FAISS; pgvector never enabled; class unused | **Severe** |
| Consent boundary | Enforced per-case opt-in | Write-only field, no UI | **Severe** |
| BillNyay audit truthfulness | Overcharge detection | Unmatched lines default to "✓ Fair"; no "not benchmarked" state | **High** |
| Kadi extraction fidelity | Working | ICU lines dropped; dosage parsed as price; summary lines misclassified; OCR and fallback disagree and both persist | **High** |
| DaaviSetu PDF | Submission-ready | Contains fabricated policy number | **High** |
| CGHS ingestion (#13) | "scraping/parsing" | 27 curated JSON entries, no scraper; source PDF sits unparsed in `data/raw/` | **Moderate** |
| SchemeSetu eligibility | "RAG agent", 4 inputs | Two `if`s; `category` + `medical_need` discarded | **Moderate** |
| Mobile edge-detection scan | "native edge detection" | Plain camera capture | **Moderate** |
| Evaluation metrics | 6 targets published | Zero harnesses | **Moderate** |
| Web `useApi` dedupe guard | "prevents duplicate submissions" | Guard has no effect | **Low** |

---

## 11. Critical Problems and Recommended Next Priorities

### P0 — Fix before any demo or viva

1. **Repair `POST /billnyay/.../appeal`.** Pass `client`, a real `StructuredDenial`, an `EvidenceList` from `run_clinician_agent`, and the dict from `run_regulatory_agent`. Add a test asserting HTTP 200 and a non-empty letter. *This is the project's headline feature and it currently 500s.* (#18)
2. **Fix or remove the four false UI pipeline labels** (§3.7). "Cross-Lingual Entity Resolution (IndicSBERT)" on screen with no IndicSBERT in the repo is the highest presentation risk in this audit. Relabel to what actually runs.
3. **Stop reporting unbenchmarked items as "Fair".** In `audit_bill`, replace `matched_rate = charged` for unmatched items with an explicit third state (`cghs_benchmark: null`, `status: "not_benchmarked"`) and render it distinctly in both clients. Today an unrecognised line shows the user a green "✓ Fair" badge on a charge nobody checked — the most damaging single behaviour in the system, because it actively reassures a patient who is being overcharged. (#19)
4. **Stop silently dropping and mis-parsing bill lines.** Lower the `len(item_name) > 3` filter (it eats `ICU`), make the line-item regex distinguish a dosage from a price (`Dolo 650: 33` currently yields ₹650), port the summary-term exclusion list into `extraction.py`'s fallback, and reconcile the OCR parser against the extraction fallback so one source line cannot produce two contradictory persisted rows. Surface an `unmatched_lines` count in `AuditResponse`. A bill audit that loses ~90% of the bill without warning is worse than no audit. (#19)
5. **Make the Groq path reachable.** Add `GROQ_API_KEY` to `.env.example` and pass it through the `api` service in `docker-compose.yml`. Log loudly — ideally surface in the API response — when the heuristic fallback is active.

### P1 — Correctness and honesty

6. **Fix the DaaviSetu PDF data mismatch** (#50) — patients are being handed a signable insurer form with a fabricated policy number.
7. **Reconcile README and `docs/` with reality** (§5). Remove or mark-as-planned: FAISS, IndicXlit/IndicSBERT, edge-detection scanning, hospital locator, Jan Aushadhi map. Regenerate `api/overview.md` from `/openapi.json`. Correct the SSE schema in two files and the stale counts in `testing.md`.
8. **Correct the privacy claims, or the code.** Either stop persisting the raw `document_text` excerpt and the `patient` entity, or amend README/ADR-003 to describe what is actually retained (§6.1).
9. **Enforce `consent_opt_in` or drop it** (#33). A privacy control that nothing reads is worse than none — it is a claim you cannot defend under questioning.

### P2 — Security

10. **Drain the 53 Dependabot alerts**, starting with the two `next` RCEs. Align `package.json` (16.3.0) with the lockfile (16.2.10).
11. **Stop returning `str(exc)`** from the global handler (§6.3).
12. **Add upload size/MIME limits, an SSE timeout, and `processing_status` eviction** (§3.5). Move to Redis or the DB before any multi-worker deployment.
13. **Restrict `CORS_ORIGINS`** and reconsider `allow_credentials=True` with `*`.
14. **Production Dockerfiles** — drop `--reload` and `npm run dev`, add non-root users, build Next.js for production.

### P3 — Test and CI credibility

15. **Run `npm test` in the `web-ci` job.** Ten tests currently never execute in CI.
16. **Assert values, not shapes.** Rewrite `test_real_image_ocr_upload_and_persistence` to assert extracted *text content* — today it passes even if EasyOCR is entirely absent.
17. **Expand Ruff beyond `E9,F63,F7,F82`** and gate coverage at a threshold.
18. **Close the `config.py` guardrail loophole** (§4.2).
19. **Delete or wire the dead code** in §3.6 — it is the main source of the gap between claimed and real capability.

### P4 — Academic completeness

20. **Start the evaluation harness (#102–#116).** All 15 metric issues are open and nothing exists. For an FYP, measured PEA/BMA/WER numbers are likely to matter more to examiners than additional features.
21. **Reclassify the BimaNyay reversal probabilities** as heuristic priors, not predictions, until #90 lands.

---

---

## 12. Post-P0 Verification (2026-09-11, commit `e7d491b` + working tree)

Independent re-verification after the five P0 fixes. Every claim below was re-executed,
not carried over from the fix session. Baseline for all "before" figures is `ec93e3a`.

### 12.1 P0 resolution status

| # | P0 finding | Status | Evidence |
|---|---|---|---|
| 1 | `/billnyay/.../appeal` returns HTTP 500 | **Resolved** | Probes A and B both return **HTTP 200**, 1,563-char prose letter, judge verdict `approve`. `/grievance` 200. |
| 2 | Bill parsing drops / mis-parses lines | **Resolved** | Probe A total **1,650 → 20,150**; Probe B **1,650 → 20,183**. ICU captured; `Dolo 650: 33` = ₹33 not ₹650; `Total Amount` excluded; hospital / patient / diagnosis all correct. |
| 3 | Unmatched items reported as "✓ Fair" | **Resolved** | `Dolo 650` → `status: not_benchmarked`, `cghs_benchmark: null`, `is_deviation: false`. Savings computed over the benchmarked subset only. |
| 4 | UI stages claim absent capabilities | **Resolved** | All four labels replaced in en/hi/mr. A test fails the build if `IndicSBERT`, `IndicXlit`, `Transliteration`/`लिप्यंतरण` or `FAISS` returns to a stage label. |
| 5 | Groq unreachable / silent degradation | **Resolved** | `GROQ_API_KEY` added to `.env.example` and forwarded in `docker-compose.yml`; startup `WARNING` on degraded mode; `/health` reports `groq_configured`; appeal response carries `llm_backed`. |

### 12.2 Reproduced probe output (live app, `GROQ_API_KEY` unset)

```
######## PROBE A  (true bill total = 20150)
  case.total_charged   = 20150.0          <- was 1650.0
  hospital             = 'Lifeline Multispeciality Hospital'   <- was 'Hospital\nPatient Name'
  patient              = 'Ramesh Kulkarni'                     <- was missing
  diagnosis            = 'Acute Appendicitis'                  <- was missing
  billing items        = ['Blood Test', 'Consultation', 'ICU'] <- ICU was dropped
  AUDIT charged=20150.0 benchmarked_charged=20150.0 bench=6000.0 savings=14150.0 unmatched=0
     Blood Test    charged=750.0    bench=250.0   status=overcharged
     ICU           charged=18500.0  bench=5400.0  status=overcharged
     Consultation  charged=900.0    bench=350.0   status=overcharged
  APPEAL    HTTP 200  llm_backed=False len=1563 judge=approve   <- was HTTP 500
  GRIEVANCE HTTP 200

######## PROBE B  (true bill total = 20183)
  case.total_charged   = 20183.0          <- was 1650.0
  billing items        = ['Blood Test', 'Consultation', 'Dolo 650', 'ICU']
  AUDIT charged=20183.0 benchmarked_charged=20150.0 bench=6000.0 savings=14150.0 unmatched=1(Rs33.0)
     Dolo 650      charged=33.0     bench=None    status=not_benchmarked  <- was charged=650.0, "Fair"
  APPEAL    HTTP 200  llm_backed=False len=1563 judge=approve

/health: {'status':'ok','version':'1.0.0','groq_configured':False,'groq_model':'openai/gpt-oss-120b'}
```

### 12.3 Suite results

| Suite | Before (`ec93e3a`) | After | Command |
|---|---|---|---|
| Backend pytest | 36 passed | **85 passed** | `python -m pytest` |
| Web unit | 10 passed | **14 passed** | `npm test` |
| Mobile unit | 17 passed | **20 passed** | `npm test` |
| **Total** | **63** | **119** | |
| Web `tsc --noEmit` | 0 errors | 0 errors | |
| Web lint / production build | clean | clean | |
| Mobile `tsc --noEmit` | 0 errors | 0 errors | |
| Ruff (CI selection) | clean | clean | `--select=E9,F63,F7,F82` |
| CI guardrails | 5/5 | **5/5** | `scripts/ci_guardrails.py` |
| `docker compose config` | exit 0 | exit 0 | |

### 12.4 Diff review findings

**Weakened tests: none.** `git diff ec93e3a` across all test files shows **zero removed assertion lines**. One existing test was modified — `test_health_endpoint` — because `/health` intentionally gained fields; it still asserts `status` and `version` and now additionally asserts the type of `groq_configured` and the presence of `groq_model`. It is strictly stronger.

The existing OCR suite (`test_ocr.py`, 6 tests) passes **unchanged** against the rewritten parser, including `test_parse_document_noise_filtering`, which asserts that `AB:` and `Dr:` are filtered out. The ICU fix was implemented as a clinical-abbreviation allowlist rather than by lowering the length threshold, precisely so that test kept its original meaning.

**Accidental behaviour changes: one, intended and contained.** `AuditResponse.total_benchmark` changed meaning — it now sums benchmarked items only, where previously it included unmatched items benchmarked against themselves. That is the point of the fix, but it makes `total_charged` and `total_benchmark` cover different item sets whenever anything is unmatched. `benchmarked_charged`, `potential_savings` and `unmatched_amount` were added so that no caller has to infer savings by subtracting mismatched totals. Two invariants are now test-enforced: `total_charged − benchmarked_charged == unmatched_amount`, and `benchmarked_count + unmatched_count == len(audit_items)`.

**Dead code introduced: one item, removed during this review.** `_rate_of(entry, default_bundled=False)` carried a parameter no caller ever passed; the signature is now `_rate_of(entry)`. Two remaining Ruff findings in touched files — the unused `JudgeScorecard` import and `ARG002` on `GroqClientFallback.generate(prompt, ...)` — were both confirmed present at `ec93e3a` and left alone as out of scope (`prompt` is interface conformance with `GroqClient`, not dead code).

**Web/mobile API contract: consistent.** A field-by-field comparison of the Pydantic models against both TypeScript interfaces shows an exact match for `AuditResponse`, `AuditResultItem` and `AppealResponse` — no client-only fields, no unconsumed fields — and both clients gate on `benchmarked && cghs_benchmark !== null` before rendering a benchmark.

**One residual presentation gap (not a contract break).** The mobile summary row still shows `total_charged` beside `total_benchmark`, which now cover different item sets; the web view was updated to render `potential_savings` instead. Mobile does render the `unmatchedNotice` disclosure, and that notice fires in exactly the cases where the two figures diverge (test-enforced), so the gap is disclosed rather than hidden. It was left unchanged deliberately: mobile runtime remains unverified (no emulator run), and adding a stat tile plus a fourth translated string to a UI that cannot be visually checked is a worse risk than the disclosed mismatch. Recommended as a small follow-up.

**Offline honesty caveat.** With `GROQ_API_KEY` unset the Barrister returns a fixed statutory template, so Clinician and Regulatory evidence does not appear in the *letter text* in offline mode. The chain itself is genuinely wired: a capturing-client test confirms that the denial code, procedure, policy clause, clinical article title, PubMed id, statute name and statute summary all reach the Barrister prompt. `llm_backed: false` discloses the template case to callers.

### 12.5 Documentation made stale by these fixes

Identified, **not edited** — documentation reconciliation is P1 item 7 and has not been authorised:

| File | Stale content |
|---|---|
| `CONTRIBUTING.md:163` | `# Expected: {"status":"ok","version":"1.0.0"}` — `/health` now returns four fields |
| `docs/development/setup.md:142` | the same `/health` expected-output line |
| `docs/configuration/environment-variables.md` | the "For Docker Compose" block quotes the compose `environment:` map without `GROQ_API_KEY`; it now contradicts `docker-compose.yml` |
| `PROJECT_CONTEXT.md` §2, §8, §15 | "36 backend / 17 mobile / 10 web tests" → now 85 / 20 / 14 |
| `docs/development/testing.md` §2.1, §2.2 | "32 Tests" / "10 Tests" → now 85 / 20 (already stale before these fixes) |
| `docs/api/overview.md` | still omits `benchmarked`, `status`, `potential_savings`, `unmatched_count`, `llm_backed` and the `/health` LLM fields, on top of the route errors recorded in §5.1 |

Sections 1–11 of this report describe the pre-fix state at `ec93e3a` and are retained as the audit baseline; this section supersedes them for the five P0 items only. All P1/P2/P3 findings remain open and unaddressed.

---

## 13. P1 #6 — DaaviSetu Data Mismatch: Fix & Verification (2026-09-11)

Resolves the §2.4 / §9.1 finding: the pre-authorization PDF did not contain the data the
patient submitted. This is the highest-severity remaining item because the output is a
document the patient signs and files with an insurer.

### 13.1 Root cause (traced, not assumed)

`ClaimData` entered the system at `POST /api/v1/daavisetu/cases/{case_id}/claim`
(`daavisetu.py:71`), was wrapped into a `ClaimPackage`, returned to the caller — and
**never persisted**. `generate_claim_package()` renders no PDF; it only returns a URL
string pointing at the download route.

`GET .../claim/pdf` therefore had nothing to read and rebuilt a *different* `ClaimData`
from Kadi entities, inventing the two fields Kadi cannot supply:

```python
policy_number=f"POL-{case_id.replace('CASE-', '')[:6]}",   # fabricated
patient_name = "Patient"                                    # placeholder default
```

`test_daavisetu_pdf_download` passed throughout because it asserted only the `%PDF`
magic bytes and never inspected the rendered content.

### 13.2 Approach

No DaaviSetu data layer existed. Rather than invent storage, the fix follows the pattern
already established by BimaNyay — a module-owned SQLAlchemy table in
`apps/api/app/models.py` written from its own endpoint — using the `daavisetu_` table
prefix that `scripts/ci_guardrails.py` already reserves.

Storing the claim in `KadiEntity.meta` was considered and rejected: ADR-002 defines Kadi
as pure shared infrastructure holding no module-specific rules, and the §3 non-overlap
matrix depends on that boundary.

| Change | File |
|---|---|
| New `DaaviSetuClaim` model → table `daavisetu_claims` (unique `case_id`, FK to `kadi_cases`, `ondelete=CASCADE`) | `apps/api/app/models.py` |
| POST persists the submitted form (upsert keyed on `case_id`) | `apps/api/app/api/v1/endpoints/daavisetu.py` |
| GET renders strictly from the persisted claim; returns **409** when nothing was submitted, instead of fabricating a form | same |
| PDF renderer `generate_preauth_pdf()` | **unchanged — layout preserved** |

Returning 409 rather than falling back to Kadi-derived guesses is deliberate: a
fabricated policy number on a signable insurer form is worse than no form. The web client
only exposes the download link inside its post-submission `{result && …}` branch, and no
mobile route calls the PDF endpoint, so no caller reaches the 409 in normal use.

### 13.3 Before / after (live probe)

```
GET before POST -> HTTP 409          (was: HTTP 200 with a fabricated form)
POST claim_id = CLAIM-a547ae3b       submitted policy=POL-STAR-774411 patient=Sunita Deshmukh

PDF (2929 bytes) rendered values:
   patient on form = 'Sunita Deshmukh'    <- was 'Patient'
   policy  on form = 'POL-STAR-774411'    <- was 'POL-a547ae'
   claim ref present = True
   hospital/diagnosis/treatment present = True
   fabricated policy absent = True
```

| Field | Before | After |
|---|---|---|
| `policy_number` | `POL-{case_id[:6]}` (invented) | submitted value, verbatim |
| `patient_name` | `"Patient"` unless a Kadi `patient` entity existed | submitted value, verbatim |
| `hospital_name` / `diagnosis` / `treatment_plan` | re-derived from Kadi at download time | submitted values, verbatim |
| `estimated_cost` | recomputed from `case.total_charged` at download time | value captured at submission |
| Claim reference on form | recomputed `CLAIM-{case_id[:8]}` | persisted `claim_id`, matches POST response |
| No claim submitted | 200 + fabricated form | 409 with remediation message |

### 13.4 Regression tests added (7)

All assert **PDF content** via PyMuPDF text extraction, not magic bytes:

| Test | Guards |
|---|---|
| `test_daavisetu_submitted_values_reach_the_pdf` | all five submitted fields + the POST's `claim_id` appear in the rendered PDF |
| `test_daavisetu_pdf_contains_no_fabricated_values` | `POL-{case_id[:6]}` absent; asserts the value cell `"1. PATIENT FULL NAME Sunita Deshmukh"` and that `"… Patient"` is not rendered |
| `test_daavisetu_estimated_cost_persisted_from_submission` | cost captured at submission (`INR 19,400.00`) is what the form shows |
| `test_daavisetu_claim_is_persisted_not_just_echoed` | queries `daavisetu_claims` directly — proves storage, not echo |
| `test_daavisetu_pdf_requires_a_submitted_claim` | 409 instead of an invented form |
| `test_daavisetu_pdf_unknown_case_returns_404` | 404 preserved for unknown cases |
| `test_daavisetu_resubmission_updates_the_same_claim` | upsert — one row per case, stale policy number no longer rendered |

### 13.5 Verification

| Suite | Before P1 #6 | After |
|---|---|---|
| Backend pytest | 85 passed | **92 passed** |
| Web unit | 14 passed | 14 passed |
| Mobile unit | 20 passed | 20 passed |
| **Total** | **119** | **126** |

Web `tsc` / lint / production build clean; mobile `tsc --noEmit` 0 errors; Ruff (CI
selection) clean; CI guardrails **5/5**, including the table-prefix check now covering
`daavisetu_claims`.

### 13.6 Diff review

**Weakened tests: none.** Zero removed assertion lines across all test files. Both
pre-existing DaaviSetu tests (`test_daavisetu_claim`, `test_daavisetu_pdf_download`) are
unmodified and still pass.

**Dead code: none.** Ruff `F401/F841/ARG` over the changed files is clean. `KadiEntity`
remains imported and used — the POST still falls back to Kadi entities for
hospital/diagnosis/treatment when the caller omits them; only the *download* path stopped
re-deriving.

**Client contracts: unchanged and consistent.** `ClaimPackage` and `ClaimData` field sets
match both TypeScript interfaces exactly, with no client-only fields. Both clients ignore
`form_filled_pdf_url` (a duplicate of `form_filled_pdf_path`) — pre-existing and untouched.

**Intentional behaviour changes (2):**
1. `GET .../claim/pdf` returns 409 when no claim exists (previously 200 + fabricated form).
2. `estimated_cost` on the PDF is now the value captured at submission rather than
   `case.total_charged` re-read at download time. The figure the patient reviewed and is
   signing must be the figure on the form; uploading further documents after submission no
   longer silently changes the amount on an already-reviewed claim.

**Newly stale documentation** (identified, not edited — still P1 item 7):
`docs/api/overview.md` does not document the 409 response, and continues to list the route
under its non-existent `/daavisetu/pre-auth/generate` name (§5.1).

---

## 14. P1/P2 Batch — Documentation, Privacy, Consent & Security (2026-09-11)

Addresses §11 P1 items 6–9 and P2 items 10–13. Each fix was traced to root cause, made at the
smallest architecturally appropriate point, and covered by behavioural regression tests.

### 14.1 Privacy / data retention

**Root cause.** Two distinct leaks, only one of which the original audit found.

1. `process_document_background` persisted a `type="patient"` entity holding the patient's
   name, and stored the first 1000 characters of raw OCR text verbatim as `document_text`.
2. *(newly found while fixing 1)* The line-item parser treated identity fields as charges:
   `Contact: 9876543210` became a **₹9,876,543,210 billing item**, and
   `Aadhaar: 1234 5678 9012` put government-ID digits into an entity name. This corrupted
   audit totals as well as leaking identifiers.

**Fixes.**

| Change | Location |
|---|---|
| New `redact_pii()` — strips names, phones, email, Aadhaar, PAN, addresses; keeps field labels and all clinical/billing content | `packages/kadi/kadi/redaction.py` |
| `patient` entity no longer persisted — it is a direct identifier and **no module reads it** (DaaviSetu takes `patient_name` from its own request payload) | `apps/api/.../kadi.py` |
| `document_text` excerpt redacted before persistence, tagged `meta.redacted = true` | `apps/api/.../kadi.py` |
| Identity/contact labels excluded from line items; amounts of ≥10 integer digits rejected | `packages/kadi/kadi/line_items.py` |

`document_text` is retained (redacted) rather than dropped because BillNyay's appeal pipeline
reads it to recover denial codes, insurer reasons and policy clauses — a verified workflow
dependency.

**Verified live** — same document, after the fix:

```
identifier 'Ramesh Kulkarni'      persisted? False
identifier '9876543210'           persisted? False
identifier 'ramesh@example.com'   persisted? False
identifier '1234 5678 9012'       persisted? False
entity types: ['billing_item', 'diagnosis', 'document_text', 'hospital']
appeal on redacted excerpt -> HTTP 200
```

**Scope limit, now stated in the docs:** this is *direct-identifier removal*, not formal
anonymisation. A diagnosis plus a hospital name can still be re-identifying in a small
population. ADR-003 and the README were corrected to claim only what the code does.

### 14.2 Consent

**Root cause.** `consent_opt_in` was written at case creation and **read by nothing**. Every
client hardcoded `true`; the web consent checkbox existed but defaulted to checked and its
value never left the component.

**Fixes.**

| Layer | Change |
|---|---|
| Backend | New `app/consent.py::require_case_consent` — enforces from the **persisted case row**, applied to all 5 Kadi-consuming routes (BillNyay audit/appeal/grievance, DaaviSetu claim/PDF) |
| Web | Checkbox now defaults to **unchecked**; value forwarded through `onStartAudit` to the API call; `page.tsx` no longer hardcodes `true` |
| Mobile | `createCase` requires an explicit `consent_opt_in` (no default); `processScanAndUpload` requires `{ consent }` and refuses without it; consent toggle added to `CameraScanScreen` gating the shutter; `BillNyay`/`DaaviSetu` screens no longer silently create consented cases |

Enforcement cannot be bypassed by a client sending `true` on the module call, because the guard
never reads the request body — only `KadiCase.consent_opt_in`.

**Verified live:**

```
CONSENT DENIED    audit 403 | appeal 403 | claim 403 | pdf 403
CONSENT OMITTED   consent_opt_in = False   (opt-in, not opt-out)
CONSENT GRANTED   audit 200 | appeal 200
UNKNOWN CASE      404 (not misreported as a consent failure)
```

### 14.3 Security hardening

| Issue | Fix | Evidence |
|---|---|---|
| `str(exc)` returned to clients | 500 body now `{detail, error_id}`; exception logged against a 12-char correlation id | `test_unhandled_errors_do_not_leak_internal_detail` |
| Wildcard CORS + `allow_credentials=True` | Credentials enabled only with an explicit origin list; methods/headers narrowed from `*` | `test_cors_does_not_pair_wildcard_origin_with_credentials` |
| Unbounded upload | `MAX_UPLOAD_BYTES` (10 MB) → `413`; extension allow-list → `415` | `413`/`415` confirmed live |
| Unbounded SSE stream | `SSE_TIMEOUT_SECONDS` (120) closes with a `timeout` event | `test_sse_stream_has_a_bounded_timeout` |
| `processing_status` grew forever | Bounded at 500 cases, finished streams evicted first | `test_status_map_is_bounded` |
| **Web dependencies: 6 vulns (1 critical, 4 high)** | `npm audit fix` + `next` → **16.3.4** | **`npm audit` → 0 vulnerabilities** |

**On the `next` upgrade.** `npm audit` recommended `16.3.5`, but `@next/swc-win32-x64-msvc@16.3.5`
is not published, so Turbopack cannot build on win32/x64 at that version. The advisory range is
`16.0.0 – 16.3.2`, so **16.3.4 is both patched and has a Windows binding**. Declared and installed
versions now match (the 16.3.0-vs-16.2.10 lockfile drift recorded in §6.5 is also resolved).

**Mobile dependencies remain unfixed — deliberately.** All 30 advisories (1 critical, 11 high)
resolve only via Expo SDK **52 → 57**, which npm reports as `isSemVerMajor: true`. `npm audit fix`
without `--force` resolves none of them. A five-major framework upgrade is out of scope for a
low-risk hardening pass; this is recorded as the top remaining security item.

### 14.4 Documentation reconciliation

Every claim below was checked against code, not assumed.

| File | Corrected |
|---|---|
| `docs/api/overview.md` | **Rewritten** from the live route table. Previously documented 5 routes that do not exist. Now includes real request/response schemas, the three-state audit model, `llm_backed`, upload limits, `409`/`413`/`415`/`403`, and the consent rules |
| `README.md` | FAISS, IndicXlit/IndicSBERT, edge-detection scanning, hospital locator, Jan Aushadhi map, "RAG agent" all marked **planned/not implemented**; test counts corrected; privacy section rewritten |
| `ADR-003` | De-identification claim replaced with what the code does, plus an explicit scope limit and the consent-enforcement rule |
| `docs/architecture/data-flow.md` | SSE payload schema and stage list corrected to `{status, progress, log}`; removed the claim that domain analysis runs on the upload stream; retention section rewritten |
| `docs/architecture/overview.md`, `components.md` | Vector store / Indic NLP / ONNX marked planned or scaffold |
| `docs/development/testing.md` | Test counts 32→122 and 10→23; mobile test path corrected; fixture corrected from `:memory:` to file-backed, with the reason |
| `docs/configuration/environment-variables.md` | Compose block now shows `GROQ_API_KEY`; non-existent `ENVIRONMENT` var replaced with the real `MAX_UPLOAD_BYTES` / `SSE_TIMEOUT_SECONDS`; CORS and error-payload notes added |
| `CONTRIBUTING.md`, `docs/development/setup.md` | `/health` expected output updated to the 4-field response |
| `AGENTS.md`, `packages/kadi/AGENTS.md` | FAISS stack claim corrected; vector store described as an unwired scaffold |
| `packages/kadi/README.md`, `packages/schemesetu/README.md` | Patient-name normalisation claim corrected; FAISS/Indic/ONNX marked planned or unwired; new modules documented |
| `PROJECT_CONTEXT.md` | Test counts corrected; three over-stated §7 rows fixed; stale mobile-scaffold checkbox closed |

Left unchanged by design: `docs/academic/reports/ArogyaRakshak_Technical_Documentation.md` (an
academic design specification describing intended architecture, not a status claim), the
unchecked `- [ ]` edge-detection item in the task backlog (correctly marked not done), and
placement rules in `AGENTS.md`/`CONTRIBUTING.md` that say *where* IndicXlit would live if built.

### 14.5 Cross-runtime contracts

Field-by-field comparison of Pydantic models against both TypeScript clients found one drift:
mobile's `CaseResponse` declared `case_id?` and `user_id?`, neither of which the API returns —
making `caseRes.id || caseRes.case_id` a dead branch. Both phantom fields removed and the call
site simplified. All contracts now match exactly.

### 14.6 Verification

| Suite | Before this batch | After |
|---|---|---|
| Backend pytest | 92 | **122** |
| Web | 19 (14 + 5 from this batch's start) | **19** |
| Mobile | 20 | **23** |
| **Total** | **131** | **164** |
| Web `tsc` / lint / build | clean | clean |
| Mobile `tsc --noEmit` | 0 errors | 0 errors |
| Ruff (CI selection) | clean | clean |
| CI guardrails | 5/5 | **5/5** |
| `docker compose config` | exit 0 | exit 0 |
| **Web `npm audit`** | **6 (1 critical, 4 high)** | **0** |
| Mobile `npm audit` | 30 | 30 *(Expo 52→57 major; out of scope)* |

**Tests added this batch: 33** (25 backend, 3 web, 5 mobile) covering redaction, identity-line
filtering, consent granted/denied/omitted/bypass-attempt, error-detail suppression, CORS,
upload size/type limits, status-map bounding, and client consent request behaviour.

**No test was weakened.** One existing assertion was inverted deliberately:
`test_kadi_entities_are_clean_end_to_end` asserted the patient name **is** persisted; it now
asserts it is **not**, matching ADR-003. Two mobile tests that encoded the old
`consent_opt_in: true` default were updated to the explicit-consent contract — the TypeScript
compiler caught both, which is why the signature was made required rather than optional.

### 14.7 Remaining issues after this batch

1. **Mobile dependencies — 30 advisories (1 critical, 11 high).** Needs Expo SDK 52 → 57.
2. **No authentication.** Case data is still retrievable by id alone; deliberately not addressed
   per scope constraints.
3. **`processing_status` is single-process.** Bounded now, but multi-worker deployments still
   need Redis or a DB-backed store.
4. **Mobile runtime unverified.** The consent toggle and audit rendering are verified by types
   and unit tests only — no emulator run.
5. **Dead scaffolds retained:** `vector_store.py`, `embeddings.py`, `compile_appeal_packet`.
   Now documented as unwired rather than deleted.
6. **Evaluation harness (#102–#116) still absent** — 15 open metric issues, no implementation.

---

## 15. Correctness & Production-Readiness Batch (2026-09-12)

Covers generated-output integrity, module data integrity, API robustness, the Kadi
pipeline, client screens, test quality and CI enforcement.

### 15.1 Fabricated data in user-facing outputs

**The §13 DaaviSetu fix made the problem durable rather than solving it.** Persisting the
submitted claim was correct, but the *submission* path still invented values — so
fabrications were now stored and rendered onto the signed form:

```python
hospital  = hospital  or "General Hospital"
diagnosis = diagnosis or "Discharged Patient Medical Recovery"   # invented diagnosis
treatment = treatment or "General clinical medical observation"
estimated_cost = case.total_charged if case.total_charged > 0 else 45000.0
```

**Worse, both clients pre-filled every form with a plausible fake identity.** A user who
pressed Generate without editing submitted — and persisted — a pre-authorization form for
`"Viraj Jadhao"` with policy `"POL-STAR-774411"` at `"Apollo Multi-Speciality Hospital"`.
BimaNyay pre-filled a policy number, insurer, ₹180,000 claim amounts, a denial reason and
a diagnosis, all feeding a legal appeal letter.

| Fix | Location |
|---|---|
| Field resolution is now request → extracted entity → **422**, with no invented third tier | `apps/api/.../daavisetu.py` |
| `estimated_cost` accepted explicitly; falls back to the audited case total, never to ₹45,000 | same |
| Appeal placeholders `DEN-DEFAULT` / `Disputed Procedure` replaced with `"Not specified in the supplied documents"`, plus a `denial_facts_extracted` flag | `apps/api/.../billnyay.py` |
| All 8 client forms emptied; placeholders added; submit gated on required fields | 4 web views, 4 mobile screens |

Verified live:

```
claim with no resolvable data -> HTTP 422
missing: ['hospital_name', 'diagnosis', 'treatment_plan', 'estimated_cost']
pdf before valid claim        -> HTTP 409
```

### 15.2 Module data integrity

| Module | Issue | Fix |
|---|---|---|
| DawaCheck | 404 said the drug was *"not found in NPPA Schedule-I ceiling price list"* — asserting national price-control status from a **7-entry** in-code table | Message now states the reference list is a curated subset and that absence "does NOT mean" the medicine is uncontrolled |
| DawaCheck | `generic_substitute_available=True` asserted unconditionally | Derived from whether the reference entry records a generic |
| DawaCheck | No provenance on an authoritative-looking price | Added `data_source` + `reference_entry_count` |
| SchemeSetu | `category` and `medical_need` collected, transmitted, then **ignored** (0 references) while the verdict read as complete | Added `criteria_evaluated`, `criteria_not_evaluated`, `is_provisional` |
| SchemeSetu | `confidence_score` constants presented as statistical confidence | Documented as a heuristic prior for the matched rule branch |

### 15.3 API robustness — three leaks that bypassed the §14 fix

The global handler was fixed in §14, but three call sites bypassed it entirely:

1. `bimanyay.py:72` — `HTTPException(500, detail=f"...{str(e)}")`
2. `bimanyay.py:118` — same pattern
3. `kadi.py` background task — streamed `f"Failed: {str(e)}"` over **SSE into the browser**

All three now log against a correlation id and return/stream a safe message. The
`StarletteHTTPException` handler no longer stringifies structured details into `message`
(it produced a Python `repr` in the body for dict details).

Verified: a corrupt PDF streams `'The PDF could not be read.'` with no `Traceback`,
`fitz`, `PyMuPDF` or `code=7` in the payload.

### 15.4 Kadi pipeline

**Silent data loss (the most consequential find).** `parse_document` caught every parse
failure and substituted the sentence `"Hospital Bill / Clinical Document text
extraction."` as though it were the document body. The pipeline then persisted entities
from that placeholder, marked the stream **`completed`**, and told the user "Document
processed successfully" — on a document it had never read. The user then saw an empty
audit and had no way to know extraction had failed.

`parse_document` now returns `extraction_ok` / `extraction_error`, derives line items only
from real text, and the background task halts and marks the stream `failed`. Verified: a
corrupt PDF yields `status='failed'` and **0 entities persisted** (previously 1 bogus
`document_text` entity and a "completed" stream).

**Parser inconsistency.** `_find_hospital_name` substring-matched `"clinic"`, so any line
containing the word **"clinical"** became the facility name — `"Some unstructured clinical
note"` was returned as the hospital and would have been printed on a pre-auth form. Now
word-boundary matched; real names (`Ruby Hall Clinic`, `Apollo Medical Centre`) still
resolve. This was found *by* a regression test, not by inspection.

**Shared logic.** Confirmed genuinely shared: a repo-wide scan found no duplicated
line-item regex outside `kadi/line_items.py`. Both the OCR stage and the extraction
fallback call it.

### 15.5 Clients

- All 8 forms de-fabricated (§15.1) with submit guards.
- New backend disclosure fields wired into both clients' types: `criteria_not_evaluated`,
  `is_provisional`, `data_source`, `reference_entry_count`, `estimated_cost`.
- DaaviSetu web gained a diagnosis input; blank optional fields are omitted from the
  request so the API can fall back to extracted entities rather than storing `""`.
- **Mobile runtime remains unverified** — no emulator was launched. Mobile changes are
  verified by `tsc --noEmit` and unit tests only.

### 15.6 Test quality

Weak shape-only assertions replaced with value-level ones:

| Test | Was | Now |
|---|---|---|
| `test_billnyay_audit` | `"total_charged" in data` | exact per-item charges, benchmarks, statuses, and totals (3000 / 1850 / 1150) |
| `test_schemesetu_eligibility` | `len(data) > 0` | both schemes present with asserted verdicts |
| `test_dawacheck_benchmark` | `is_overcharged is True` | ceiling 2.30 and deviation 52.17% |
| `test_daavisetu_claim` | 2 fields echoed | all 6 fields round-trip, hospital sourced from the document |
| `test_parse_document_pdf_fallback` | asserted the placeholder sentence | asserts failure is *signalled* |

Two cross-module integration tests added: one document driving Kadi → BillNyay →
DaaviSetu → PDF with values tracked through every stage, and the same document proving
consent blocks every module.

### 15.7 CI

**Web tests never ran in CI.** `web-ci` executed `npm ci`, `lint`, `build` only — the
(now 25) web tests were dead weight. Added an explicit test step. Also pinned `tsx` as a
devDependency; the test script previously relied on `npx tsx` fetching the runner at
execution time, which `npm ci` does not guarantee.

### 15.8 Verification

| Suite | Before batch | After |
|---|---|---|
| Backend pytest | 122 | **139** |
| Web | 19 | **25** |
| Mobile | 23 | **27** |
| **Total** | **164** | **191** |
| Web `tsc` / lint / build | clean | clean |
| Mobile `tsc --noEmit` | 0 errors | 0 errors |
| Ruff (CI selection) | clean | clean |
| CI guardrails | 5/5 | **5/5** |
| `docker compose config` | exit 0 | exit 0 |
| Web `npm audit` | 0 | **0** |
| Cross-runtime contracts | consistent | **10/10 consistent** |

**27 tests added.** No test weakened. Three existing tests were updated because they
encoded behaviour now deliberately changed — each became stricter:
`test_daavisetu_claim` (relied on an invented diagnosis), `test_parse_document_pdf_fallback`
(asserted the placeholder-on-failure), and `test_billnyay_audit`/`test_schemesetu_eligibility`/
`test_dawacheck_benchmark` (shape-only → value-level).

**Dead code:** one import (`HTTPException` in `bimanyay.py`) became unused through this
batch's changes and was removed. The remaining Ruff `F401`/`F841` findings were verified
pre-existing in files this batch did not touch and were left alone.

### 15.9 Remaining issues

1. **Mobile dependencies — 30 advisories (1 critical, 11 high).** Still requires Expo SDK
   52 → 57; no non-major fix exists.
2. **No authentication.** Case data remains retrievable by id alone.
3. **`processing_status` is single-process.** Bounded, but multi-worker needs Redis/DB.
4. **Mobile runtime unverified.** No emulator run in any session to date.
5. **SchemeSetu remains income/state only.** Now disclosed rather than fixed — evaluating
   category and SECC status is a feature, deliberately out of scope.
6. **DawaCheck reference list is 7 formulations** against a stated 800–900. Now disclosed
   via `data_source`; ingestion is issue #16.
7. **Evaluation harness (#102–#116) still absent.**

## Appendix A — Verification Commands

```bash
python -m pytest                                    # 36 passed
python scripts/ci_guardrails.py                     # 5/5 passed
python -m ruff check apps/api packages              # 251 errors (CI selection: clean)
cd apps/web  && npm test && npm run lint && npm run build && npx tsc --noEmit
cd apps/mobile && npm run type-check && npm test    # 0 errors / 17 passed
docker compose config                               # exit 0
```

Note: the repository requires **Python 3.11** (`py -3.11` on this host). The default `python` on the audit machine is 3.14 and has none of the dependencies installed — consistent with `PROJECT_CONTEXT.md` §11 Known Issue 1.

## Appendix B — Explicitly Unverified

Recorded as unverified rather than assumed working:

1. **Mobile app runtime** — never launched on a device or emulator. Type-check and unit tests passing is not evidence that screens render or that camera capture works.
2. **Docker image builds** — not built locally (multi-GB torch layer). CI reports success on `main`; the containers were never *run* in CI either.
3. **PostgreSQL + pgvector runtime** — all local testing used SQLite. pgvector is never actually enabled at runtime (`setup_pgvector_index` is never called).
4. **Groq LLM path** — no API key available. Every LLM code path in this audit executed its fallback branch. The real Groq behaviour of `extraction.py`, `GroqClient`, the auditor, clinician and barrister agents is **untested and unobserved**.
5. **EasyOCR accuracy** — the library imports and the code path exists, but `parse_document` swallows all exceptions into a placeholder string, so no test in the repo distinguishes "OCR worked" from "OCR failed silently".
6. **Web ↔ API integration in a browser** — verified by code reading (paths and schemas match) and by driving the API directly; no browser session was run against a live backend.

---

*Audit performed 2026-09-11 against commit `ec93e3a`. Findings are evidence-based; anything that could not be executed or read directly is marked unverified above rather than assumed.*
