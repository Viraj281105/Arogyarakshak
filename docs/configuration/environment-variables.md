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
| `CORS_ORIGINS` | No (production: **Yes**) | `http://localhost:3000` | Comma-separated web origins allowed to call the API with the sign-in cookie. Example: `https://arogyarakshak.in`. A wildcard `*` disables sign-in from browsers. Production refuses to start on a wildcard or when the variable is unset. |
| `MAX_UPLOAD_BYTES` | No | `10485760` (10 MB) | Maximum accepted document upload size. Larger uploads return `413`. |
| `SSE_TIMEOUT_SECONDS` | No | `120` | Maximum lifetime of a `/stream` connection before it closes with a `timeout` event. |
| `RATE_LIMIT_PER_MINUTE` | No | `120` | Requests allowed per client IP per 60-second window before `429 Too Many Requests`. See ADR-008 — this exists for unauthenticated (guest) traffic; account routes have their own stricter `AUTH_RATE_LIMIT_PER_MINUTE` bucket (ADR-026). |
| `TRUSTED_PROXY_COUNT` | No | `0` | Number of reverse-proxy hops in front of this API that are trusted to append the real client IP to `X-Forwarded-For` (e.g. `1` behind a single nginx/load balancer you control). At `0` (default), that header is **never** read — any client can forge it — and rate limiting uses the raw TCP peer IP, which means every request behind an unconfigured proxy shares one bucket. Only raise this when every hop between the trusted proxy and this API is genuinely unreachable except through it; see `app/rate_limit.py::resolve_client_ip`. |

