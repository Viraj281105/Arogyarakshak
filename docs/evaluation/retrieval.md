# Retrieval, citation checking and Hindi/Marathi explanations (Wave 2, stream B)

> **Read this first.** Every number below is measured on a **SYNTHETIC, hand-labelled** gold
> set of **47 queries over 27 English passages** copied from clean in-repo text. The queries
> were written by the same team that wrote the retriever, the labels were assigned before the
> first run, and the coverage floor (below) was chosen **after** seeing this set, so the
> figures are optimistic for that reason. They are **not** real-world retrieval accuracy, not
> a held-out test, and say nothing about Hindi/Marathi retrieval or about the real downloaded
> PDFs.

## What shipped

| Piece | Where | Rule it enforces |
|---|---|---|
| `kadi.retrieval` | `packages/kadi/kadi/retrieval/` | Pure-Python deterministic BM25. `search` returns `[]` (never a guess) when no chunk clears a score floor **and** a query-term coverage floor. Retrieval only surfaces verbatim quotes; it never decides anything. |
| Per-case index | `CaseRetrievalIndex` | In memory only, `purge()` / `with` block expunges it (BYOD). A test forbids every file open/create/temp-file call during add, search and purge. No document text in logs. |
| Ranking | `schemesetu.ranking.rank_schemes` | Eligibility status first, relevance second, always `provisional=True`. Verdicts are copied, never changed; `schemesetu/agent.py` is untouched. Income is never used. |
| Citation check | `schemesetu.citations.verify_citation` | A sentence is `supported` only if every figure (Devanagari digits, lakh/crore normalised) and every scheme name it asserts is in the cited span; with neither it is `uncheckable`, never `supported`. |
| hi/mr explanations | `schemesetu.explain_i18n` | Fixed templates chosen by scheme and the already-computed verdict, each sentence with a citation key that resolves to the cited source text. No machine translation, no model call. **All Hindi/Marathi wording is UNREVIEWED: `NEEDS NATIVE-SPEAKER QA`** (field `review_status` on every sentence and on the explanation). |
| Harness | `apps/api/app/evaluation/retrieval.py` | `evaluate_retrieval(gold_rows, searcher)`; `evaluate_retrieval_dataset(corpus_rows, gold_rows)` wires it to BM25. |

### Tokenisation

Lower-case, hidden characters removed, NFKC, Devanagari digits to ASCII, nukta dropped,
chandrabindu to anusvara (the same idea as `kadi.injection._matching_view`, copied rather than
imported because that file belongs to another stream), `2,50,000` to `250000`, `1.50` kept
whole, danda as a separator. English stop-words and question words only; **no Hindi/Marathi
stop-word list** (it would be unreviewed).

## Metric definitions

Gold row: `{"id", "query", "relevant": ["<source>#<page>", ...]}`; empty `relevant` = out-of-corpus,
the retriever must return nothing. Hits are de-duplicated by `<source>#<page>`.

- `hit_rate@k`: share of answerable queries with at least one relevant clause in the top k.
- `recall@k`: mean over answerable queries of (relevant found in top k / relevant).
- `precision`, `micro_recall`: micro-averaged over **all** queries; any hit returned for an
  out-of-corpus query is a false positive.
- `pcra`: correctly retrieved relevant clauses / total relevant clauses. It equals
  `micro_recall`; reported under both names.
- `mrr`: mean reciprocal rank of the first relevant clause (0 when none), over answerable queries.
- `abstention_rate`: share of out-of-corpus queries answered with an empty list.
- An undefined metric (zero denominator) is `None`, never 0.

## Data

`data/evaluation/retrieval_corpus_synthetic.jsonl` (27 passages) and
`retrieval_queries_synthetic.jsonl` (47 queries), both starting with a `_meta` record with
`"synthetic": true` (the loader refuses anything else).

Corpus sources, all clean in-repo English text: SchemeSetu criteria and cited-source summaries
(`thresholds.py`, 12 passages), BimaNyay clause library and letter text (`clause_auditor`,
`drafter`, `clinical_triggers`, `tracker`, 12 passages), DaaviSetu readiness texts
(`readiness.py`, 3 passages). `page` is the passage number inside its module, **not a PDF
page**. The real downloaded Marathi/Hindi PDFs have corrupted text layers and are **not** used.

