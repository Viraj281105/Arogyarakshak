# ADR-023: Self-hosted telemetry, no outbound

## Status
Accepted (2026-11-18). Builds on ADR-019 (single API process) and ADR-021 (deployment topology).

## Context
The API had a bounded in-memory latency tracker (`/metrics/latency/*`), an access log and request
ids, but no metrics a scraper can read, no traces, no way to ship logs, and no alerting. AGENTS.md
allows network traffic only to Groq, the local PostgreSQL container and the official package
registries, and the product handles health information (ADR-003, ADR-010): telemetry must not
become a new place where patient data or case identifiers accumulate or leave the machine.

## Decision
1. **Everything is self-hosted** in an opt-in Compose override (`docker-compose.observability.yml`):
   Prometheus, Alertmanager, Loki, Tempo, an OpenTelemetry Collector and Grafana. No SaaS
   exporter, no vendor agent, no Grafana/Loki analytics, no update checks. Alertmanager ships
   with no outbound receiver. All published ports bind to `127.0.0.1`; images are pinned by tag;
   the Docker socket is never mounted; Grafana has no anonymous access and its container refuses
   the development admin password under `APP_ENV=production`.
2. **Metrics:** `prometheus_client` with a private registry; `GET /metrics` outside the OpenAPI
   contract, enabled by default in development and off under production unless `METRICS_ENABLED`
   says otherwise. Route labels are route templates from the OpenAPI paths (or `<unmatched>`);
   all other labels are closed vocabularies or capped (`app/telemetry/metrics.py`,
   `llm_metrics.py`). A fuzz test asserts PHI-looking input never appears in any label.
3. **Tracing:** OpenTelemetry with OTLP/HTTP to the collector, `OTEL_ENABLED=false` by default and
   imported lazily, so a deployment that does not use it is unchanged. Only the standard
   instrumentations' attributes (method, route template, status, DB statement type) are recorded;
   this code adds no attributes. The trace id is added to JSON logs.
4. **Logs:** stdout stays the source of truth. Shipping uses Docker's built-in `fluentd` logging
   driver (async) to the collector's `fluentforward` receiver, then OTLP to Loki. Rejected:
   Promtail/agents with `docker_sd` (need the Docker socket or a host `/var/lib/docker` mount),
   the Loki Docker plugin (extra plugin install), OTLP log export from the app (experimental
   Python API, and it would make the app depend on the collector being up).
5. **SLOs** (proposals, not measurements): API availability 99.5 %; 95 % of documents processed
   within 10 s (the existing target of issue #116); 95 % of LLM calls `ok` or `fallback`.
   Multi-window burn-rate alerts (14.4x over 1 h and 5 m pages, 6x over 6 h and 30 m tickets).
6. **Single process stays** (ADR-019): the metrics are per process and need no multiprocess mode.
   The existing `LatencyTracker` is kept and now also feeds the Prometheus histogram.

## Consequences
- Case ids, document text, file names and user strings are not allowed in labels, log fields or
  span attributes; adding one requires revisiting this ADR.
- Dashboards and rules are tied to metric names; `tests/test_observability_stack_config.py`
  fails when a rule or panel references a metric the API does not export.
- Residual risks: the compose stack and its image tags were validated statically unless the
  handoff note says it was run; tag pins do not protect against a re-pushed tag (digests are not
  recorded); `/metrics` has no authentication, so it must stay on loopback or the compose
  network; Tempo runs as root inside its container (capabilities dropped) to write its volume.
- The OTel Collector image has no shell, so it has no container healthcheck; Prometheus scrapes
  its metrics and an alert fires when the target is down.
