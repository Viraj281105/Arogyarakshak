# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- Human clinical review, safety governance and human OCR resolution layer (ADR-011, `docs/architecture/clinical-review.md`): attributable clinical statements with mandatory conflict-of-interest disclosure and honest verification status; institution-private DaaviSetu preauth readiness playbooks; bounded BillNyay clinical plausibility review; versioned, independently approved clinical safety escalation rules; blind two-reader transcription of uncertain OCR medication text; provenance classes (`AI_DERIVED`, `HUMAN_REVIEWED`, `HUMAN_AUTHORED`, `EXTERNAL_SOURCE`, `PATIENT_PROVIDED`); web reviewer workspace at `/clinical-review`; mobile patient-side cards.

### Fixed (ADR-011 audit)
- OCR transcription tasks no longer flood on letterheads/"Rx"/"Tab.", never forward prescriber names, link only by whole tokens to one medicine, and apply a reading by replacing only the uncertain token.
- A withdrawn, superseded or cancelled clinician statement is removed from the stored signed appeal PDF.
- The insurer-facing appeal PDF no longer carries a "no clinician statement" notice; that notice is patient-facing only.
- Plausibility no longer treats room/nursing lines as interventions and discloses billed items it did not assess.
- Safety rules now check each document's full text at upload; readiness discloses its 1,000-character search scope.
- Only independently verified reviewers are listed publicly; others are assigned by shared ID. Demo reviewers are locked out outside demo mode.
- Safety-rule approvals are tied to a submission round.
- Safety-check failures are shown explicitly. Mobile DaaviSetu now receives its scanned case; mobile screens wait for processing before reading it.

### Fixed (second ADR-011 audit)
- The per-document OCR task cap now counts linked tasks only; letterhead noise at the top of a page could previously use it up so the medicine lines were never flagged.
- A whole uncertain OCR line naming a medicine (e.g. "Tab Augmntn 625mg 1-0-1") now links to that medicine; a leading "Tab."/"Cap." no longer prevents a human reading from being applied.
- A human reading that cannot be placed into the extracted entry is recorded as `NOT_APPLIED`; DawaCheck no longer falls back to benchmarking the uncertain OCR text, and a later partial reading cannot clear that state (a whole-entry flag can).
- A red flag found in a document's full text is no longer lost when the safety rule is re-versioned; it carries forward to the active version while that version still lists the term.
- Plausibility coverage is PARTIAL (not FULL) when a diagnosis could not be assessed.
- Reviewer-facing review responses no longer include the patient's case id.

### Added (demo-hardening pass, 2026-09-27)
- One medicine trust gate (`kadi.clinical_review.medicine_trust`) used by DawaCheck and reviewer evidence; DawaCheck rows carry `trust` (state, label, reasons).
- Uncertain OCR readings that cannot be linked to exactly one medicine are no longer dropped: the medicine(s) they may concern are held back as `ocr_uncertainty` (`AMBIGUOUS`, `POSSIBLE_MATCH`, `OVER_CAP`, `UNGROUNDED`) and are not benchmarked until a whole-entry human reading settles them.
- Deterministic demo kit (`demo/`): synthetic documents, Scenarios A–D with expected output, and a demo-mode-only OCR replay for the Scenario C prescription image (`app/clinical/demo_ocr.py`). Each scenario is an automated test.
- Web DawaCheck shows the case's own medicines with their trust decision and an "Ask for a human reading" action.
- Mobile: processing lifecycle state machine (`services/caseProcessing.ts`) with a 90 s inactivity timeout ("Processing is taking longer than expected." + "Refresh status"), shared active case across tabs, case-medicines card.
- SSE stream emits `idle` at once when nothing is being processed for the case.

