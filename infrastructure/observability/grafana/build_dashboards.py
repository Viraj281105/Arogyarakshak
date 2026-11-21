#!/usr/bin/env python3
"""Generates the provisioned Grafana dashboards (dashboards/*.json).

The JSON files are committed (Grafana reads them as-is); this script is the readable source.
Re-run it after editing:  python infrastructure/observability/grafana/build_dashboards.py
tests/test_observability_stack_config.py checks that every metric a panel queries exists.
"""

import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "dashboards"
PROM = {"type": "prometheus", "uid": "prometheus"}
LOKI = {"type": "loki", "uid": "loki"}


def target(expr, legend="", ds=PROM, ref="A"):
    return {"datasource": ds, "expr": expr, "legendFormat": legend, "refId": ref}


def panel(pid, title, kind, x, y, w, h, targets, unit=None, desc="", extra=None):
    p = {
        "id": pid,
        "type": kind,
        "title": title,
        "description": desc,
        "datasource": targets[0]["datasource"],
        "gridPos": {"x": x, "y": y, "w": w, "h": h},
        "targets": [dict(t, refId=chr(65 + i)) for i, t in enumerate(targets)],
        "fieldConfig": {"defaults": ({"unit": unit} if unit else {}), "overrides": []},
        "options": {},
    }
    if extra:
        for k, v in extra.items():
            if isinstance(v, dict) and k in p:
                p[k].update(v)
            else:
                p[k] = v
    return p


def dashboard(uid, title, desc, panels):
    return {
        "uid": uid,
        "title": title,
        "description": desc,
        "tags": ["arogyarakshak"],
        "timezone": "browser",
        "schemaVersion": 39,
        "version": 1,
        "editable": False,
        "refresh": "30s",
        "time": {"from": "now-1h", "to": "now"},
        "templating": {"list": []},
        "annotations": {"list": []},
        "panels": panels,
    }


def histq(q, metric, by="le", window="5m", select=""):
    return f"histogram_quantile({q}, sum by ({by}) (rate({metric}_bucket{select}[{window}])))"


api_red = dashboard(
    "arogya-api-red",
    "API - RED",
    "Rate, errors and duration of the API by route template. Route labels are templates, never concrete paths or ids.",
    [
        panel(1, "Request rate by route", "timeseries", 0, 0, 12, 8,
              [target("sum by (route) (rate(arogya_http_requests_total[5m]))", "{{route}}")], "reqps"),
        panel(2, "5xx ratio", "timeseries", 12, 0, 6, 8,
              [target('sum(rate(arogya_http_requests_total{status=~"5.."}[5m])) / sum(rate(arogya_http_requests_total[5m]))', "5xx")],
              "percentunit"),
        panel(3, "Status codes", "timeseries", 18, 0, 6, 8,
              [target("sum by (status) (rate(arogya_http_requests_total[5m]))", "{{status}}")], "reqps"),
        panel(4, "Latency p50 / p95 / p99", "timeseries", 0, 8, 12, 8,
              [target(histq(0.5, "arogya_http_request_duration_seconds", window="5m"), "p50"),
               target(histq(0.95, "arogya_http_request_duration_seconds", window="5m"), "p95"),
               target(histq(0.99, "arogya_http_request_duration_seconds", window="5m"), "p99")], "s"),
        panel(5, "p95 latency by route", "timeseries", 12, 8, 12, 8,
              [target(histq(0.95, "arogya_http_request_duration_seconds", by="le, route"), "{{route}}")], "s"),
        panel(6, "Upload rejections", "timeseries", 0, 16, 8, 8,
              [target("sum by (reason) (increase(arogya_upload_rejections_total[15m]))", "{{reason}}")],
              desc="Uploads answered with 413, 415 or an empty-document 400."),
        panel(7, "DB connection pool", "timeseries", 8, 16, 8, 8,
              [target("arogya_db_pool_checked_out", "checked out"), target("arogya_db_pool_size", "size")],
              desc="Empty on SQLite (no pool counters)."),
        panel(8, "API logs (Loki)", "logs", 16, 16, 8, 8,
              [target('{service_name="arogyarakshak-api"}', "", LOKI)],
              desc="JSON log lines; request_id and trace_id are structured metadata."),
    ],
)

