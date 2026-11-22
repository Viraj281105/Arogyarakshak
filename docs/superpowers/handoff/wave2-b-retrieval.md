# Wave 2 handoff — stream B (retrieval, SchemeSetu ranking, citations, hi/mr explanations)

Branch `wave2/b-retrieval`. Figures, definitions and caveats: `docs/evaluation/retrieval.md`; every figure there is
regenerated into `docs/evaluation/retrieval_results.json` (SYNTHETIC hand-labelled sets written by the retriever's author;
the tuning set is optimistic because the floors were chosen on it; the held-out slice is small).

## What shipped

- `packages/kadi/kadi/retrieval/` — `chunk_document` (linear time, limits, one-sentence overlap), `Bm25Index`,
  `CaseRetrievalIndex` (in-memory, `purge()`, context manager, thread-safe), `Hit(source, page, quote, score)`, `tokenize`.
  Hit text is untrusted document data. No new dependency. No env var.
  Defaults: `min_score=0.0`, `min_score_ratio=0.25`, `min_coverage=0.5` (all terms for 1-2 term queries).
- `packages/schemesetu/schemesetu/{ranking,citations,explain_i18n}.py` (+ tests), imported from the submodules (not exported
  from `schemesetu/__init__.py`). `agent.py` and its tests untouched.
- `apps/api/app/evaluation/retrieval.py` (harness, `build_results()`), `retrieval_corpus.py` (generates the corpus from the
  source modules), `data/evaluation/retrieval_{corpus,queries,heldout}_synthetic.jsonl`,
  `docs/evaluation/retrieval_results.json`.
- Tests: `packages/kadi/tests/test_retrieval.py`, `packages/schemesetu/tests/test_{ranking,citations,explain_i18n}.py`,
  `apps/api/tests/test_evaluation_retrieval.py`.

## Wiring the integrator must add (I did not edit these files)

`apps/api/app/evaluation/runner.py`

```python
from app.evaluation.retrieval import evaluate_retrieval_dataset   # with the other imports

DATASETS["retrieval"] = "retrieval_queries_synthetic.jsonl"       # add to the DATASETS dict (the tuning set)

def _retrieval(rows):
    _meta, corpus = load_dataset(DATA_DIR / "retrieval_corpus_synthetic.jsonl")
    return evaluate_retrieval_dataset(corpus, rows)

# add to the _RUNNERS dict:  "retrieval": _retrieval
```

`apps/api/app/evaluation/regression.py`

```python
# HEADLINE_METRICS (all "higher"; the paths resolve against evaluate_retrieval_dataset output)
MetricSpec("retrieval.mrr", "higher"),
MetricSpec("retrieval.recall_at_k", "higher"),
MetricSpec("retrieval.pcra", "higher"),
MetricSpec("retrieval.precision", "higher"),
MetricSpec("retrieval.abstention_rate", "higher"),
MetricSpec("retrieval.at_k.3.hit_rate", "higher"),

# COUNT_METRICS
"retrieval.queries", "retrieval.answerable",
```

Then regenerate the baseline in a reviewed commit
(`python scripts/check_eval_regression.py --write-baseline apps/api/app/evaluation/baseline/phase4_baseline.json`).
Take the values from the regenerated baseline, not from this file: the figures in `docs/evaluation/retrieval.md` are the
reference and carry the tuning caveat (tuning set: MRR 0.72, hit@3 0.72, abstention 0.94 at n=63; held-out: MRR 0.73,
abstention 0.80 at n=20; tuned/synthetic; two decimals on purpose). A zero-tolerance gate on a tuned synthetic set guards
against regressions only. The held-out file is reported by `retrieval_results.json`, not by the runner. Any existing test
that asserts the exact set of `DATASETS` keys will need the new key.

## Decisions

- Floors: the absolute BM25 floor made every single-term query abstain in a 1-3 chunk index, so the default floor is a
  fraction (0.25) of the query's own best achievable score; a coverage floor requires all terms for 1-2 term queries and
  ceil(50%) otherwise ("PAN card" must not match "ration card"). Chosen on the tuning set.
- Tokeniser fold copied from `kadi.injection._matching_view` (parity test; that file belongs to another stream).
- `schemesetu` does not import `kadi`: `verify_citation` takes anything with a `.quote` and optional `.scheme`;
  `explain_i18n` builds its own `CitedSpan`, keeping the domain-package independence contracts intact.
- `verify_citation` statuses: `supported`, `scheme_only`, `unsupported`, `uncheckable`; scheme names are matched in the span
  body only (the title is carried separately and ignored) and figures must sit near the named scheme in a multi-scheme span.
- Ranking relevance = 0.3 state specificity + 0.7 share of stated medical-need words in the scheme's cited criteria text; never
  uses income.
- The corpus file is generated from the source modules and a test fails on drift. **If stream A/C/E (bimanyay, daavisetu,
  schemesetu wording) changes those texts the drift test will fail after integration:** run
  `cd apps/api && python -m app.evaluation.retrieval_corpus && python -m app.evaluation.retrieval`, re-check the labels in the
  queries files, and recommit.

## NOT verified / limits

- No Hindi/Marathi retrieval measured (no clean Devanagari corpus). hi/mr templates, stop-word and number-word lists are
  `NEEDS NATIVE-SPEAKER QA`.
- `verify_citation` is a string check on figures and scheme names, not semantic entailment (pinned limitation); only PMJAY and
  MJPJAY are recognised.
- Nothing calls the retrieval index in production code, so the BYOD hook (`purge()` when a case session ends) is for whoever
  wires it. Not measured on real documents/OCR output or on large corpora.
- Filesystem-silence is tested through the common file-creating entry points only (a tripwire, not a proof).
