# ADR-021: Modular monolith, no service extraction yet; single-replica Kubernetes path

## Status
Accepted (2026-10-19). Extends ADR-013 (local Docker Compose demo stays the supported target).

## Context
The transformation brief asked for "a credible path to independently deployable services"
while avoiding a distributed monolith. Candidates evaluated against the actual code:

| Candidate | Independent scaling need? | Data ownership | Blocking constraint |
|---|---|---|---|
| OCR / extraction worker | Yes in principle (CPU/RAM heavy: EasyOCR + torch) | None — consumes a document | Needs the document bytes on another process → durable storage of patient documents, forbidden by ADR-003 (see ADR-019) |
| Domain modules as services (BillNyay, DawaCheck, …) | No — pure, fast, in-memory rules | Read Kadi case entities | Would turn in-process calls into network calls over shared case data: a distributed monolith |
| Clinical review / governance | No | Own tables, but shares case lifecycle and erasure | Erasure (ADR-010) must cascade atomically across it |
| Groq adapter | No — an outbound HTTP call | None | Already isolated behind `kadi.extraction`; a service adds a hop and nothing else |
| Notifications | Does not exist (mobile reminders are on-device) | — | Nothing to extract |

## Decision
1. **Keep one deployable API** (a modular monolith) with boundaries enforced in code
   (ADR-018), plus the web client. No microservice is extracted in this change.
2. **Extraction trigger** for the OCR worker, the only real candidate: all of (a) a
   document-retention model that permits short-lived encrypted storage (ADR-003 superseded),
   (b) progress moved out of process, (c) measured OCR load that one process cannot serve.
   Its contract would be the `kadi_document_jobs` state machine (ADR-019), already in place.
3. **Kubernetes path** (`infrastructure/kubernetes/`, kustomize): API and web Deployments,
   ClusterIP Services, hardened pods (non-root, read-only root FS, all capabilities dropped,
   RuntimeDefault seccomp, no service-account token), Pod Security "restricted" namespace,
   ingress-only NetworkPolicy, an example TLS Ingress overlay, a one-off migration Job.
   API is `replicas: 1` with `Recreate`. **No HPA** (no viable model with one replica) and
   **no PodDisruptionBudget** (with one replica it would block every node drain; a PDB is
   added when replicas > 1 becomes possible). No PostgreSQL manifests: use a managed or
   separately operated PostgreSQL. No Helm: one environment shape does not justify templating.
4. ADR-013 is unchanged: nothing is deployed to a cluster by this repository, and a public
   deployment still requires real authentication (ADR-008) first.

## Rationale
Every candidate service either violates ADR-003 or adds network hops across shared data
without a scaling need. The deployment artifacts describe the system that exists.

## Consequences
- One image to build, scan and roll out; failure domains are a single process plus Postgres.
- Vertical scaling only for the API until the extraction trigger is met.
- The manifests are validated by rendering (`kubectl kustomize`) and policy tests, **not** by a
  cluster deployment: none exists for this project.

## Operational cost
Low: two Deployments, a migration Job, no extra platform components.

## Risks
Resource requests/limits are unmeasured assumptions (documented in
`docs/operations/kubernetes.md`); OCR on large scans can exceed the 3 GiB limit.

## Alternatives rejected
Per-domain services, a broker-based worker tier, Helm charts, HPA — each for the reasons above.
