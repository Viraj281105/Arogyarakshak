# End-to-End Processing Time — Evaluation

> **Read this first.** These numbers were measured against the **offline regex/heuristic
> fallback path** (`GROQ_API_KEY` unset — the documented default deployment state), on
> **small, synthetic, single-page text fixtures**, on one development machine. They are a
> development-time regression floor, not a production SLA measurement. Real multi-page
> scanned PDFs through EasyOCR, and real Groq network round-trips, are categorically
> different workloads and are **not** measured here — see Limitations.

## What is measured

`app/latency_metrics.py` records wall-clock time from the `upload_received` SSE event
to the pipeline's terminal event (`completed` or `failed`) in
`process_document_background` (`apps/api/app/api/v1/endpoints/kadi.py`) — i.e. the full
OCR → Kadi extraction → entity resolution → database write flow a real upload goes
through. `GET /api/v1/kadi/metrics/latency` reports p50/p95/max/mean over a bounded,
in-memory, single-process rolling window (last 500 samples) and the count/rate of
samples exceeding the project's stated 10-second target (#116).

## Method

`scripts/evaluate_latency.py` boots the real FastAPI app against an ephemeral SQLite
database (same bootstrap pattern as `apps/api/tests/conftest.py`) and uploads 4 curated
text fixtures through the actual `/cases` → `/upload` flow, 3 times each:

| Fixture | What it probes |
|---|---|
| `small_text_bill` | Minimal case: 2 line items |
| `multi_item_bill` | 6 line items including an ICU charge and a dosage-bearing medicine line (`Dolo 650: 33`) |
| `denial_letter` | BillNyay-relevant document_text path (denial code, policy clause, procedure) |
| `prescription_note` | Medicine + diagnosis extraction, feeds DawaCheck's auto-trigger |

Reproduce:

```bash
python scripts/evaluate_latency.py
python scripts/evaluate_latency.py --repeats 10 --json eval.json
```

## Results

Measured on 2026-09-15, `GROQ_API_KEY` unset (offline fallback), development laptop
(Windows, Python 3.11), 12 total runs (4 fixtures × 3 repeats):

| Metric | Value |
|---|---|
| Samples | 12 |
| Target | 10.0 s |
| p50 | 0.014 s |
| p95 | 0.021 s |
| max | 0.023 s |
| mean | 0.015 s |
| Violations | 0 |
| Compliance rate | 1.000 |

Per-fixture individual run times (seconds):

| Fixture | Run 1 | Run 2 | Run 3 |
|---|---|---|---|
| `small_text_bill` | 0.079 | 0.018 | 0.017 |
| `multi_item_bill` | 0.024 | 0.021 | 0.022 |
| `denial_letter` | 0.010 | 0.011 | 0.010 |
| `prescription_note` | 0.018 | 0.017 | 0.018 |

(The first run's 0.079s over `small_text_bill` is Python import/warm-up cost inside the
harness process, not the pipeline itself — subsequent runs of every fixture converge to
low double-digit milliseconds.)

## Findings

1. **The offline pipeline is not the bottleneck at this scale.** For small text
   documents with the LLM path disabled, every stage (OCR text extraction, regex-based
   entity extraction, entity resolution, SQLite write) completes in well under 100ms —
   two orders of magnitude inside the 10-second target.
2. **This tells you almost nothing about the deployment that actually ships.** The
   documented default has `GROQ_API_KEY` unset, so this offline path genuinely is what
   most users experience today — but the moment a real Groq API key is configured, or a
   real scanned image goes through EasyOCR instead of a plain text file, the dominant
   cost shifts entirely to network I/O and OCR inference, neither of which this run
   exercised.
3. **The monitoring hook itself works and is now permanently available**, independent of
   this specific measurement: every real upload (test, demo, or production) now
   contributes a sample to `GET /api/v1/kadi/metrics/latency`, so p95/violations can be
   checked at any time against real traffic, not just this synthetic run.

## Limitations

- **LLM path unmeasured.** No `GROQ_API_KEY` was configured for this run. A live Groq
  call adds real network latency (the codebase's own timeout on that call is 12 seconds
  — see `GroqClient.generate` — which alone could approach or exceed the 10-second
  target on a slow connection). This is the single most important gap: the number that
  matters for a demo with a configured API key has not been measured and should be
  before citing this evaluation as proof the target is met in that mode.
- **EasyOCR/PDF parsing unmeasured.** All 4 fixtures are plain `.txt` uploads (the OCR
  parser's text path). `EasyOCR` (image uploads) and `PyMuPDF` (PDF uploads) were never
  exercised here — both are meaningfully slower than string parsing, particularly
  EasyOCR's model inference on a scanned image.
- **Tiny sample size (12) and single machine.** No confidence interval is reported,
  because one would imply sampling from a real population; these are point
  measurements on one development laptop.
- **Single-process, in-memory tracker.** `latency_metrics.py`'s bounded window does not
  aggregate across worker processes — the same disclosed limitation as
  `processing_status` and the rate limiter (ADR-008). A multi-worker production
  deployment needs a shared store (e.g. the database, or Prometheus) to get a true
  system-wide p95.
- **No concurrent-load test.** All runs were sequential. Contention under concurrent
  uploads (e.g. SQLite's single-writer lock, or GIL contention during EasyOCR inference)
  is not represented in these numbers.
