# Environment Variables & Configuration Reference

All runtime parameters in **ArogyaRakshak** are controlled via environment variables loaded by Pydantic Settings (`apps/api/app/config.py`) and Docker Compose.

---

## 1. Environment Variable Reference Table

| Variable | Required | Default Value | Description & Example |
|---|---|---|---|
| `GROQ_API_KEY` | **Yes** (for LLM calls) | `""` (empty) | API key for Groq inference cloud. Example: `gsk_abc123...` |
| `GROQ_MODEL` | No | `openai/gpt-oss-120b` | Model identifier on Groq. Never use deprecated `llama3-70b` or `llama-3.3-70b-versatile`. |
| `DATABASE_URL` | **Yes** | `postgresql://arogyarakshak:arogyarakshak@postgres:5432/arogyarakshak` | Full SQLAlchemy async database connection URI. When running API locally outside Docker, use `localhost:5432`. |
| `POSTGRES_USER` | No | `arogyarakshak` | Username for PostgreSQL container. |
| `POSTGRES_PASSWORD` | No | `arogyarakshak` | Password for PostgreSQL container. Change in production! |
| `POSTGRES_DB` | No | `arogyarakshak` | Database name for PostgreSQL. |
| `CORS_ORIGINS` | No | `*` | Comma-separated list of allowed CORS origins. Example: `http://localhost:3000,https://arogyarakshak.in` |
| `MAX_UPLOAD_BYTES` | No | `10485760` (10 MB) | Maximum accepted document upload size. Larger uploads return `413`. |
| `SSE_TIMEOUT_SECONDS` | No | `120` | Maximum lifetime of a `/stream` connection before it closes with a `timeout` event. |
| `RATE_LIMIT_PER_MINUTE` | No | `120` | Requests allowed per client IP per 60-second window before `429 Too Many Requests`. See ADR-008 — this exists because the API has no authentication. |
| `TRUSTED_PROXY_COUNT` | No | `0` | Number of reverse-proxy hops in front of this API that are trusted to append the real client IP to `X-Forwarded-For` (e.g. `1` behind a single nginx/load balancer you control). At `0` (default), that header is **never** read — any client can forge it — and rate limiting uses the raw TCP peer IP, which means every request behind an unconfigured proxy shares one bucket. Only raise this when every hop between the trusted proxy and this API is genuinely unreachable except through it; see `app/rate_limit.py::resolve_client_ip`. |