| `SESSION_LIFETIME_HOURS` | No | `168` (7 days) | Absolute lifetime of an account session (ADR-026). Sessions are stored in the database (hash only) and survive restarts. |
| `SESSION_IDLE_TIMEOUT_MINUTES` | No | `120` | A session unused for this long stops working. Activity refreshes it (at most one write a minute). |
| `SESSION_COOKIE_SECURE` | Production: **must stay `true`** | `true` | Web session cookie is `__Host-arogya_session`, `httpOnly`, `Secure`, `SameSite=Strict`. `false` (plain `http://` local development only) drops `Secure` and the `__Host-` prefix (`arogya_session`); refused under `APP_ENV=production`. |
| `AUTH_TRUSTED_ORIGINS` | No | `""` (= explicit `CORS_ORIGINS`) | Comma-separated origins allowed to send cookie-authenticated state-changing requests and browser logins (CSRF check, ADR-026 §5). Outside production the API's own origin is also allowed; under `APP_ENV=production` it is not (it comes from the `Host` header), so list the web origin here or in `CORS_ORIGINS`. A cross-origin web client also needs an explicit `CORS_ORIGINS`, or the browser will not send the cookie. |
| `PASSWORD_SCRYPT_N` | No | `32768` (2^15) | stdlib `hashlib.scrypt` cost (power of two). With r=8 one hash needs ~32 MiB; 128·N·r must stay within 64 MiB. Raising it re-hashes each password at its next login. |
| `PASSWORD_SCRYPT_R` | No | `8` | scrypt block size. |
| `PASSWORD_SCRYPT_P` | No | `3` | scrypt parallelism (N=2^15, r=8, p=3 is an OWASP equivalent-strength setting). |
| `AUTH_RATE_LIMIT_PER_MINUTE` | No | `10` | Per-client-IP requests per minute to register, login, verification and password-reset routes (a separate, stricter bucket in the same in-memory limiter). `429` with `Retry-After`. |
| `LOGIN_FREE_FAILURES` | No | `5` | Wrong passwords per (account, client IP) before each further attempt from that pair must wait an increasing delay (ADR-026 §7). Wrong current passwords on password change and account deletion count too. Attempts inside the delay get the same generic `401`. Other IPs are unaffected, so this is not a lockout. |
| `LOGIN_FAILURE_WINDOW_MINUTES` | No | `15` | Failures of a pair expire after this long without a new failure. |
| `LOGIN_MAX_DELAY_SECONDS` | No | `900` | Cap of the doubling delay (1 s, 2 s, 4 s, …). |
| `ACCOUNT_VERIFICATION_TOKEN_TTL_HOURS` | No | `24` | Email-verification token lifetime (single use, hash stored). |
| `PASSWORD_RESET_TOKEN_TTL_MINUTES` | No | `30` | Password-reset token lifetime (single use, hash stored). |
| `MAIL_TRANSPORT` | No | `disabled` | `disabled` sends nothing: verification and reset requests create the token and log that nothing was delivered (never the address or token). `gmail_api` sends through one Gmail mailbox over HTTPS (ADR-030, setup in [email-gmail.md](email-gmail.md)). |
| `GMAIL_SENDER` | With `gmail_api` | `""` | Address of the dedicated sender mailbox. |
| `GMAIL_CLIENT_ID` | With `gmail_api` | `""` | OAuth 2.0 client id. |
| `GMAIL_CLIENT_SECRET` | With `gmail_api` | `""` | OAuth 2.0 client secret. Secret: never commit it. |
| `GMAIL_REFRESH_TOKEN` | With `gmail_api` | `""` | Refresh token with the `gmail.send` scope. Secret: never commit it. |
| `WEB_APP_BASE_URL` | With `gmail_api` | `""` | Web app address used in account links. Must be `https://` under `APP_ENV=production`. |
| `DOCUMENT_SIGNING_SECRET` | Production: **Yes** | `dev-insecure-signing-secret-change-in-production` | HMAC key for appeal-PDF integrity signatures (#66). Proves a PDF is byte-for-byte what this server generated; **not** a licensed digital signature certificate. Override with a long random value in any real deployment. |
| `CLINICAL_GOVERNANCE_ADMIN_KEY` | No | `""` (disabled) | Operator secret (sent as `X-Governance-Admin-Key`) for seating safety-board members, recording verification attempts and seeding demo fixtures (ADR-011). **Empty disables those actions (503)** — it never means "open". Use a long random value. |
| `CLINICAL_DEMO_MODE` | No | `false` | Enables the demo kit: `POST /api/v1/kadi/clinical-demo/seed`, `/reset`, `/scenarios/{A-E}`, the `DEMO_VERIFIED` reviewer status, the Scenario C OCR replay and the clients' DEMO MODE banner. Logged as a warning at startup. **Never enable in a real deployment** — refused with `APP_ENV=production`. |
| `APP_ENV` | No | `development` | Deployment profile. `production` marks a real deployment: the API **refuses to start** while any development default remains — `CLINICAL_DEMO_MODE=true`, the default or a short (< 32 chars) `DOCUMENT_SIGNING_SECRET`, the default `arogyarakshak:arogyarakshak` database credentials, a wildcard `CORS_ORIGINS`, `SCHEMA_MANAGEMENT=create_all`, or `SESSION_COOKIE_SECURE=false` (`Settings.production_config_errors`). The interactive `/docs` and `/redoc` pages are also turned off. |
| `SCHEMA_MANAGEMENT` | No | `migrate` | How the API treats the database schema at start-up (ADR-020). `migrate`: upgrade to the latest Alembic revision (a database made by the old `create_all` start-up is stamped at the baseline first). `none`: change nothing; run `alembic upgrade head` as a release step — `/health/ready` reports 503 while the database is behind. `create_all`: legacy, throwaway local databases only; refused in production. |
| `LOG_FORMAT` | No | `text` | `text` for humans, `json` for one JSON object per line (timestamp, level, logger, message, service, environment, request_id). |
| `LOG_LEVEL` | No | `INFO` | Root log level. |
| `DEMO_DOCUMENTS_DIR` | No | *(auto)* | Where the demo scenario loaders read the synthetic documents. Empty = the repository's `demo/documents` (local runs) or `/app/demo/documents` (the API image copies them there). Inert outside demo mode. |
| `OCR_LOW_CONFIDENCE_THRESHOLD` | No | `0.5` | EasyOCR segments below this confidence become human transcription tasks instead of trusted text (ADR-011). |
| `OCR_LANGUAGES` | No | `en` | Comma-separated EasyOCR language codes (`hi`, `mr`, `en`; unknown codes are rejected, and a bad value is reported even for a clean-only PDF). Default `en`. With `en` only, a PDF page whose text layer is judged corrupted (legacy-font Devanagari) is **skipped and reported** (`partial`), never read with the English model; set `hi,mr,en` to OCR it. Readers are cached per language set; weights are never downloaded while serving (`scripts/fetch_ocr_models.py` at image build time; `EASYOCR_MODULE_PATH`). See `docs/evaluation/devanagari-ocr.md`. |
| `OCR_MAX_PAGES` | No | `3` | Corrupted PDF pages OCR'd per document (hard ceiling 10); the rest are reported as skipped. |
| `OCR_DOCUMENT_BUDGET_SECONDS` | No | `120` | Wall-clock OCR budget per document, checked between pages; remaining pages are reported as skipped. |
| `OCR_QUEUE_TIMEOUT_SECONDS` | No | `30` | How long a request waits for the single process-wide OCR slot before the pages are reported `ocr_busy` (images: a "busy" error). |
| `OCR_PDF_MAX_PIXELS` | No | `10000000` | Pixel budget for one rasterised PDF page (also capped at 8000 px per side). A page referencing an embedded image above 40 MP is not rendered. |
| `SAFETY_RULE_REQUIRED_APPROVALS` | No | `1` | Independent safety-board approvals needed before a rule can be activated. The proposer's own approval never counts. |
| `METRICS_ENABLED` | No | *(unset: on in development, off under `APP_ENV=production`)* | Serves Prometheus metrics at `GET /metrics` (not in the OpenAPI contract; internal only: the API's host port is bound to `127.0.0.1` and Prometheus scrapes it over the compose network). Labels are route templates, never raw paths or case ids. When off, `/metrics` is `404`. WS1, ADR-023. |
| `OTEL_ENABLED` | No | `false` | Turns on OpenTelemetry tracing (FastAPI, httpx, SQLAlchemy). Off: nothing from the OpenTelemetry SDK is imported. `docker-compose.observability.yml` sets it to `true` for the `api` service. |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | No | `http://127.0.0.1:4318` | OTLP/HTTP base URL of the collector (`/v1/traces` is appended). Keep it on this machine or the compose stack (`otel-collector`); a warning is logged for any other host. |
| `OTEL_SERVICE_NAME` | No | `arogyarakshak-api` | `service.name` resource attribute on spans. |
| `OTEL_TRACES_SAMPLER_RATIO` | No | `1.0` | Head sampling ratio between 0 and 1 (parent-based). |
| `GRAFANA_ADMIN_PASSWORD` | Production: **Yes** (when the stack is used) | `arogyarakshak-dev-only` | Grafana admin password for the observability stack. The Grafana container refuses to start under `APP_ENV=production` while this is the development default or shorter than 12 characters; `python scripts/observability_preflight.py` performs the same check first. Anonymous access is always off. |

> **Note on CORS:** the web client signs in with a cookie, so its origin must be listed. When
> `CORS_ORIGINS` is a wildcard, credentialed cross-origin requests are disabled automatically (a
> wildcard origin combined with credentials would let any site issue authenticated requests) and
> nobody can sign in from a browser. Use `localhost` for both the web and the API locally:
> `127.0.0.1` and `localhost` are different sites to the cookie.

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

---

## 4. LLM reliability settings (WS2, ADR-024)

Read by `packages/kadi/kadi/llm/config.py` (`LlmConfig.from_env`) from the **process
environment** — Kadi cannot use the API's pydantic Settings, so these are not read from a
`.env` file by the API itself. Docker Compose forwards them to the `api` service; for a local
`uvicorn` run, export them or start it with `uvicorn app.main:app --env-file ../../.env`.
Every default keeps the pre-WS2 behaviour except retries and the circuit breaker.

| Variable | Default | Description |
|---|---|---|
| `GROQ_FALLBACK_MODEL` | `""` (none) | Second Groq model tried when the primary (`GROQ_MODEL`) fails, including when its circuit is open. Deprecated models (ADR-004) and a value equal to `GROQ_MODEL` are ignored with a warning. |
| `LLM_TIMEOUT_SECONDS` | unset | Per-attempt timeout ceiling. **Unset:** each call site's own timeout applies (BillNyay 12 s, Kadi extraction 10 s). **Set:** the effective timeout is `min(call-site timeout, LLM_TIMEOUT_SECONDS)` — it can lower a call site's timeout, never raise it. A call without its own timeout uses this value, else 12 s. |
| `LLM_TOTAL_DEADLINE_SECONDS` | `20` | Overall wall-clock limit for one LLM call across **all** attempts, backoff sleeps and the fallback model. Each attempt's timeout is capped to the time left, no backoff sleep crosses it, and the fallback model is skipped when no time is left; the caller then uses its offline fallback. Must be > 0 (0, negative or non-numeric values are refused with a warning and the default is used); maximum 600. |
| `LLM_MAX_ATTEMPTS` | `3` | Attempts per model for timeouts, connection errors, 429, 408 and 5xx. `1` = no retries (the old behaviour). |
| `LLM_BACKOFF_BASE_SECONDS` / `LLM_BACKOFF_MAX_SECONDS` | `0.5` / `8` | Equal-jitter exponential backoff: retry *n* waits between half and all of `min(max, base·2ⁿ)`; a 429's `Retry-After` (seconds or HTTP-date) raises the wait, clamped by `LLM_RETRY_AFTER_MAX_SECONDS`. |
| `LLM_RETRY_AFTER_MAX_SECONDS` | `30` | Upper bound on a honoured `Retry-After`; the overall deadline still applies on top. |
| `LLM_BREAKER_FAILURE_THRESHOLD` | `5` | Consecutive availability failures that open a model's circuit (calls then fail fast to the offline fallback). |
| `LLM_BREAKER_RECOVERY_SECONDS` | `30` | How long a circuit stays open before one probe call is allowed. |
| `LLM_CASE_TOKEN_BUDGET` | `0` (unlimited) | Token budget **per BillNyay pipeline run** (one appeal or grievance draft), not a lifetime budget per case: drafting again for the same case starts a new budget, and Kadi extraction is not budgeted. A call that does not fit uses the canned offline fallback instead of calling Groq. |
| `LLM_CACHE_ENABLED` | `false` | In-memory response cache. Only deterministic requests with no detected identifiers are cached; see ADR-024 for the residual risk before enabling it. |
| `LLM_CACHE_MAX_ENTRIES` / `LLM_CACHE_TTL_SECONDS` | `256` / `300` | Cache bound and time-to-live (TTL capped at 3600 s). Case erasure empties the cache. |
| `LLM_SHADOW_ENABLED` | `false` | Opt-in shadow runs of a candidate model next to production (agreement counters only, no content). |
| `LLM_SHADOW_MODEL` | `""` | Candidate model for shadow runs; shadowing stays off while empty. Deprecated models are refused. |
| `LLM_SHADOW_SAMPLE_RATE` / `LLM_SHADOW_MAX_RUNS` | `0.1` / `50` | Fraction of eligible calls shadowed, and the per-process cap on shadow calls (cost bound). |
