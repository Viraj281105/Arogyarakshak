# Observability

Self-hosted metrics, logs and traces for the API (ADR-023). Nothing is sent outside this
machine. Metric labels and log fields never contain documents, patient identifiers or case ids
(routes are templates). Traces come from standard instrumentation that would otherwise record raw
paths, SQL text and exception messages, so they are scrubbed twice; see "Privacy rules" for exactly
what is removed and what remains.

## What you get

| Signal | Source | Where to look |
|---|---|---|
| Metrics | `GET /metrics` on the API (internal; not in the OpenAPI contract) | Prometheus `http://127.0.0.1:9090`, Grafana dashboards |
| Logs | API JSON logs on stdout, shipped by Docker's `fluentd` log driver to the OTel Collector, then Loki | Grafana, Explore, datasource Loki: `{service_name="arogyarakshak-api"}` |
| Traces | OpenTelemetry (FastAPI, httpx, SQLAlchemy) over OTLP/HTTP to the collector, then Tempo; scrubbed in the API and again in the collector | Grafana, Explore, datasource Tempo; the log line's `trace_id` field is the trace id. `/health*` and `/metrics` are not traced; `/api/v1/kadi/metrics/latency/*` is |
| Alerts | Prometheus rules, delivered to Alertmanager (no outbound receiver) | `http://127.0.0.1:9093`, Grafana dashboard "SLOs" |

The older `/api/v1/kadi/metrics/latency` endpoints still work; the same measurement now also
feeds `arogya_case_processing_seconds`.

## Metrics

| Metric | Labels | Notes |
|---|---|---|
| `arogya_http_requests_total` | `method`, `route`, `status` | `route` is the template (`/api/v1/kadi/cases/{case_id}`) or `<unmatched>`; method outside the standard set is `OTHER`; status outside 100-599 is `other`. Scrapes of `/metrics` are not counted. |
| `arogya_http_request_duration_seconds` | `method`, `route` | histogram |
| `arogya_upload_rejections_total` | `reason`, `route` | `too_large` (413), `unsupported_type` (415), `empty` (400 on an upload route) |
| `arogya_pipeline_stage_duration_seconds` | `stage`, `outcome` | stages `ocr`, `extraction`, `entity_resolution`, `database_write`, `module_checks` |
| `arogya_case_processing_seconds` | `outcome` | end-to-end upload to terminal event; the 10 s bucket is the SLO boundary |
| `arogya_db_pool_size` / `_checked_out` / `_overflow` | none | only for pools that expose counters (not SQLite) |
| `arogya_llm_calls_total`, `_call_duration_seconds`, `_tokens_total`, `_retries_total`, `_cache_hits_total`, `_circuit_state` | `model` (configured models only, else `other`), `kind`, `outcome`, `direction` | fed by `record_llm_event` (`app/telemetry/llm_metrics.py`); the integrator registers it as the LLM observer once the resilient client lands. Until then these series stay empty. |

Standard process, GC and platform metrics are included.

## SLOs (targets proposed for a demo deployment; not measured results)

| SLO | Objective | Alerts |
|---|---|---|
| Availability | 99.5 % of requests not 5xx | `ApiErrorBudgetBurnFast` (14.4x, 1 h and 5 m, page), `ApiErrorBudgetBurnSlow` (6x, 6 h and 30 m, ticket) |
| Case latency | 95 % of documents processed within 10 s (`TARGET_LATENCY_SECONDS`) | `CaseLatencyBudgetBurnFast/Slow`, `CaseLatencyP95AboveTarget` |
| LLM success | 95 % of calls end `ok` or `fallback` | `LlmErrorBudgetBurnFast/Slow`, `LlmCircuitOpen` |

Also `ApiTargetDown` and `ObservabilityComponentDown`. Rules: `infrastructure/observability/prometheus/rules/`.

## Running the stack

Prerequisites: Docker with Compose v2 and access to Docker Hub for the pinned images.

```bash
# 1. Refuse unsafe production settings early (the Grafana container checks them too)
python scripts/observability_preflight.py

# 2. Validate the merged configuration (no containers started)
docker compose -f docker-compose.yml -f docker-compose.observability.yml config -q

# 3. Start the observability services (and the API, with tracing and the log driver)
docker compose -f docker-compose.yml -f docker-compose.observability.yml up -d

# Observability stack only, leaving the API to run on the host (uvicorn):
docker compose -f docker-compose.yml -f docker-compose.observability.yml up -d \
  prometheus alertmanager loki tempo otel-collector grafana
```

URLs (loopback only): Grafana `http://127.0.0.1:3001` (user `admin`, password
`GRAFANA_ADMIN_PASSWORD`; the dev default is `arogyarakshak-dev-only`), Prometheus
`http://127.0.0.1:9090`, Alertmanager `http://127.0.0.1:9093`. Loki and Tempo have no host
port; use Grafana. The collector's OTLP/HTTP (`4318`) and fluentd (`24224`) ports are published
on loopback for a host-run API and for the Docker daemon's log driver.

