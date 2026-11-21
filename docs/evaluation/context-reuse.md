# Context reuse: CRR and DPR (#112)

**What this measures:** instrumented counts on the five SYNTHETIC demo scenarios (A-E), n = 5
scenarios and 14 context requests. It is **not production traffic** and says nothing about
extraction quality. The baseline is **modelled** (counted), not executed: see "Honest limits".

## Definitions (decided before measuring, Phase 4 decision D8)

- **Context request**: a module asking Kadi's stored case context for entities, line items or the
  timeline. Hook: `note_context_request` (`apps/api/app/services/context_requests.py`).
- **Outcome**: `reused` when the case already held context that answered the request (at least one
  stored item); `fresh` when it held nothing usable, or when reuse is switched off.
- **CRR** = `reused` requests / all context requests.
- **Work units**: one OCR unit and one extraction unit per document pass. `ingest` is the one pass
  done when a document is taken in; `repeat` is the pass a module would have to redo without a
  shared context.
- **DPR** = (baseline work - current work) / baseline work. Baseline = the same flow with
  `CONTEXT_REUSE_ENABLED=false`, where every request repeats OCR + extraction over each document
  the case holds at that moment.

## Where requests are instrumented

| Hook | Module label | Context |
|---|---|---|
| `build_case_audit` (billing items) | `billnyay` | line_items |
| `build_case_icd_audit` (diagnosis + procedures) | `billnyay` | entities |
| `case_document_text` (appeal and grievance) | `billnyay` | entities |
| `build_case_medicine_benchmarks` | `dawacheck` | entities |
| `case_medical_need` (eligibility) | `schemesetu` | entities |

Upload-time auto-triggers call the same service functions, so they are counted as requests too.
Ingestion work is counted in `case_ingestion._run_pipeline` (`arogya_context_work_total{phase="ingest"}`).

Metrics (`app/telemetry/context_metrics.py`, on the existing private registry): 
`arogya_context_requests_total{module,outcome}` and `arogya_context_work_total{kind,phase}`.
Labels come from closed sets, anything else collapses to `other`; no case id or text is ever a
label (PHI-fuzz test in `tests/test_context_metrics.py`).

## Result (synthetic scenarios A-E, reuse on versus `CONTEXT_REUSE_ENABLED=false`)

| Scenario | Requests | Reused | CRR | Current work | Baseline work | DPR |
|---|---|---|---|---|---|---|
| A bill + discharge summary, audit, ICD audit, appeal | 7 | 7 | 1.00 | 4 | 28 | 0.857 |
| B pre-authorisation request (upload-time checks) | 2 | 2 | 1.00 | 2 | 6 | 0.667 |
| C prescription image, DawaCheck benchmark | 2 | 2 | 1.00 | 2 | 6 | 0.667 |
| D denial letter, appeal | 1 | 1 | 1.00 | 2 | 4 | 0.500 |
| E diabetes admission note (upload-time checks) | 2 | 2 | 1.00 | 2 | 6 | 0.667 |
| **Pooled** | **14** | **14** | **1.00** | **12** | **50** | **0.76** |

Dataset: `data/evaluation/context_reuse_synthetic.jsonl` (first line `_meta`, `synthetic: true`).
`apps/api/tests/test_context_scenarios.py` re-runs the scenarios through the real upload pipeline
and fails if the dataset differs from the observed counts (regenerate with
`CONTEXT_REUSE_REGEN=1`). `evaluate_context_reuse` (`app/evaluation/context_reuse.py`) is pure and
unit-tested with hand-computed expectations; a mutation check (changed DPR formula, CRR
denominator, reused/fresh swap) was caught by those tests.

## Honest limits

- **CRR of 1.00 is close to true by construction**: modules already read Kadi's stored entities and
  never re-extract, so every request that finds stored context is a reuse. The figure shows the
  instrumentation works and that no module bypasses the shared context in these flows. It would
  fall below 1 only when a module asks for context the case does not hold (the unit test
  `test_a_request_for_context_the_case_does_not_hold_is_fresh` shows that path).
- **The baseline is modelled, not executed.** With reuse off nothing is re-run (zero document
  retention: the document is gone after ingestion). The repeat work is the count of OCR and
  extraction passes a re-extracting design would do, one per document per request. DPR therefore
  grows with the number of requests per case and is a property of the counting model; a real
  re-extraction would also repeat LLM calls, which are not counted here.
- Scenario C's OCR and extraction are a recorded replay (demo mode); the pipeline stages are
  counted as for any upload.
- Not instrumented yet (outside the files this stream owned): DaaviSetu readiness and claim
  routes (`apps/api/app/clinical/context.py`, `api/v1/endpoints/daavisetu/claims.py`), the case
  timeline (`app/case_timeline.py`), claim pack, and Kadi's own reads. Scenarios B and E exercise
  DaaviSetu readiness in their scripts, so their counts come only from the upload-time module checks.
- Request counts depend on which module calls the flow makes (listed per row in the dataset).
