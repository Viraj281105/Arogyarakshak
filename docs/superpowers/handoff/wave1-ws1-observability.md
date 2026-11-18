# Wave 1 handoff - WS1 Observability

Branch `ws1/observability` (from `wave1/integration` at a3fffaa). Design note:
`docs/superpowers/specs/2026-11-18-ws1-observability-design.md`. ADR: `ADR-023-self-hosted-telemetry.md`.
Operator doc: `docs/operations/observability.md`.

## What shipped

- **Metrics** (`apps/api/app/telemetry/metrics.py`, `llm_metrics.py`): private Prometheus registry, `GET /metrics`
  (hidden from OpenAPI, `METRICS_ENABLED`, default on in development / off in production). HTTP rate, errors and duration
  by route template; upload rejections (derived from the response status, no endpoint edits); pipeline stage timers around
  OCR, extraction, entity resolution, DB write and module checks in `case_ingestion._run_pipeline`; end-to-end case time fed
  from `LatencyTracker.record` (the `/metrics/latency/*` endpoints and their tests are unchanged); DB pool gauges (empty on
  SQLite); `record_llm_event` (duck-typed, WS2 interface).
- **Label safety:** routes must be in the OpenAPI path set else `<unmatched>`; methods/status/stage/outcome/reason from closed
  sets; LLM `model` must be a configured model (`GROQ_MODEL` / `GROQ_FALLBACK_MODEL`) else `other`; `kind` is a capped identifier.
  A PHI-looking and random fuzz test checks nothing leaks into any label.
- **Tracing** (`telemetry/tracing.py`): OTel SDK + OTLP/HTTP, lazy imports, `OTEL_ENABLED=false` default; FastAPI, httpx and
  SQLAlchemy instrumentation; `trace_id` added to JSON logs (null without an active span).
- **Logs:** Docker `fluentd` driver (async) -> collector `fluentforward` -> Loki OTLP. No docker.sock.
- **Stack:** `docker-compose.observability.yml` + `infrastructure/observability/**` (Prometheus v3.5.0, Alertmanager v0.28.1,
  Loki 3.5.0, Tempo 2.7.2, OTel Collector contrib 0.128.0, Grafana 12.0.2; loopback ports 9090, 9093, 3001, 4318, 24224; Loki/Tempo
  unpublished); recording rules, SLO burn-rate alerts, four generated dashboards (API RED, LLM, pipeline, SLOs), provisioned
  datasources, `scripts/observability_preflight.py`, Grafana entrypoint guard that refuses the dev password under production.
- **Wiring:** `main.py` (imports, `/metrics`, telemetry setup at the end of the file so the OpenAPI schema it reads is complete),
  `observability.py` (metrics call in the existing middleware `finally`, `trace_id` in JSON logs), `latency_metrics.py` (one call),
  `case_ingestion.py` (stage timers), `.importlinter` (`app.telemetry` added to the "below HTTP" contract, required by
  `test_architecture`).
- Requirements: prometheus-client 0.26.0, opentelemetry-sdk / exporter-otlp-proto-http 1.45.2, fastapi/httpx/sqlalchemy
  instrumentations 0.66b2 (all PyPI).

## Real test evidence

- `apps/api/tests/test_telemetry_metrics.py`, `test_telemetry_tracing.py`, `test_observability_stack_config.py`: 50 new tests (the extra skip is
  the `promtool` test: not installed). Written first; the first run failed with `ModuleNotFoundError: No module named 'app.telemetry'`.
