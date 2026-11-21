# Wave 2 handoff: Stream C (context reuse, #112)

## What shipped
- `apps/api/app/telemetry/context_metrics.py`: `ContextRequestEvent`, `record_context_request`,
  `record_context_work`, `totals()`. Counters `arogya_context_requests_total{module,outcome}` and
  `arogya_context_work_total{kind,phase}` on the existing registry via its public API
  (`metrics.registry`, `reset_for_tests`); they rebind automatically after a registry rebuild.
  Closed label sets, PHI-fuzz test.
- `apps/api/app/services/context_requests.py`: `note_context_request` hook plus `reuse_enabled()`.
  Hooks (one line each) in `billnyay_audit` (audit, ICD audit), `billnyay_appeal`
  (`case_document_text`), `dawacheck_benchmarks`, `schemesetu_eligibility`, and two
  `record_context_work` lines in `case_ingestion._run_pipeline`. Behaviour unchanged: a test runs
  every scenario with reuse on and off and compares the module responses (canonicalised for row
  order and per-call ids/timestamps).
- Env var `CONTEXT_REUSE_ENABLED` (default true), documented in
  `docs/configuration/environment-variables.md` and `.env.example`. Env-only (not in `Settings`,
  because `config.py` was not in this stream's files).
- `apps/api/app/evaluation/context_reuse.py`: pure `evaluate_context_reuse(rows)`.
- `data/evaluation/context_reuse_synthetic.jsonl` (n = 5 scenarios A-E), verified against the live
  pipeline by `tests/test_context_scenarios.py`.
- `docs/evaluation/context-reuse.md`. Result: CRR 1.00 (14/14), DPR 0.76 (12 vs 50 work units).

## Decisions
- Context request = a service-layer read of stored case context; `reused` iff it returned at least one item.
- Baseline is modelled by counting (no re-extraction is run), because documents are not retained.
- Counters live in their own module rather than in `metrics.py` internals.

## Wiring the integrator must add
`apps/api/app/evaluation/runner.py`:
```python
DATASETS["context_reuse"] = "context_reuse_synthetic.jsonl"
# the scorer takes the dataset rows directly, so it is its own runner:
from app.evaluation.context_reuse import evaluate_context_reuse
_RUNNERS["context_reuse"] = evaluate_context_reuse
```
`apps/api/app/evaluation/regression.py`:
```python
MetricSpec("context_reuse.crr", "higher"),
MetricSpec("context_reuse.dpr", "higher"),
# COUNT_METRICS:
"context_reuse.n_scenarios", "context_reuse.n_requests",
```
Then regenerate the baseline with `scripts/evaluate_phase4.py`. Expected values now: crr 1.0,
dpr 0.76, n_scenarios 5, n_requests 14. Optionally add the two metric names to the table in
`docs/operations/observability.md` and a Grafana panel; this stream did not touch either.

## Not verified / follow-ups
- DaaviSetu readiness (`app/clinical/context.py`), DaaviSetu claims routes, case timeline and claim
  pack read entities outside `services/**`; not instrumented (see the doc). Hooking them would make
  scenarios B and E informative.
- CRR of 1.00 is nearly by construction; DPR depends on the counting model. No production traffic,
  no LLM-call counts, no timing.
- `test_context_scenarios.py` regenerates dataset rows only with `CONTEXT_REUSE_REGEN=1`.
