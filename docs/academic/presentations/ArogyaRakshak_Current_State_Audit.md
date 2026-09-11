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