- Full API suite `python -m pytest apps/api -q`: **552 passed, 2 skipped** (baseline 502 passed, 1 skipped, measured on this branch with the new deps on the path; the task's quoted baseline was 499). `python scripts/ci_guardrails.py`: exit 0. `lint-imports`: 5 contracts kept. `ruff check apps/api packages --select=E9,F63,F7,F82`: clean.
- Bug found only by running the API with `OTEL_ENABLED=true`: the FastAPI instrumentor keyword is `excluded_urls`, not `exclude_urls`;
  the TypeError was swallowed and logged as a warning. Fixed, and a test now asserts the app is really instrumented.
- Local API (SQLite via `DATABASE_URL=sqlite+aiosqlite:///...`, `SCHEMA_MANAGEMENT=create_all`, `LOG_FORMAT=json`,
  `OTEL_ENABLED=true`, no collector listening): `/health` ok; after one 404 and one case creation `/metrics` showed
  `arogya_http_requests_total{method="POST",route="/api/v1/kadi/cases",status="201"} 1.0`,
  `{route="<unmatched>",status="404"}` for the unknown case path (the case id never appeared), and the access log line carried
  `"trace_id": "ae1aec71ce61a73ee1a2e29698edc212"` beside `request_id`. `/metrics` is absent from `/openapi.json`. Server stopped, scratch DB removed.

## NOT verified (stated plainly)

The user's relayed message authorised pulling the pinned images and running the stack under project `arogya-obs`. The harness blocked
the `docker compose pull` as an unsanctioned network action (a relayed coordinator message is not direct user consent), so
**no image was pulled and no container was started** by this stream. Therefore all of these are unverified:

- `docker compose ... config -q` ran (it needs no daemon or network) and passed, but nothing was started;
- container health, Prometheus `up`/rules loaded, `promtool check rules/config`, `amtool check-config`;
- that the chosen image tags exist on Docker Hub (they were picked from release history and are unconfirmed; digests not recorded);
- Grafana provisioning of datasources/dashboards and panels returning data; Browser screenshots of dashboards;
- Loki ingesting a log line and finding it by LogQL; the collector's `transform` statements and `fluentforward` field handling (the
  record shape from the Docker driver is an assumption, likely needing adjustment on first run); Tempo receiving and returning a trace;
- the Tempo healthcheck (`wget` in the image is assumed) and the volume write permission under `user: 0:0`;
- Windows/Docker Desktop reaching `127.0.0.1:24224` from the daemon for the fluentd driver and `host.docker.internal` for host-run APIs.

To finish: run the commands in `docs/operations/observability.md` (use `-p arogya-obs`), then `promtool check rules`
via `docker run --rm --entrypoint promtool -v ...`, and fix whatever the first start reports. Static checks in
`test_observability_stack_config.py` cover structure, loopback binding, pinning, no socket, the production guard (executed with `sh`),
alert/dashboard metric names and generator drift.

## Cross-stream interface notes

- WS2: nothing to import. After both merge, register `app.telemetry.llm_metrics.record_llm_event` as the observer at API startup
  and add one test. Expected event fields: `model, kind, outcome, latency_s, prompt_tokens, completion_tokens, cache_hit, retries,
  circuit_state` (`closed|half_open|open`). The `model` label is honoured only when equal to `settings.groq_model` or
  `GROQ_FALLBACK_MODEL`; `kind` must match `^[a-z][a-z0-9_]{0,23}$` (max 12 distinct values) or becomes `other`.
- Shared files touched append-only: `apps/api/requirements.txt`, `.env.example`, `docs/configuration/environment-variables.md`
  (6 rows after `SAFETY_RULE_REQUIRED_APPROVALS`), `docs/development/setup.md`, `docs/development/troubleshooting.md`; plus
  `.importlinter` (one line).
- Env vars added: `METRICS_ENABLED`, `OTEL_ENABLED`, `OTEL_EXPORTER_OTLP_ENDPOINT`, `OTEL_SERVICE_NAME`,
  `OTEL_TRACES_SAMPLER_RATIO`, `GRAFANA_ADMIN_PASSWORD`. `app/config.py` was not edited (own class in `telemetry/settings.py`).
- For PROJECT_CONTEXT / CHANGELOG: new package `app.telemetry`, ADR-023, observability stack, unverified items above.

## Follow-ups

- First live run of the stack and tuning of the collector's log transform.
- Digest pinning once images are pulled.
- Optional: authentication for `/metrics` if it is ever exposed beyond loopback/compose.