### Fixed (demo-hardening pass, 2026-09-27)
- Readings linking to no medicine, to several medicines, or beyond the task cap let the medicine be benchmarked as `AI_DERIVED`; LLM-normalised names ("Amoxycilin" → "Amoxicillin") lost the OCR uncertainty.
- A human reading of only a marker could produce names like "Tab. 40"; results that name no drug are now refused.
- An agreed transcription of a whole uncertain line that is exactly the entry ("Tab Augmntn 625mg 1-0-1 x 5 days") was always `NOT_APPLIED`; it is now placed. A later whole-entry reading overrides an earlier escalation only if it is later; partial readings never clear held-back states.
- Entity resolution auto-merged combination products into their base drug ("Pan-D" into "Pan 40"); a one-sided variant letter is now a conflict for medicines (evaluation unchanged: 0 false merges).
- Plausibility returned PLAUSIBLE when one intervention matched and another is expected for an undocumented diagnosis; now CLINICAL_REVIEW_RECOMMENDED with `conflicting_items`. More administrative lines are excluded; the summary says unassessed diagnoses are not treated as compatible.
- A failing safety evaluation surfaces as `status: UNAVAILABLE` ("Safety check unavailable"), never as "no rules active"; plausibility survives it and recommends review.
- One board member could retire a safety rule alone; retirement is now request + independent confirmation.
- Mobile screens read the case before processing was established (first-render race), BillNyay audited straight after the upload 202, a stale response could overwrite newer state, and tabs did not share the scanned case (DaaviSetu was unreachable for a scanned bill).
- Web module views computed on a half-built case during processing; a dropped/silent stream showed nothing.
- "Judge-Approved Draft" (an automated scorer) relabelled "Passed automated quality check" (web + mobile; Hindi/Marathi rewording needs native-speaker QA). "Audit Completed" after extraction relabelled "Extraction complete".

### Changed
- BillNyay appeals now append finalized clinician statements verbatim (or state that none exists); the Barrister prompt forbids implying a clinician's opinion; the offline appeal template no longer asserts that physician records prove necessity.
- Kadi OCR now returns EasyOCR per-segment confidence; low-confidence readings become human transcription tasks.
- DawaCheck no longer benchmarks a medicine whose uncertain reading is unresolved.

### Added (earlier)
- Comprehensive repository-wide documentation overhaul, including structured `/docs` architecture, ADRs, and contributor manuals.
- Scoped AI coding agent manuals (`AGENTS.md`, `apps/api/AGENTS.md`, `apps/web/AGENTS.md`, `packages/kadi/AGENTS.md`, `.github/AGENTS.md`).
- Architectural specification for `BimaNyay` (insurance claim denial dispute analysis & IRDAI 3-tier grievance escalation engine).
- Architectural roadmap for cross-platform mobile application (`apps/mobile`) in React Native / Expo.
- Dedicated GitHub issue templates (Bug Report, Feature Request) and PR Template.
- Open-source governance files (`CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, `.gitattributes`).

### Changed
- **SchemeSetu no longer decides eligibility from income thresholds.** The PMJAY ₹2,50,000 and MJPJAY ₹1,50,000 limits were unverified heuristics; the official sources now cited in `packages/schemesetu/schemesetu/thresholds.py` (PIB releases 2116209 and 2053883; Government of Maharashtra restatements of the GR dated 28 July 2023) define no income ceiling. Income is reported as non-determinative, PMJAY is reported `ambiguous` with verification steps, MJPJAY follows state of residence, and every result cites its sources.
- **API:** `SchemeResult.confidence_score` removed; `non_determinative_factors`, `criteria_provenance` and `sources` added. The income-profile trigger now returns `FIRE` | `NO_CHANGE` | `INSUFFICIENT_EVIDENCE` with `schemes_applicable`, `newly_applicable` and `income_role` (replacing `NO_THRESHOLD_CROSSED`, `*_within_threshold` and `threshold_provenance`). Web and mobile clients render `ambiguous` as "Verification needed" instead of "Not Eligible".

### Removed
- `packages/schemesetu/schemesetu/embeddings.py` (`OfflineEmbedder`): an unwired scaffold that nothing imported. Its fallback built vectors from Python's per-process-salted `hash()`, so they were not reproducible. Domain modules may not ship their own embedding layer; cross-lingual embeddings belong to Kadi's optional IndicSBERT signal (`kadi/resolution/semantic.py`, ADR-006).

---

## [0.2.0] - 2026-08-20

### Added
- **Phase 1 Foundations**:
  - Implemented Kadi core extraction engine (`packages/kadi/kadi/extraction.py`) and vector store indexer (`packages/kadi/kadi/vector_store.py`).
  - Added shared OCR parser (`packages/kadi/kadi/ocr/ocr_parser.py`).
  - Integrated SchemeSetu rule-based eligibility agent (`packages/schemesetu/schemesetu/agent.py`). *(Corrected: this entry originally claimed a RAG agent and an ONNX embedding fallback. Neither existed — `embeddings.py` was an unwired SentenceTransformer scaffold with no ONNX code, since removed.)*
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