Queries: 16 SchemeSetu, 16 BimaNyay, 6 DaaviSetu, 9 out-of-corpus (several deliberately share
words with the corpus: "hospitals", "family", "card"). Two answerable queries are
deliberate vocabulary-mismatch cases ("free treatment for elderly people").

## Measured (2026-11-21, 47 queries, synthetic, offline, defaults: score floor 1.0, coverage floor 1/3)

| Metric | Value |
|---|---|
| MRR (n=38 answerable) | **0.851** |
| hit_rate@1 / @3 / @5 | 0.789 / 0.921 / 0.921 |
| recall@3 | 0.807 |
| PCRA @3 (= micro recall) | 0.764 (42 of 55 relevant clauses) |
| precision @3 (micro) | 0.553 (42 tp, 34 fp) |
| abstention_rate (n=9 out-of-corpus) | **0.889** (8 of 9 returned nothing) |

The 4 recorded failures (all kept in the report, none hidden):

- `RET-010` "What could not be verified about the Maharashtra scheme order?" returned the
  sources-retrieved passage instead of the verification-gap passage (the shared words are
  generic).
- `RET-016` "free treatment for elderly people": **not found** (corpus says "senior citizens");
  an honest empty answer, counted as a miss.
- `RET-037` "Can a checklist label say the patient had failed treatment?": **not found**
  (query words mostly absent from the clause).
- `RET-044` "Documents needed for a PAN card application": answered with a MJPJAY passage
  because "documents" and "card" both occur in it. A lexical retriever cannot tell that
  "PAN card" is unrelated; this is the 1 out-of-corpus miss.

Precision is low at k=3 by construction: most queries have one or two relevant passages, and
the retriever returns up to three.

### Sensitivity to the coverage floor (same data)

| min_coverage | MRR | hit@3 | PCRA@3 | precision@3 | abstention |
|---|---|---|---|---|---|
| 0.0 | 0.860 | 0.947 | 0.836 | 0.390 | 0.556 |
| 0.2 | 0.864 | 0.947 | 0.836 | 0.422 | 0.667 |
| **0.33 (default)** | 0.851 | 0.921 | 0.764 | 0.553 | 0.889 |
| 0.5 | 0.763 | 0.816 | 0.673 | 0.698 | 1.000 |
| 0.6 | 0.671 | 0.711 | 0.564 | 0.838 | 1.000 |

The score floor (0.5 to 4.0) did not change any figure here (the coverage floor binds first).
Before the coverage floor existed, abstention was 0.444 (4 of 9), because a single shared
word such as "card" cleared any BM25 score floor. The default trades recall for abstention;
it was picked by looking at this table, which is why it is optimistic.

## What this does NOT show

- Nothing about Hindi or Marathi retrieval: there is no clean Devanagari corpus in the repo.
  Devanagari handling is covered only by unit tests of the tokeniser (nukta, chandrabindu,
  digits, danda) and chunker.
- Nothing about real documents (bills, rejection letters, scanned PDFs) or OCR noise.
- Nothing about an embedding/dense re-ranker: none exists (Kadi rule: dense similarity may only
  re-rank, never decide).
- `verify_citation` checks figures and scheme names, not meaning: a sentence with the right
  numbers and a wrong claim ("below 70" for "70 and above") passes. A pass is "no unsupported
  number or scheme name".
- The Hindi/Marathi explanation templates were not reviewed by a native speaker.

## Reproduce

```bash
python -m pytest apps/api/tests/test_evaluation_retrieval.py packages/kadi/tests/test_retrieval.py packages/schemesetu/tests
```

Until the integrator wires the runner (see
`docs/superpowers/handoff/wave2-b-retrieval.md`), call the harness directly:

```python
from app.evaluation.datasets import DATA_DIR, load_dataset
from app.evaluation.retrieval import evaluate_retrieval_dataset
_, corpus = load_dataset(DATA_DIR / "retrieval_corpus_synthetic.jsonl")
_, gold = load_dataset(DATA_DIR / "retrieval_queries_synthetic.jsonl")
report = evaluate_retrieval_dataset(corpus, gold)
```
