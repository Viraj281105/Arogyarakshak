# Wave 2 handoff: Stream C (context reads, #112) - after review round 1

## What shipped
- `app/services/case_context.py::load_case_entities(db, case_id, types, *, module, context)`: the single
  reader of stored case context; runs the shared query, records exactly one event, issues no SQL of its
  own. `Module`/`ContextKind`/`Outcome` are `Literal` types (`app/telemetry/context_metrics.py`).
- Migrated to it: billnyay audit/ICD/appeal text, dawacheck, schemesetu, `clinical/context.py`,
  `case_timeline.py`, `auto_triggers.py`, daavisetu claims (2 reads), `claim_pack.py`, `kadi/cases.py`.
  Allow-listed (reason in the test): `clinical/transcription_service.py` single-entity write-path lookup.
  `tests/test_architecture.py` fails if `KadiEntity` is selected anywhere else.
- Counters `arogya_context_requests_total{module,context,outcome}` (outcome `served|empty`) and
  `arogya_context_ingest_work_total{kind}`; both built together under a lock, logs carry the exception
  type name only.
- Removed: `CONTEXT_REUSE_ENABLED`, `reuse_enabled()`, the switch-off branch and its `count(*)` query
  (a hook never touches the request session now), the second "reuse_off" run, the env/.env.example/doc
  entries (restored to the base versions).
- Scorer `evaluate_context_reuse(rows)` (`app/evaluation/context_reuse.py`): hit rate and a modelled DPR,
  baseline computed inside the scorer from explicit data (`ingest + requests x documents x 2`), uses
  `metrics.safe_div`, rounds only in the report. Rows: `{id, documents, ingest, requests{module{served,empty}}}`.
- Dataset generation moved to `scripts/generate_context_reuse_dataset.py` (throwaway SQLite in a temp
  dir); `tests/test_context_scenarios.py` compares only. Shared flows: `tests/context_flows.py`.
  PHI helpers moved to `tests/telemetry_helpers.py` (`test_telemetry_metrics.py` now imports them).
- Result (synthetic A-E, n=5, 20 reads): hit rate 1.00, DPR 0.8286 (12 vs 70 work units).

## Wiring the integrator must add
`apps/api/app/evaluation/runner.py`:
```python
DATASETS["context_reuse"] = "context_reuse_synthetic.jsonl"
from app.evaluation.context_reuse import evaluate_context_reuse
_RUNNERS["context_reuse"] = evaluate_context_reuse   # takes the rows directly
```
`apps/api/app/evaluation/regression.py`: **gate only DPR and the counts. Do not gate the hit rate**
(it measures non-emptiness and is about 1 by construction).
```python
MetricSpec("context_reuse.dpr", "higher"),
# COUNT_METRICS:
"context_reuse.n_scenarios", "context_reuse.n_requests",
```
Regenerate the baseline with `scripts/evaluate_phase4.py`. Expected: dpr 0.8286, n_scenarios 5, n_requests 20.
`hit_rate` may appear in the report but not in the headline list. Optionally add the two counters to
`docs/operations/observability.md`.

## Not verified / limits
- DPR is a counting model on synthetic flows; the baseline is never executed. No production traffic,
  no LLM-call counts, no timing. Hit rate 1.00 is by construction.
- `ingest` work in the replayed scenario C is counted although OCR is replayed (demo mode).
- Stream F edits `services/billnyay_audit.py` matcher functions; this stream touched only the two
  context-read blocks there.