llm = dashboard(
    "arogya-llm",
    "LLM calls",
    "Groq call outcomes, latency, tokens and circuit breaker state. No prompt or response text is ever recorded.",
    [
        panel(1, "Calls by outcome", "timeseries", 0, 0, 12, 8,
              [target("sum by (outcome) (rate(arogya_llm_calls_total[5m]))", "{{outcome}}")], "ops"),
        panel(2, "Error ratio", "timeseries", 12, 0, 6, 8,
              [target("arogya:llm_error_ratio:rate5m", "5m"), target("arogya:llm_error_ratio:rate1h", "1h")], "percentunit"),
        panel(3, "Circuit state", "stat", 18, 0, 6, 8,
              [target("max by (model) (arogya_llm_circuit_state)", "{{model}}")],
              desc="0 closed, 1 half-open, 2 open.",
              extra={"fieldConfig": {"defaults": {"mappings": [{"type": "value", "options": {
                  "0": {"text": "closed"}, "1": {"text": "half-open"}, "2": {"text": "OPEN"}}}]}}}),
        panel(4, "Latency p50 / p95", "timeseries", 0, 8, 12, 8,
              [target(histq(0.5, "arogya_llm_call_duration_seconds", by="le, kind"), "p50 {{kind}}"),
               target(histq(0.95, "arogya_llm_call_duration_seconds", by="le, kind"), "p95 {{kind}}")], "s"),
        panel(5, "Tokens per second", "timeseries", 12, 8, 12, 8,
              [target("sum by (direction) (rate(arogya_llm_tokens_total[5m]))", "{{direction}}")]),
        panel(6, "Retries", "timeseries", 0, 16, 12, 8,
              [target("sum by (kind) (rate(arogya_llm_retries_total[5m]))", "{{kind}}")]),
        panel(7, "Cache hits", "timeseries", 12, 16, 12, 8,
              [target("sum by (kind) (rate(arogya_llm_cache_hits_total[5m]))", "{{kind}}")]),
    ],
)

pipeline = dashboard(
    "arogya-pipeline",
    "Case pipeline",
    "Document processing: end-to-end time against the 10 s target and per-stage durations.",
    [
        panel(1, "End-to-end p50 / p95", "timeseries", 0, 0, 12, 8,
              [target(histq(0.5, "arogya_case_processing_seconds", window="15m"), "p50"),
               target(histq(0.95, "arogya_case_processing_seconds", window="15m"), "p95")], "s",
              extra={"fieldConfig": {"defaults": {"custom": {"thresholdsStyle": {"mode": "line"}},
                                                   "thresholds": {"mode": "absolute", "steps": [
                                                       {"color": "green", "value": None}, {"color": "red", "value": 10}]}}}}),
        panel(2, "Cases per outcome", "timeseries", 12, 0, 12, 8,
              [target("sum by (outcome) (increase(arogya_case_processing_seconds_count[15m]))", "{{outcome}}")]),
        panel(3, "Stage p95 duration", "timeseries", 0, 8, 12, 8,
              [target(histq(0.95, "arogya_pipeline_stage_duration_seconds", by="le, stage", window="15m"), "{{stage}}")], "s"),
        panel(4, "Stage runs", "timeseries", 12, 8, 12, 8,
              [target("sum by (stage, outcome) (increase(arogya_pipeline_stage_duration_seconds_count[15m]))", "{{stage}} {{outcome}}")]),
    ],
)

slo = dashboard(
    "arogya-slo",
    "SLOs",
    "Service level indicators and burn rates for availability (99.5 %), case latency (95 % within 10 s) and LLM success (95 %). Targets are proposals, not measured results.",
    [
        panel(1, "Availability SLI (1 h)", "stat", 0, 0, 6, 6,
              [target("1 - arogya:http_error_ratio:rate1h", "non-5xx")], "percentunit",
              desc="Target 99.5 %."),
        panel(2, "Cases within 10 s (1 h)", "stat", 6, 0, 6, 6,
              [target("1 - arogya:case_slow_ratio:rate1h", "within 10 s")], "percentunit", desc="Target 95 %."),
        panel(3, "LLM success (1 h)", "stat", 12, 0, 6, 6,
              [target("1 - arogya:llm_error_ratio:rate1h", "ok or fallback")], "percentunit", desc="Target 95 %."),
        panel(4, "Firing alerts", "stat", 18, 0, 6, 6,
              [target('count(ALERTS{alertstate="firing"}) or vector(0)', "firing")]),
        panel(5, "Availability burn rate", "timeseries", 0, 6, 8, 8,
              [target("arogya:http_error_ratio:rate1h / 0.005", "1h"), target("arogya:http_error_ratio:rate6h / 0.005", "6h")],
              desc="Multiples of the error budget; page at 14.4 (1 h), ticket at 6 (6 h)."),
        panel(6, "Case latency burn rate", "timeseries", 8, 6, 8, 8,
              [target("arogya:case_slow_ratio:rate1h / 0.05", "1h"), target("arogya:case_slow_ratio:rate6h / 0.05", "6h")]),
        panel(7, "LLM burn rate", "timeseries", 16, 6, 8, 8,
              [target("arogya:llm_error_ratio:rate1h / 0.05", "1h"), target("arogya:llm_error_ratio:rate6h / 0.05", "6h")]),
    ],
)

if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    for name, dash in {"api-red": api_red, "llm": llm, "pipeline": pipeline, "slo": slo}.items():
        (OUT / f"{name}.json").write_text(json.dumps(dash, indent=2) + "\n", encoding="utf-8")
        print("wrote", name)
