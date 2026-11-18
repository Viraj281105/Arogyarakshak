# Observability

Self-hosted metrics, logs and traces for the API (ADR-023). Nothing is sent outside this
machine, and nothing here records documents, patient identifiers or case ids.

## What you get

| Signal | Source | Where to look |
|---|---|---|
| Metrics | `GET /metrics` on the API (internal; not in the OpenAPI contract) | Prometheus `http://127.0.0.1:9090`, Grafana dashboards |
| Logs | API JSON logs on stdout, shipped by Docker's `fluentd` log driver to the OTel Collector, then Loki | Grafana, Explore, datasource Loki: `{service_name="arogyarakshak-api"}` |
| Traces | OpenTelemetry (FastAPI, httpx, SQLAlchemy) over OTLP/HTTP to the collector, then Tempo | Grafana, Explore, datasource Tempo; the log line's `trace_id` field is the trace id |
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

**API on the host instead of in Compose.** Put `host.docker.internal:8000` in
`infrastructure/observability/prometheus/targets/api-host.yml` (instructions in the file), run
`OTEL_ENABLED=true OTEL_EXPORTER_OTLP_ENDPOINT=http://127.0.0.1:4318 LOG_FORMAT=json uvicorn
app.main:app --port 8000`. Host-run logs are not shipped (the Docker log driver only covers
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

No label, log field or span attribute may contain document text, patient identifiers, file names,
case ids or free text from users. Metric routes are templates; the access log already follows
the same rule. Add a metric only with a closed or capped label set and extend the fuzz test in
`apps/api/tests/test_telemetry_metrics.py`.

## What has and has not been verified

See `docs/superpowers/handoff/wave1-ws1-observability.md` for the exact list of what was run
(unit and configuration tests, a local API serving `/metrics`) versus what was not (starting the
containers, pulling the images, `promtool`, the Grafana dashboards rendering with data).
