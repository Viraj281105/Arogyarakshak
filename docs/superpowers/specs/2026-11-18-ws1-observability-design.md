# WS1 Observability - design note

**Date:** 2026-11-18. **Branch:** `ws1/observability`. **Plan:** `docs/superpowers/plans/2026-11-18-wave1.md` (WS1).

## Decisions

| Area | Decision | Why |
|---|---|---|
| Metrics library | `prometheus_client` with a **dedicated `CollectorRegistry`** (`apps/api/app/telemetry/metrics.py`) | Official client, no agent. A private registry keeps tests isolated and means only the metrics we declare are exposed. Single process (ADR-019), so no multiprocess mode. |
| Where HTTP metrics are recorded | Inside the existing `RequestContextMiddleware` `finally` block, via one call `record_http_request(...)` | It already computes the route template and status; no second middleware, minimal `main.py` diff. `/metrics` scrapes are not counted. |
| Label policy | Route **templates** only (`route_template`, finite set from OpenAPI plus `<unmatched>`), methods clamped to a fixed set, status as a 3-digit code, every other label from a closed vocabulary or a `BoundedLabel` (hard cap on distinct values, overflow -> `other`) | Case ids, document text and user strings can never become label values. Fuzz-tested. |
| Upload rejections | Derived in the middleware from the response (413/415 and 400 on `.../upload`) rather than editing endpoints | Keeps endpoint files untouched; label is the route template + reason. |
| Pipeline stages | `stage_timer("ocr" / "extraction" / "database_write")` around the three steps in `case_ingestion._run_pipeline`; end-to-end time fed from `LatencyTracker.record` | Reuses the existing measurement; `/metrics/latency/*` unchanged. |
| LLM metrics | `record_llm_event(event)` duck-typed (`llm_metrics.py`), per the WS1/WS2 interface | WS1 imports no WS2 code. |
| Exposure | `GET /metrics`, `include_in_schema=False`, gated by `METRICS_ENABLED` (unset: on in development, off in production) | Internal-only; the API port is bound to 127.0.0.1 and Prometheus reaches it on the compose network. |
| Tracing | OpenTelemetry SDK + OTLP/**HTTP** exporter (no grpcio wheel), FastAPI/httpx/SQLAlchemy instrumentation, all imported lazily inside `setup_tracing()`; `OTEL_ENABLED=false` default | Import-safe and a no-op when off. Missing optional instrumentation packages are skipped with a log line. The trace id is added to JSON log records beside `request_id`. |
| Log shipping | JSON logs on stdout, Docker's built-in **`fluentd` logging driver** (async) to the OTel Collector `fluentforward` receiver on `127.0.0.1:24224`, then `otlphttp` to Loki's native OTLP endpoint | No `docker.sock`, no host `/var/lib/docker` mount, no plugin install. Rejected: promtool/Promtail docker_sd (needs the socket), Loki Docker plugin (extra plugin install), app-side OTLP logs (experimental API; stdout stays the source of truth). |
| Stack images | prom/prometheus v3.5.0, grafana/grafana 12.0.2, grafana/loki 3.5.0, grafana/tempo 2.7.2, otel/opentelemetry-collector-contrib 0.128.0, prom/alertmanager v0.28.1; pinned by tag, digests not recorded | Tags chosen from release history; confirmed only by the pull in the verification run (see handoff). |
| Network | Every published port on `127.0.0.1`; no `docker.sock`; Grafana anonymous auth off, sign-up off | Plan constraint. |
| Grafana password | `GRAFANA_ADMIN_PASSWORD`, documented dev default; the Grafana container **refuses to start** when `APP_ENV=production` and the dev default is still set (entrypoint guard); `scripts/observability_preflight.py` performs the same check before `compose up` | A compose file cannot make a default conditional on another variable, so the guard lives in the container entrypoint and is tested. |
| Alertmanager | A single receiver with no outbound integration | No outbound network; the operator adds a receiver. |

## SLO definitions (targets are proposals for a demo deployment, not measured values)

1. **Availability:** 99.5 % of API requests are not 5xx over 30 days. Burn-rate alerts: 14.4x over 1 h and 5 m (page), 6x over 6 h and 30 m (ticket).
2. **Case processing latency:** 95 % of documents finish within 10 s (the existing `TARGET_LATENCY_SECONDS`, issue #116). Burn-rate alerts on the share of cases over 10 s, plus a p95 > 10 s alert.
3. **LLM success:** 95 % of LLM calls end `ok` or `fallback`. Burn-rate alert plus a circuit-open alert (`arogya_llm_circuit_state == 2`).

## Not verified here (unless the handoff says otherwise)

Whatever the handoff note lists as not run live. The SLO numbers above are targets, not observations.
