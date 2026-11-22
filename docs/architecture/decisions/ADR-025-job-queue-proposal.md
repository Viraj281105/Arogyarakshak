# ADR-025: Document job queue (proposal)

## Status
**PROPOSED** (2026-11-21). Nothing in this ADR is implemented and nothing is decided.
If accepted, it supersedes **only** the "no message broker" part of ADR-019 (the
`kadi_document_jobs` state machine, start-up reconciliation and "re-upload on failure" stay in
force unless a later ADR changes them). ADR-003 (bring-your-own-document, zero retention) and
ADR-021's extraction trigger are **not** touched by this proposal; one option below would
require amending ADR-003 and says so explicitly.

## Context
ADR-019 chose to keep document processing in a FastAPI `BackgroundTask` in the one API process
and to make failure visible (persisted job state, `interrupted` after a restart) rather than to
add a broker, because a broker that can retry a job must hold the document bytes durably, which
ADR-003 forbids.

What that leaves open, none of it measured yet:

1. **No back-pressure.** Every accepted upload starts its pipeline immediately. OCR (EasyOCR on
   CPU) is the heaviest step; N simultaneous uploads run N pipelines on the same thread pool and
   memory budget. The only bound is the per-IP rate limit (120 requests per minute), which says
   nothing about CPU or memory. The k6 scripts in `tests/load/` exist to measure this, but have
   not been run.
2. **No horizontal scaling.** The SSE progress map and the rate limiter are per-process and
   start-up reconciliation assumes it is the only process (ADR-019, ADR-021 extraction trigger).
3. **No automatic retry.** A crashed or interrupted job is re-uploaded by the user.

The trigger ADR-021 set for extracting a worker is: (a) a retention model that permits
short-lived encrypted storage, (b) progress out of process, (c) *measured* load that one process
cannot serve. (c) is not met: there is no measurement.

## Options

| | A. Status quo | B. In-process bounded queue | C. Postgres queue (`FOR UPDATE SKIP LOCKED`) | D. Redis (list/stream) |
|---|---|---|---|---|
| New infrastructure | none | none | none (existing Postgres) | a Redis service |
| Back-pressure | none | **yes** (bounded concurrency, `503`/`429` when full) | yes | yes |
| Survives a restart | job *state* only | job state only | job + payload, **if** payload is stored | job + payload, if payload is stored and Redis persists |
| Retry without re-upload | no | no | yes, **needs the bytes** | yes, **needs the bytes** |
| Multi-replica API | no | no | possible with leases; progress and rate limiter still need work | possible; Redis could also hold progress (pub/sub) and the rate limit |
| ADR-003 (zero retention) | kept | kept | **violated** unless payloads are short-lived, encrypted and purged (needs an ADR-003 amendment) | same, plus data sits outside Postgres' erasure path (ADR-010) |
| Failure modes added | none | a full queue rejects uploads | queue table bloat and vacuum, lock contention, poison jobs | one more thing to run, secure, back up and monitor; persistence settings decide whether it is "retention" |

### A. Status quo
Cheapest, and correct until a measurement says otherwise.

### B. In-process bounded queue
Replace "start the pipeline now" with an `asyncio` queue and a fixed number of workers in the
same process (a semaphore with a small bounded wait list is the minimum form). Concurrency is
capped (config value, default today's behaviour), excess uploads get an explicit
`503 Retry-After`, and queue depth becomes a metric (`arogya_*`, ADR-023). The document bytes
still live only in this process's memory, so ADR-003 and the single-process rule are unchanged.
It does not retry and does not scale out; it makes overload a controlled, observable condition
instead of a slow one.

### C. Postgres-backed queue with `SKIP LOCKED`
`kadi_document_jobs` gains `claimed_by`, `lease_expires_at`, `attempts`; workers claim with
`SELECT ... FOR UPDATE SKIP LOCKED`. This is the natural extension of ADR-019's table and the
only option with no new service. But another worker can run a job only if it can read the
document, so a payload must be stored: a new table holding an **encrypted, TTL-bound** blob,
deleted on terminal state and by the retention sweep (ADR-010). That is a retention model
ADR-003 currently forbids, so this option cannot be accepted without amending ADR-003 (and the
privacy notice, the erasure test and the BYOD claims). Without payloads it degenerates to
option B with extra rows.

### D. Redis
Same payload problem as C, plus an extra service. Its one genuine advantage is that it also
moves the two other single-process pieces (progress stream, rate limiter) out of the API
process, which is the rest of the horizontal-scaling story. If persistence (RDB/AOF) is off and
payloads have a TTL it is closer to ADR-003's spirit, but then it is not durable and the
retry argument disappears.

## Proposed decision (conditional)
1. **Do not adopt C or D now.** The trigger in ADR-021 is unmet and no load has been measured.
2. **Run the k6 scripts and record the result first** (`docs/operations/load-and-chaos.md`).
   Adopt B only if overload (CPU or memory exhaustion, SLO breach: 95 % of documents within
   10 s) is observed with a single process; B is small, reversible and keeps every existing
   invariant.
3. Revisit C or D only when the product needs multiple replicas or automatic retry, **and** a
   separate ADR amends ADR-003 to permit short-lived encrypted payloads. That change belongs to
   the privacy owner, not to the platform team.

## Effect on the single-process rule
- **B:** none. Still exactly one API process; `replicas: 1`, `Recreate`, no HPA stay.
- **C/D:** the rule could be relaxed only together with (a) progress moved out of process,
  (b) a shared rate-limit store, (c) per-instance start-up reconciliation using leases, and
  (d) updating the Kubernetes policy tests that pin `replicas: 1`
  (`tests/infrastructure/test_kubernetes_manifests.py`). Not in scope here.

## Migration path (if B, then optionally C)
1. Add the queue behind a setting whose default reproduces today's behaviour (unbounded);
   job state transitions (`queued` to terminal) are already what the queue needs.
2. Expose queue depth, wait time and rejection count as metrics; add an alert.
3. Turn the cap on for a demo deployment, re-run `tests/load/upload.js` and `sse_stream.js`.
4. Only then, and only with an accepted ADR-003 amendment, add lease columns and a payload
   table (Alembic revision, ADR-020) for C.

## Rollback
- **B:** set the concurrency cap back to unbounded (one setting); no schema change, nothing to
  migrate. In-flight jobs are covered by the existing start-up `interrupted` marking.
- **C:** stop workers; drop the payload table (Alembic downgrade); jobs fall back to ADR-019
  behaviour. Any stored payload must be purged and the purge verified, because it is patient
  data. This is why C is the riskier option.

## Consequences if adopted as proposed
Overload becomes an explicit, measured, user-visible state (`503 Retry-After`) rather than
silent slowdown, at the cost of one more setting and a rejected-upload path to test (add it to
`tests/chaos/`). Retry and scale-out remain deliberately out of reach until ADR-003 is revisited.

## Open questions
- What concurrency can one process sustain? Unknown: no k6 run exists.
- Does the product accept rejecting an upload under load, or must it queue unboundedly?
- Is a payload-retention model acceptable to the privacy owner at all? If not, C and D are
  closed permanently and this ADR should be rejected in favour of B alone.
