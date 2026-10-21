# Service catalog

What actually runs. Decisions: ADR-013 (local demo target), ADR-019, ADR-021 (no service extraction).

## api — FastAPI backend (`apps/api`)

| | |
|---|---|
| Responsibility | Case lifecycle, document ingestion (OCR → extraction → resolution → persistence), the five domain modules, clinical review governance, generated documents |
| Contract | REST under `/api/v1`, OpenAPI in `docs/api/openapi.json` (contract-tested), SSE at `/api/v1/kadi/cases/{id}/stream` |
| Dependencies | PostgreSQL 16 (required); Groq API (optional — offline fallbacks when `GROQ_API_KEY` is empty); Hugging Face Hub only if `KADI_SEMANTIC_MATCHING=true` |
| Configuration | `app/config.py`; reference in `docs/configuration/environment-variables.md`; `APP_ENV=production` refuses development defaults |
| Data ownership | Every table in `app/models/` (one module per owning domain; single owner: the API). Schema via Alembic (ADR-020) |
| Health | `/health/live` (process up, no DB), `/health/ready` (DB reachable and schema at head → 200, else 503), `/health` (legacy; reports Groq configuration) |
| Deployment | One process, one replica (ADR-019). Image `apps/api/Dockerfile` (multi-stage, non-root uid 10001). Compose service `api`; Kubernetes `infrastructure/kubernetes/base/api.yaml` |
| Failure behaviour | DB down → readiness 503, liveness 200 (no restart loop). Groq down/absent → heuristic extraction and templated letters, `groq_configured:false`. Crash mid-processing → job `interrupted`, client told to re-upload. Unhandled error → 500 with `error_id`, no internals |
| Observability | One access-log line per request (route template, status, duration), `X-Request-ID` on every response, `LOG_FORMAT=json` for collectors, `/api/v1/kadi/metrics/latency` for pipeline latency |

## web — Next.js client (`apps/web`)

| | |
|---|---|
| Responsibility | Patient-facing UI (English/Hindi/Marathi) |
| Contract | Calls the API from the browser; `NEXT_PUBLIC_API_URL` baked in at build time |
| Data ownership | None server-side. Case access token held in browser memory (ADR-009) |
| Health | `GET /` |
| Deployment | Image `apps/web/Dockerfile` (`runtime` target; compose dev uses `build` target with `next dev`). Stateless |

## postgres — PostgreSQL 16 (`pgvector/pgvector:pg16` image; no vector features used)

Owned by the API. Local: compose service bound to `127.0.0.1:5432`. Kubernetes: not provided —
use a managed instance. Backup/restore: `docs/operations/runbook.md`.

## mobile — Expo client (`apps/mobile`)

Same API contract as web. Not a deployable server component.

## Evaluated and not extracted

OCR worker, per-domain services, Groq adapter, notifications — see ADR-021 for the reasons and
the conditions that would change the decision.
