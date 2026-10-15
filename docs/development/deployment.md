# Deployment (local demo)

Supported target: one machine, Docker Compose, localhost only (ADR-013).

## 1. Start

```powershell
$env:CLINICAL_GOVERNANCE_ADMIN_KEY = "choose-a-long-random-demo-key"   # required by the override
docker compose -f docker-compose.yml -f docker-compose.demo.yml up -d --build
```

- Web: http://localhost:3000 — API: http://localhost:8000/health
- `docker-compose.demo.yml` removes `--reload`, turns demo mode on, runs the web production
  build, adds an API healthcheck, and makes the web service wait for a healthy API.
- Leave `GROQ_API_KEY` unset for the deterministic demo; set it to exercise real extraction.

## 2. Verify

```powershell
python scripts/demo_runtime_smoke.py --api http://127.0.0.1:8000 --admin-key $env:CLINICAL_GOVERNANCE_ADMIN_KEY
```

Expect every check to pass (Scenarios A–E over HTTP, then a reset).

## 3. Stop and clean up

```powershell
docker compose -f docker-compose.yml -f docker-compose.demo.yml down        # keep data volumes
docker compose -f docker-compose.yml -f docker-compose.demo.yml down -v     # also drop pgdata/hf_cache
```

Uploaded documents are never stored (ADR-003); `down -v` removes the case database too.

## 4. Before any non-local hosting (not supported today)

- Replace ADR-008 (no authentication) with real authentication.
- Terminate TLS in front of the API and set `TRUSTED_PROXY_COUNT` to the real proxy hops.
- `APP_ENV=production`, `CLINICAL_DEMO_MODE=false`, unique Postgres credentials, a real
  `DOCUMENT_SIGNING_SECRET`, and no host port mapping for Postgres.
- Review data-protection obligations for health data.
