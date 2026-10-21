# ADR-019: Document processing reliability without a message broker

## Status
Accepted (2026-10-19)

## Context
An upload is accepted with `202`, then OCR → extraction → entity resolution → persistence →
auto-triggers run in a FastAPI `BackgroundTask` in the same process. Progress is an in-memory
event list (`processing_status`) streamed over SSE.

Failure modes before this ADR:
- A crash or restart during processing lost the in-memory stream. Reconnecting clients got
  `idle — No document is being processed`, indistinguishable from "nothing was uploaded".
  Nothing persistent recorded that a document had been accepted.
- Running two API processes (workers or replicas) would split SSE streams from their uploads
  and multiply the per-process rate limit. This was documented only in code comments.

The obvious "durable queue" fix conflicts with ADR-003 (bring-your-own-document, zero
retention): a worker on another process can only retry a job if the document bytes are stored
somewhere durable — exactly what ADR-003 forbids.

## Options considered
1. **Broker + workers** (Redis/RabbitMQ/Kafka, separate worker service). Requires persisting
   document bytes in the broker or object storage → violates ADR-003. Adds two services.
2. **Postgres-backed job queue with stored payloads.** Same ADR-003 violation.
3. **Persist the job's *state* (not the document), reconcile on start-up.** The process that
   received the bytes is the only one that can process them; make its outcome — including
   death — visible and durable.

## Decision
Option 3.
- Table `kadi_document_jobs` (migration `0002_document_jobs`): `id`, `case_id` (FK, cascade),
  `sha256`, `state`, `pipeline_version`, `error_id`, timestamps. A database CHECK constraint
  limits `state` to `queued | processing | completed | duplicate | failed | interrupted`.
  No file name, text or bytes.
- The upload route commits a `queued` job **before** returning `202`. The pipeline marks it
  `processing`, then a terminal state mirroring its last progress event. Terminal states are
  final: a late write cannot overwrite one (`WHERE state IN ('queued','processing')`).
- A cancelled task (shutdown) leaves the job in flight on purpose. At start-up, before any
  upload is accepted, every in-flight job is marked `interrupted`.
- When the in-memory stream has no entry for a case, the SSE route reads the latest job: an
  `interrupted` or `failed` job is reported as `failed` with a plain "please upload it again"
  message (and `interrupted: true`), never as idle.
- Job bookkeeping never fails the pipeline (logged, swallowed).
- `PIPELINE_VERSION` records which ingestion pipeline handled a document (provenance).
- **The API must run as exactly one process.** Enforced in the Dockerfile CMD (no
  `--workers`), the Kubernetes Deployment (`replicas: 1`, `strategy: Recreate`, no HPA) and
  `tests/infrastructure/test_kubernetes_manifests.py`.

## Rationale
It fixes the silent failure (a lost document now produces an explicit, recoverable user
state) without storing documents and without new infrastructure.

## Consequences
- No automatic retry: recovery is "re-upload", stated to the user. This is the price of ADR-003.
- Horizontal scaling of the API is not possible until the progress stream and rate limiter
  move out of process (e.g. Postgres `LISTEN/NOTIFY` for progress, a shared rate-limit store)
  **and** start-up reconciliation becomes per-instance (lease/heartbeat column). Documented as
  the extraction trigger in ADR-021.
- Exactly-once processing is not claimed. Duplicate uploads are already idempotent via the
  `kadi_case_documents` digest guard; a duplicate records a `duplicate` job.

## Operational cost
One small table, one row per upload, erased with the case (`purge_case`, retention sweep).

## Risks
If someone runs two API processes anyway, start-up reconciliation in one would mark the
other's live jobs `interrupted`. The single-process rule is therefore written into every
deployment artifact and tested.

## Alternatives rejected
Options 1 and 2 (both require retaining patient documents).
