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
