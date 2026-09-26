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

| `CLINICAL_GOVERNANCE_ADMIN_KEY` | No | `""` (disabled) | Operator secret (sent as `X-Governance-Admin-Key`) for seating safety-board members, recording verification attempts and seeding demo fixtures (ADR-011). **Empty disables those actions (503)** — it never means "open". Use a long random value. |
| `CLINICAL_DEMO_MODE` | No | `false` | Enables `POST /api/v1/kadi/clinical-demo/seed` and the `DEMO_VERIFIED` reviewer status. Logged as a warning at startup. **Never enable in a real deployment.** |
| `OCR_LOW_CONFIDENCE_THRESHOLD` | No | `0.5` | EasyOCR segments below this confidence become human transcription tasks instead of trusted text (ADR-011). |
| `SAFETY_RULE_REQUIRED_APPROVALS` | No | `1` | Independent safety-board approvals needed before a rule can be activated. The proposer's own approval never counts. |

> **Note on CORS:** when `CORS_ORIGINS` is a wildcard (the default), credentialed cross-origin
> requests are disabled automatically — a wildcard origin combined with credentials would let
> any site issue authenticated requests. Set an explicit comma-separated origin list to enable
> credentials.

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