**API on the host instead of in Compose.** Nothing to edit: Prometheus's `api` job already lists
`host.docker.internal:8000` (resolved through the prometheus service's `extra_hosts`). Start the
observability services only, then run (`--no-access-log` because uvicorn's own access line prints
the raw path, unlike the API's template-only access log)
`OTEL_ENABLED=true OTEL_EXPORTER_OTLP_ENDPOINT=http://127.0.0.1:4318 LOG_FORMAT=json uvicorn
app.main:app --port 8000 --no-access-log`. Host-run logs are not shipped (the Docker log driver only covers
containers); pipe them through a container if needed, or read them from the terminal.

Production: `APP_ENV=production` requires a unique `GRAFANA_ADMIN_PASSWORD` (12+ characters),
turns `/metrics` off unless `METRICS_ENABLED=true`, and the stack should stay on a private network:
neither `/metrics` nor the Grafana/Prometheus ports are authenticated beyond Grafana's login.

Tear down: `docker compose -f docker-compose.yml -f docker-compose.observability.yml down` (add
`-v` to delete the telemetry volumes).

## Dashboards

Provisioned read-only into the "ArogyaRakshak" folder: **API - RED**, **LLM calls**,
**Case pipeline**, **SLOs**. They are generated from
`infrastructure/observability/grafana/build_dashboards.py` (edit it, re-run it, commit the JSON);
a test fails if the JSON and the generator disagree or a panel queries a metric the API does not export.

## Privacy rules

- **Metrics and logs:** no label or log field may contain document text, patient identifiers,
  file names, case ids or user free text. Metric routes are templates; the access log follows the
  same rule. Add a metric only with a closed or capped label set and extend the fuzz test in
  `apps/api/tests/test_telemetry_metrics.py`.
- **Traces:** the standard instrumentations record the raw request target (it contains the case
  id), the query string, SQL text, and full exception messages (a SQLAlchemy error includes the
  bound parameters). Two layers remove them:
  1. In the API, `app/telemetry/span_scrub.py` (an exporter wrapper) drops `http.target`,
     `http.url`, `url.full`, `url.path`, `url.query`, `db.statement`, `db.query.text`; redacts
     `CASE-<id>` tokens in remaining string values and the span name; keeps only `exception.type`
     on exception events (no `exception.message`, no `exception.stacktrace`); drops status
     descriptions.
  2. In the collector, `transform/scrub_spans` does the same.
  What remains on a span: method, route template (`http.route` and the span name), status code,
  peer address and port, user agent, host name, timings, DB system and database name, exception
  type. `apps/api/tests/test_telemetry_scrubbing.py` drives a real instrumented request with a
  case id, a query string and an exception containing a name, and asserts none appears in any
  exported span.
- Loki log lines are the API's own access/application log lines, which already follow the log rules.

## Operational notes

- **Two workflows, one job.** The Prometheus job `api` has two static targets: `api:8000` (the
  Compose container, label `workflow=compose`) and `host.docker.internal:8000` (an API started on
  the host, `workflow=host`). The one not running is a never-up target; dashboards and rules use no
  job or workflow filter, so both workflows show data. `ApiTargetDown` is
  `up{job="api"} == 0 and max_over_time(up{job="api"}[7d]) == 1`: it fires only for a target that
  was up within the last 7 days and has been down for 2 minutes, so the other workflow's target never
  pages. (After 7 days of continuous outage it stops firing.) The Prometheus UI's Targets page will
  still show the unused target as down; that is expected. Unit tests for this rule:
  `infrastructure/observability/prometheus/tests/alerts.test.yml`, run with
  `docker run --rm --entrypoint promtool -v "$PWD/infrastructure/observability/prometheus:/p:ro"
  prom/prometheus:v3.5.0 test rules /p/tests/alerts.test.yml`.
- **`METRICS_ENABLED` is forced `true`** for the `api` service by the override, even under
  `APP_ENV=production`: Prometheus must scrape it and running the override is the opt-in.
- **`/metrics` is unauthenticated**; network isolation (loopback port, compose network) is the only
  protection. Scrapes go through the API's rate limiter (a scrape every 15 s is far below the limit).
- **Logs can be lost.** The `fluentd` driver runs async (`fluentd-async`): lines are dropped if the
  collector is down or the driver buffer is full, and early API logs may be lost while the collector
  starts. `docker compose logs api` still has everything.
- **Loki `service_name`.** The collector sets `service.name=arogyarakshak-api` on log resources so
  `{service_name="arogyarakshak-api"}` works (Docker's driver sets none).
- **`arogya_case_processing_seconds` includes failed documents**, so the case-latency SLI counts a
  failed (usually fast) document as within the target.
- **Tempo is the only container run as root with an added capability** (`DAC_OVERRIDE`), needed to
  write its named volume under `cap_drop: ALL`. Acceptable for this loopback-only local demo; for
  production use a non-root user plus an init step that chowns the volume.
- If `OTEL_EXPORTER_OTLP_ENDPOINT` points outside this machine / the stack, the API only logs a
  warning; it does not refuse.

## What has and has not been verified

See `docs/superpowers/handoff/wave1-ws1-observability.md` for the exact list of what was run live
versus what was not.