| `DOCUMENT_SIGNING_SECRET` | Production: **Yes** | `dev-insecure-signing-secret-change-in-production` | HMAC key for appeal-PDF integrity signatures (#66). Proves a PDF is byte-for-byte what this server generated; **not** a licensed digital signature certificate. Override with a long random value in any real deployment. |
| `CLINICAL_GOVERNANCE_ADMIN_KEY` | No | `""` (disabled) | Operator secret (sent as `X-Governance-Admin-Key`) for seating safety-board members, recording verification attempts and seeding demo fixtures (ADR-011). **Empty disables those actions (503)** — it never means "open". Use a long random value. |
| `CLINICAL_DEMO_MODE` | No | `false` | Enables the demo kit: `POST /api/v1/kadi/clinical-demo/seed`, `/reset`, `/scenarios/{A-E}`, the `DEMO_VERIFIED` reviewer status, the Scenario C OCR replay and the clients' DEMO MODE banner. Logged as a warning at startup. **Never enable in a real deployment** — refused with `APP_ENV=production`. |
| `APP_ENV` | No | `development` | Deployment profile. `production` marks a real deployment: the API **refuses to start** while any development default remains — `CLINICAL_DEMO_MODE=true`, the default or a short (< 32 chars) `DOCUMENT_SIGNING_SECRET`, the default `arogyarakshak:arogyarakshak` database credentials, a wildcard `CORS_ORIGINS`, or `SCHEMA_MANAGEMENT=create_all` (`Settings.production_config_errors`). The interactive `/docs` and `/redoc` pages are also turned off. |
| `SCHEMA_MANAGEMENT` | No | `migrate` | How the API treats the database schema at start-up (ADR-020). `migrate`: upgrade to the latest Alembic revision (a database made by the old `create_all` start-up is stamped at the baseline first). `none`: change nothing; run `alembic upgrade head` as a release step — `/health/ready` reports 503 while the database is behind. `create_all`: legacy, throwaway local databases only; refused in production. |
| `LOG_FORMAT` | No | `text` | `text` for humans, `json` for one JSON object per line (timestamp, level, logger, message, service, environment, request_id). |
| `LOG_LEVEL` | No | `INFO` | Root log level. |
| `DEMO_DOCUMENTS_DIR` | No | *(auto)* | Where the demo scenario loaders read the synthetic documents. Empty = the repository's `demo/documents` (local runs) or `/app/demo/documents` (the API image copies them there). Inert outside demo mode. |
| `OCR_LOW_CONFIDENCE_THRESHOLD` | No | `0.5` | EasyOCR segments below this confidence become human transcription tasks instead of trusted text (ADR-011). |
| `SAFETY_RULE_REQUIRED_APPROVALS` | No | `1` | Independent safety-board approvals needed before a rule can be activated. The proposer's own approval never counts. |
| `METRICS_ENABLED` | No | *(unset: on in development, off under `APP_ENV=production`)* | Serves Prometheus metrics at `GET /metrics` (not in the OpenAPI contract; internal only: the API's host port is bound to `127.0.0.1` and Prometheus scrapes it over the compose network). Labels are route templates, never raw paths or case ids. When off, `/metrics` is `404`. WS1, ADR-023. |
| `OTEL_ENABLED` | No | `false` | Turns on OpenTelemetry tracing (FastAPI, httpx, SQLAlchemy). Off: nothing from the OpenTelemetry SDK is imported. `docker-compose.observability.yml` sets it to `true` for the `api` service. |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | No | `http://127.0.0.1:4318` | OTLP/HTTP base URL of the collector (`/v1/traces` is appended). Keep it on this machine or the compose stack (`otel-collector`); a warning is logged for any other host. |
| `OTEL_SERVICE_NAME` | No | `arogyarakshak-api` | `service.name` resource attribute on spans. |
| `OTEL_TRACES_SAMPLER_RATIO` | No | `1.0` | Head sampling ratio between 0 and 1 (parent-based). |
| `GRAFANA_ADMIN_PASSWORD` | Production: **Yes** (when the stack is used) | `arogyarakshak-dev-only` | Grafana admin password for the observability stack. The Grafana container refuses to start under `APP_ENV=production` while this is the development default or shorter than 12 characters; `python scripts/observability_preflight.py` performs the same check first. Anonymous access is always off. |

> **Note on CORS:** when `CORS_ORIGINS` is a wildcard (the default), credentialed cross-origin
> requests are disabled automatically — a wildcard origin combined with credentials would let
> any site issue authenticated requests. Set an explicit comma-separated origin list to enable
> credentials.

> Every response carries an `X-Request-ID` header (a well-formed incoming one is reused) that also
> appears on every log line for that request.

> Unhandled `500` responses return only `{"detail": ..., "error_id": ...}`. The exception text
> is written to the API logs against that `error_id` and is never returned to the client.

---

## 2. Configuration Setup

### For Local Non-Docker Development
Copy `.env.example` to `.env` in the repository root:
```env
GROQ_API_KEY=gsk_your_key
GROQ_MODEL=openai/gpt-oss-120b
DATABASE_URL=postgresql://arogyarakshak:arogyarakshak@localhost:5432/arogyarakshak
CORS_ORIGINS=http://localhost:3000
```

### For Docker Compose
Docker Compose automatically loads variables from `.env` in the root directory:
```yaml
environment:
  DATABASE_URL: ${DATABASE_URL:-postgresql://arogyarakshak:arogyarakshak@postgres:5432/arogyarakshak}
  GROQ_MODEL: ${GROQ_MODEL:-openai/gpt-oss-120b}
  GROQ_API_KEY: ${GROQ_API_KEY:-}
```

---

## 3. Security Guidelines for Credentials

1. **Never commit `.env`**: `.env` is explicitly ignored in `.gitignore`.
2. **Never log secrets**: API keys and database passwords must never appear in `logger.info()` or exception stack traces.
3. **Automated Secret Scanning**: Commits containing API keys matching patterns like `gsk_*` are automatically rejected by pre-commit hooks and GitHub secret scanning.
