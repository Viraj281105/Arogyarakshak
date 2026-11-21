# Context hit rate and duplicate-processing reduction (#112)

**What this measures:** counts collected from the instrumented pipeline on the five SYNTHETIC
demo scenarios (A-E): n = 5 scenarios, 20 context reads. It is **not production traffic** and
says nothing about extraction quality. The headline covers only the instrumented readers listed
below, and the DPR is a **modelled** figure.

## Definitions (Phase 4 decision D8; the earlier "CRR / reused" wording was dropped)

- **Context request**: a read of a case's stored context (entities, line items, timeline). Every
  read goes through one function, `load_case_entities` (`apps/api/app/services/case_context.py`),
  which runs the shared query and records one event. It issues no SQL of its own.
- **Outcome**: `served` when the read returned at least one stored item; `empty` when the case held
  nothing for it.
- **Context hit rate** = served / all requests. This measures **non-emptiness, not reuse**:
  modules never re-extract, so a read of a populated case is served by construction and the rate
  is about 1. It is reported for transparency and **must not be gated**. No observable notion of
  "reuse" (a read after an earlier consumer read the same context) is defined here, so the word
  is not used.
- **DPR** = (baseline work - current work) / baseline work, **modelled, not measured**:
  `current = ingest work` (OCR + extraction passes actually done) and
  `baseline = ingest work + requests x documents x 2` (a design in which every read re-runs OCR and
  extraction over each document). Nothing is re-run: documents are not retained after ingestion,
  so the document count is passed to the scorer as data (`app/evaluation/context_reuse.py`).
  DPR therefore grows with reads per case and documents per case; it is a property of the counting
  model, not evidence of measured time or cost saved. LLM calls are not counted.

## Instrumented readers (the only reads in the headline)

| Reader | `module` | `context` |
|---|---|---|
| BillNyay CGHS audit (`build_case_audit`) | billnyay | line_items |
| BillNyay ICD audit, appeal/grievance document text | billnyay | entities |
| DawaCheck case benchmark | dawacheck | entities |
| SchemeSetu case medical need | schemesetu | entities |
| DaaviSetu claim form and claim summary text | daavisetu | entities |
| Clinical review context, auto-trigger readiness snapshot, case details | kadi | entities |
| Case timeline | kadi | timeline |
| Claim pack billing check | kadi | line_items |

`tests/test_architecture.py` fails if `KadiEntity` is selected anywhere else, except
`clinical/transcription_service.py` (a single-entity lookup on a write path). `module` and
`context` are `Literal` types and a test checks every call site's values, so a typo is a red test.
Ingestion work is counted in `case_ingestion._run_pipeline`.

Metrics (`app/telemetry/context_metrics.py`): `arogya_context_requests_total{module,context,outcome}`
and `arogya_context_ingest_work_total{kind}`; closed label sets, PHI-fuzz test.

## Result (synthetic scenarios A-E)

| Scenario | Reads | Served | Current work | Baseline work | DPR |
|---|---|---|---|---|---|
| A bill + discharge summary, audit, ICD audit, appeal | 9 | 9 | 4 | 40 | 0.900 |
| B pre-authorisation request (upload-time checks) | 3 | 3 | 2 | 8 | 0.750 |
| C prescription image, DawaCheck benchmark | 3 | 3 | 2 | 8 | 0.750 |
| D denial letter, appeal | 2 | 2 | 2 | 6 | 0.667 |
| E diabetes admission note (upload-time checks) | 3 | 3 | 2 | 8 | 0.750 |
| **Pooled** | **20** | **20** | **12** | **70** | **0.829** |

Hit rate 1.00 (20/20). The dataset `data/evaluation/context_reuse_synthetic.jsonl` is produced by
`python scripts/generate_context_reuse_dataset.py`; `tests/test_context_scenarios.py` only
compares a fresh run with it. The scorer is unit-tested with hand-computed expectations and was
mutation-checked (baseline without the document factor, inverted DPR, served/empty swap; also the
reader without its record call and a raw `select(KadiEntity)` for the architecture test).

## Honest limits

- Hit rate 1.00 is a consequence of the design, not a result about reuse.
- DPR is the output of a counting model over synthetic flows; the baseline is not executed.
- Scenario C's OCR and extraction are a recorded replay (demo mode); the stages are counted as
  for any upload.
- DaaviSetu readiness (scenarios B and E scripts) is not a separate read here: readiness uses the
  clinical context reader, but only the upload-time auto-trigger reads are in these flows.
- Call lists per scenario are in the dataset (`module_calls`); they decide the read counts.
