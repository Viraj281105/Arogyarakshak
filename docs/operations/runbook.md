# Operational runbook

For the local Docker Compose deployment (ADR-013); the same signals exist on Kubernetes
(`docs/operations/kubernetes.md`).

## Signals

| Signal | Where | Meaning |
|---|---|---|
| `GET /health/live` | API | Process is serving. Never touches the database. |
| `GET /health/ready` | API | `200 {"status":"ready"}` when the database answers **and** the schema is at the code's Alembic head; `503` otherwise, with `database` / `schema.ok` booleans. |
| `GET /health` | API | Legacy probe; also shows `groq_configured` (false = offline fallbacks in use). |
| `X-Request-ID` | every response | Quote it when reporting a problem; grep the logs for it. |
| `error_id` | 500 responses, failed processing events | Correlates with the server log line holding the exception. |
| `/api/v1/kadi/metrics/latency` | API | End-to-end document processing latency (in-process, resets on restart). |

Logs: `docker compose logs -f api`. Set `LOG_FORMAT=json` for a collector. Logs carry the
route template (never a case id in the path), status, duration and request id — never
document contents, file names or tokens.

## Common incidents

**Readiness 503, `database: false`.** PostgreSQL is down or unreachable. `docker compose ps
postgres`, `docker compose logs postgres`. The API stays live and recovers by itself when the
database returns; it does not restart-loop.

**Readiness 503, `schema.ok: false`.** With `SCHEMA_MANAGEMENT=none`, run
`docker compose run --rm api alembic upgrade head`. With `migrate`, the start-up upgrade
failed — the log line `Database schema step (migrate) failed` has the cause.

**API refuses to start: "Refusing to start under APP_ENV=production".** Each preceding log
line names one setting (signing secret, DB credentials, CORS, schema mode, demo mode). Fix the
variable; the message never prints the secret.

**A user says processing never finished.** If the API restarted mid-processing, the job is
`interrupted` and the client is told to re-upload (ADR-019); the document was never stored, so
it cannot be re-run server-side. Look for `Marked N in-flight document job(s) as interrupted`
at start-up. For a `failed` job, grep the log for its `error_id`.

**429 responses.** Per-IP fixed window (`RATE_LIMIT_PER_MINUTE`). Behind a proxy, check
`TRUSTED_PROXY_COUNT`, otherwise every user shares the proxy's bucket.

## Backup and restore

**Status: procedure written, NOT validated.** No restore has been performed against this
project's database (the Docker engine was unavailable when this was written). Treat it as a
draft until someone runs the restore drill below and records the result here.

Recovery objectives have not been set: they must come from whoever operates a real
deployment. For the local demo, all data is synthetic and reloadable (Load Scenario A–E), so
no backup is required.

What is in the database: case entities, redacted excerpts, generated appeal/claim PDFs,
clinical-review records, audit events. No original uploaded documents (ADR-003). Backups
therefore contain health information: encrypt them, restrict access, and apply the same
retention as the live data (`CASE_TTL_DAYS`) — a backup kept longer than the TTL defeats
case erasure (ADR-010).

```bash
# Backup (custom format, compressed)
docker compose exec -T postgres pg_dump -U arogyarakshak -d arogyarakshak -Fc > backup-$(date +%F).dump

# Restore drill into a SCRATCH database — never over the live one
docker compose exec -T postgres createdb -U arogyarakshak restore_check
docker compose exec -T postgres pg_restore -U arogyarakshak -d restore_check --no-owner < backup-YYYY-MM-DD.dump
docker compose exec -T postgres psql -U arogyarakshak -d restore_check \
  -c "SELECT version_num FROM alembic_version" \
  -c "SELECT count(*) FROM kadi_cases"
docker compose exec -T postgres dropdb -U arogyarakshak restore_check
```

A drill passes when the restored `alembic_version` equals the backup's, row counts match the
source at backup time, and an API pointed at the restored database reports `/health/ready`
200. Record date, sizes and timings here when it has been done.
