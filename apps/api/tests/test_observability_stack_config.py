"""WS1: static validation of the observability stack files (nothing is started here).

Parses docker-compose.observability.yml and the Prometheus / Alertmanager / Loki / Tempo /
Collector / Grafana configuration and checks the constraints the design promises: loopback-only
ports, pinned images, no Docker socket, Grafana without anonymous access, the production
password guard, rules that only reference metrics the API really exports, and dashboards that
match their generator.
"""

import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[3]
COMPOSE = ROOT / "docker-compose.observability.yml"
OBS = ROOT / "infrastructure" / "observability"
EXPECTED_SERVICES = {"prometheus", "alertmanager", "loki", "tempo", "otel-collector", "grafana"}


def load(path):
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def compose():
    return load(COMPOSE)


# --- reusable checks (also run against deliberately bad input below) --------------------


def port_errors(compose):
    errors = []
    for name, svc in compose.get("services", {}).items():
        for port in svc.get("ports", []) or []:
            text = port if isinstance(port, str) else f"{port.get('host_ip', '')}:{port.get('published')}"
            if not str(text).startswith("127.0.0.1:"):
                errors.append(f"{name}: port {text} is not bound to 127.0.0.1")
    return errors


def image_errors(compose):
    errors = []
    for name, svc in compose.get("services", {}).items():
        image = svc.get("image")
        if image is None:
            continue
        tag = image.rsplit(":", 1)[1] if ":" in image.rsplit("/", 1)[-1] else ""
        if not tag or tag == "latest":
            errors.append(f"{name}: image {image} is not pinned by tag")
    return errors


def socket_errors(compose):
    errors = []
    for name, svc in compose.get("services", {}).items():
        for volume in svc.get("volumes", []) or []:
            source = volume if isinstance(volume, str) else volume.get("source", "")
            if "docker.sock" in str(source) or str(source).startswith(("/var/run", "/run/docker")):
                errors.append(f"{name}: mounts {source}")
        if svc.get("privileged"):
            errors.append(f"{name}: privileged")
    return errors


# --- compose file -------------------------------------------------------------------------


def test_stack_declares_the_expected_services(compose):
    assert EXPECTED_SERVICES <= set(compose["services"])


def test_every_published_port_is_loopback_only(compose):
    assert port_errors(compose) == []


def test_every_image_is_pinned_by_tag(compose):
    assert image_errors(compose) == []


def test_docker_socket_is_never_mounted(compose):
    assert socket_errors(compose) == []
    assert "docker.sock" not in COMPOSE.read_text(encoding="utf-8").replace("docker.sock`", "").split("Rules this file keeps")[1].split("services:")[1]


def test_checks_catch_bad_compose():
    bad = {"services": {
        "a": {"image": "x/y", "ports": ["9090:9090"], "volumes": ["/var/run/docker.sock:/var/run/docker.sock"]},
        "b": {"image": "x/y:latest", "ports": ["0.0.0.0:80:80"], "privileged": True},
    }}
    assert len(port_errors(bad)) == 2
    assert len(image_errors(bad)) == 2
    assert len(socket_errors(bad)) == 2


def test_stateful_services_use_named_volumes_and_limits(compose):
    for name in EXPECTED_SERVICES:
        svc = compose["services"][name]
        assert svc["deploy"]["resources"]["limits"]["memory"], name
        assert svc["security_opt"] == ["no-new-privileges:true"], name
        assert svc["cap_drop"] == ["ALL"], name
    for volume in ("prometheus-data", "loki-data", "tempo-data", "grafana-data", "alertmanager-data"):
        assert volume in compose["volumes"]


def test_healthchecks_exist_except_the_shell_less_collector(compose):
    for name in EXPECTED_SERVICES - {"otel-collector"}:
        assert "healthcheck" in compose["services"][name], name
    assert "healthcheck" not in compose["services"]["otel-collector"]  # the image has no shell/wget


def test_grafana_has_no_anonymous_access_or_signup(compose):
    env = compose["services"]["grafana"]["environment"]
    assert env["GF_AUTH_ANONYMOUS_ENABLED"] == "false"
    assert env["GF_USERS_ALLOW_SIGN_UP"] == "false"
    assert env["GF_ANALYTICS_REPORTING_ENABLED"] == "false"
    assert "GRAFANA_ADMIN_PASSWORD" in env["GF_SECURITY_ADMIN_PASSWORD"]


def test_api_override_ships_logs_through_fluentd_not_the_socket(compose):
    api = compose["services"]["api"]
    assert api["logging"]["driver"] == "fluentd"
    assert api["logging"]["options"]["fluentd-address"].startswith("127.0.0.1:")
    assert api["logging"]["options"]["fluentd-async"] == "true"
    assert api["environment"]["METRICS_ENABLED"] == "true"


def test_override_merges_with_the_base_file_when_docker_cli_is_present():
    if not shutil.which("docker"):
        pytest.skip("docker CLI not installed")
    result = subprocess.run(
        ["docker", "compose", "-f", "docker-compose.yml", "-f", "docker-compose.observability.yml", "config", "-q"],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr


# --- production password guard --------------------------------------------------------------


def _guard_script(compose):
    return compose["services"]["grafana"]["entrypoint"][2].replace("$$", "$")


@pytest.mark.skipif(not shutil.which("sh"), reason="no POSIX shell")
@pytest.mark.parametrize(
    "env,refused",
    [
        ({"APP_ENV": "production", "GF_SECURITY_ADMIN_PASSWORD": "arogyarakshak-dev-only"}, True),
        ({"APP_ENV": "production", "GF_SECURITY_ADMIN_PASSWORD": "short"}, True),
        ({"APP_ENV": "production", "GF_SECURITY_ADMIN_PASSWORD": "a-unique-long-secret"}, False),
        ({"APP_ENV": "development", "GF_SECURITY_ADMIN_PASSWORD": "arogyarakshak-dev-only"}, False),
    ],
)
def test_grafana_entrypoint_refuses_dev_password_in_production(compose, env, refused):
    script = _guard_script(compose).replace("exec /run.sh", "echo started")
    result = subprocess.run(["sh", "-c", script], env={**os.environ, **env}, capture_output=True, text=True)
    assert (result.returncode != 0) == refused, result.stderr
    if refused:
        assert "Refusing to start Grafana" in result.stderr
        assert env["GF_SECURITY_ADMIN_PASSWORD"] not in result.stderr


def _preflight():
    spec = importlib.util.spec_from_file_location("observability_preflight", ROOT / "scripts" / "observability_preflight.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["observability_preflight"] = module
    spec.loader.exec_module(module)
    return module


def test_preflight_refuses_dev_password_only_in_production():
    pre = _preflight()
    assert pre.check({"APP_ENV": "production"})
    assert pre.check({"APP_ENV": "production", "GRAFANA_ADMIN_PASSWORD": "arogyarakshak-dev-only"})
    assert pre.check({"APP_ENV": "production", "GRAFANA_ADMIN_PASSWORD": "short"})
    assert pre.check({"APP_ENV": "production", "GRAFANA_ADMIN_PASSWORD": "a-unique-long-secret"}) == []
    assert pre.check({"APP_ENV": "development"}) == []
    assert pre.check({}) == []


def test_dev_default_is_the_same_everywhere(compose):
    from app.telemetry.settings import DEV_GRAFANA_PASSWORD

    assert _preflight().DEV_GRAFANA_PASSWORD == DEV_GRAFANA_PASSWORD
    assert DEV_GRAFANA_PASSWORD in COMPOSE.read_text(encoding="utf-8")


# --- Prometheus / Alertmanager / others -------------------------------------------------------


def exported_names():
    """Sample names the API's registry can export: its # TYPE lines plus the pool gauges, which
    only render when an engine with pool counters is registered (so they are listed explicitly
    to keep this independent of test order)."""
    from app.telemetry import metrics as m

    names = set(m.DB_POOL_METRICS)
    for line in m.render().decode().splitlines():
        if line.startswith("# TYPE "):
            _, _, name, kind = line.split(" ", 3)
            names.add(name)
            if kind.strip() == "histogram":
                names.update({name + "_bucket", name + "_count", name + "_sum"})
            if kind.strip() == "counter":
                names.add(name if name.endswith("_total") else name + "_total")
    return names


def recorded_names():
    names = set()
    for rules in (OBS / "prometheus" / "rules").glob("*.rules.yml"):
        for group in load(rules)["groups"]:
            names.update(r["record"] for r in group["rules"] if "record" in r)
    return names


def referenced(expr):
    return set(re.findall(r"\barogya[_:][A-Za-z0-9_:]*", expr))


def test_prometheus_config_scrapes_both_api_workflows_under_one_job_and_loads_rules():
    cfg = load(OBS / "prometheus" / "prometheus.yml")
    jobs = {j["job_name"]: j for j in cfg["scrape_configs"]}
    assert jobs["api"]["metrics_path"] == "/metrics"
    targets = [t for sc in jobs["api"]["static_configs"] for t in sc["targets"]]
    # in-compose API and an API started on the host (works without editing any file)
    assert set(targets) == {"api:8000", "host.docker.internal:8000"}
    assert "file_sd_configs" not in jobs["api"]
    assert "api-host" not in jobs, "dashboards and rules assume a single `api` job"
    assert {"prometheus", "alertmanager", "loki", "tempo", "otel-collector"} <= set(jobs)
    assert cfg["alerting"]["alertmanagers"][0]["static_configs"][0]["targets"] == ["alertmanager:9093"]
    assert list((OBS / "prometheus" / "rules").glob("*.rules.yml"))
    prom = load(COMPOSE)["services"]["prometheus"]
    assert "host.docker.internal:host-gateway" in prom["extra_hosts"]


def test_tempo_runs_as_root_with_dac_override_so_its_volume_is_writable():
    tempo = load(COMPOSE)["services"]["tempo"]
    assert tempo["user"] == "0:0"  # dropping this made Tempo crash-loop: mkdir /var/tempo/wal/blocks denied
    assert tempo["cap_add"] == ["DAC_OVERRIDE"]


def test_alert_rules_are_well_formed_and_reference_real_metrics():
    known = exported_names() | recorded_names()
    seen = []
    for path in (OBS / "prometheus" / "rules").glob("*.rules.yml"):
        for group in load(path)["groups"]:
            for rule in group["rules"]:
                expr = rule["expr"]
                assert expr.count("(") == expr.count(")"), expr
                missing = referenced(expr) - known
                assert not missing, f"{rule.get('alert') or rule.get('record')}: unknown metric(s) {missing}"
                if "alert" in rule:
                    seen.append(rule["alert"])
                    assert rule["labels"]["severity"] in {"page", "ticket"}
                    assert rule["annotations"]["summary"] and rule["annotations"]["description"]
                    assert re.fullmatch(r"\d+[smh]", rule["for"])
    for required in ("ApiErrorBudgetBurnFast", "ApiErrorBudgetBurnSlow", "CaseLatencyP95AboveTarget",
                     "LlmErrorBudgetBurnFast", "LlmCircuitOpen", "ApiTargetDown"):
        assert required in seen


def test_burn_rate_thresholds_equal_burn_times_budget():
    budgets = {"http_error": 0.005, "case_slow": 0.05, "llm_error": 0.05}
    rules = {r["alert"]: r["expr"] for g in load(OBS / "prometheus/rules/alerts.rules.yml")["groups"] for r in g["rules"] if "alert" in r}
    expectations = {
        "ApiErrorBudgetBurnFast": ("http_error", 14.4), "ApiErrorBudgetBurnSlow": ("http_error", 6),
        "CaseLatencyBudgetBurnFast": ("case_slow", 14.4), "CaseLatencyBudgetBurnSlow": ("case_slow", 6),
        "LlmErrorBudgetBurnFast": ("llm_error", 14.4), "LlmErrorBudgetBurnSlow": ("llm_error", 6),
    }
    for alert, (kind, burn) in expectations.items():
        thresholds = {float(x) for x in re.findall(r">\s*([0-9.]+)", rules[alert])}
        assert len(thresholds) == 1 and next(iter(thresholds)) == pytest.approx(burn * budgets[kind]), alert


def test_promtool_checks_rules_when_available():
    promtool = shutil.which("promtool")
    if not promtool:
        pytest.skip("promtool not installed")
    result = subprocess.run([promtool, "check", "rules", *map(str, (OBS / "prometheus" / "rules").glob("*.rules.yml"))],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr


def test_alertmanager_config_has_route_and_matching_receiver_without_outbound_integrations():
    cfg = load(OBS / "alertmanager" / "alertmanager.yml")
    names = {r["name"] for r in cfg["receivers"]}
    assert cfg["route"]["receiver"] in names
    for receiver in cfg["receivers"]:
        assert set(receiver) == {"name"}, "an outbound integration needs an ADR-023 revisit"


def test_loki_tempo_collector_configs_parse_and_wire_together():
    loki = load(OBS / "loki" / "loki.yml")
    assert loki["common"]["storage"]["filesystem"]
    tempo = load(OBS / "tempo" / "tempo.yml")
    assert tempo["storage"]["trace"]["backend"] == "local"
    otel = load(OBS / "otel-collector" / "config.yml")
    pipelines = otel["service"]["pipelines"]
    assert pipelines["traces"]["exporters"] == ["otlp/tempo"]
    assert pipelines["logs"]["receivers"] == ["fluentforward"]
    assert pipelines["logs"]["exporters"] == ["otlphttp/loki"]
    for name in ("memory_limiter", "batch"):
        assert name in otel["processors"]
    for pipeline in pipelines.values():
        for part in pipeline["receivers"] + pipeline["exporters"] + pipeline["processors"]:
            assert any(part in otel.get(section, {}) for section in ("receivers", "exporters", "processors")), part
    assert "docker" not in json.dumps(otel).lower().replace("docker `fluentd`", "")


def test_grafana_datasources_and_dashboard_provider():
    ds = load(OBS / "grafana/provisioning/datasources/datasources.yml")["datasources"]
    assert {d["uid"] for d in ds} == {"prometheus", "loki", "tempo"}
    assert sum(1 for d in ds if d.get("isDefault")) == 1
    provider = load(OBS / "grafana/provisioning/dashboards/dashboards.yml")["providers"][0]
    assert provider["options"]["path"] == "/var/lib/grafana/dashboards"
    assert provider["allowUiUpdates"] is False


def dashboards():
    return {p.name: json.loads(p.read_text(encoding="utf-8")) for p in (OBS / "grafana" / "dashboards").glob("*.json")}


def test_four_dashboards_with_unique_uids_and_known_datasources_and_metrics():
    dash = dashboards()
    assert set(dash) == {"api-red.json", "llm.json", "pipeline.json", "slo.json"}
    assert len({d["uid"] for d in dash.values()}) == 4
    known = exported_names() | recorded_names()
    for name, d in dash.items():
        ids = [p["id"] for p in d["panels"]]
        assert len(ids) == len(set(ids)), name
        for p in d["panels"]:
            assert p["datasource"]["uid"] in {"prometheus", "loki"}
            for t in p["targets"]:
                if t["datasource"]["uid"] == "prometheus":
                    missing = referenced(t["expr"]) - known
                    assert not missing, f"{name}/{p['title']}: {missing}"
                    assert t["expr"].count("(") == t["expr"].count(")")


def test_committed_dashboards_match_their_generator():
    spec = importlib.util.spec_from_file_location("build_dashboards", OBS / "grafana" / "build_dashboards.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    built = {"api-red.json": module.api_red, "llm.json": module.llm, "pipeline.json": module.pipeline, "slo.json": module.slo}
    assert built == dashboards()


def test_new_environment_variables_are_documented():
    env_example = (ROOT / ".env.example").read_text(encoding="utf-8")
    docs = (ROOT / "docs" / "configuration" / "environment-variables.md").read_text(encoding="utf-8")
    for var in ("METRICS_ENABLED", "OTEL_ENABLED", "OTEL_EXPORTER_OTLP_ENDPOINT", "OTEL_SERVICE_NAME",
                "OTEL_TRACES_SAMPLER_RATIO", "GRAFANA_ADMIN_PASSWORD"):
        assert var in env_example, var
        assert var in docs, var


def test_exported_names_do_not_depend_on_a_registered_engine(monkeypatch):
    from app.telemetry import metrics as m

    monkeypatch.setattr(m, "_db_engine", None)
    names = exported_names()
    assert {"arogya_db_pool_size", "arogya_db_pool_checked_out", "arogya_db_pool_overflow"} <= names


def test_grafana_makes_no_outbound_calls_and_has_no_gravatar(compose):
    env = compose["services"]["grafana"]["environment"]
    expected = {
        "GF_ANALYTICS_REPORTING_ENABLED": "false",
        "GF_ANALYTICS_CHECK_FOR_UPDATES": "false",
        "GF_ANALYTICS_CHECK_FOR_PLUGIN_UPDATES": "false",
        "GF_ANALYTICS_FEEDBACK_LINKS_ENABLED": "false",
        "GF_NEWS_NEWS_FEED_ENABLED": "false",
        "GF_PLUGINS_PLUGIN_ADMIN_ENABLED": "false",
        "GF_PLUGINS_PREINSTALL_DISABLED": "true",
        "GF_SECURITY_DISABLE_GRAVATAR": "true",
    }
    for key, value in expected.items():
        assert env.get(key) == value, key


def test_tempo_is_the_only_root_container_and_it_is_documented(compose):
    privileged = {n: s for n, s in compose["services"].items() if s.get("user") or s.get("cap_add")}
    assert set(privileged) == {"tempo"}
    assert privileged["tempo"]["cap_add"] == ["DAC_OVERRIDE"]
    adr = (ROOT / "docs/architecture/decisions/ADR-023-self-hosted-telemetry.md").read_text(encoding="utf-8")
    ops = (ROOT / "docs/operations/observability.md").read_text(encoding="utf-8")
    for doc in (adr, ops, COMPOSE.read_text(encoding="utf-8")):
        assert "only container run as root" in doc


def test_collector_scrubs_traces_a_second_time_and_names_the_log_service():
    otel = load(OBS / "otel-collector" / "config.yml")
    pipelines = otel["service"]["pipelines"]
    assert "transform/scrub_spans" in pipelines["traces"]["processors"]
    statements = json.dumps(otel["processors"]["transform/scrub_spans"])
    for needle in ("http.target", "http.url", "url.full", "url.path", "url.query", "db.statement", "db.query.text",
                   "exception.message", "exception.stacktrace", "CASE-"):
        assert needle in statements, needle
    assert "http.route" not in statements
    assert "transform/service_name" in pipelines["logs"]["processors"]
    assert "arogyarakshak-api" in json.dumps(otel["processors"]["transform/service_name"])


def _alert_rules():
    return {r["alert"]: r for g in load(OBS / "prometheus/rules/alerts.rules.yml")["groups"] for r in g["rules"] if "alert" in r}


def test_api_target_down_only_fires_for_a_target_that_was_up():
    expr = _alert_rules()["ApiTargetDown"]["expr"]
    # a never-up target (the other workflow's) has max_over_time(up) == 0 and must not page
    assert expr == 'up{job="api"} == 0 and max_over_time(up{job="api"}[7d]) == 1'


def test_promtool_unit_test_file_covers_api_target_down_and_matches_the_rule():
    spec = load(OBS / "prometheus" / "tests" / "alerts.test.yml")
    assert spec["rule_files"] == ["../rules/alerts.rules.yml"]
    rule = _alert_rules()["ApiTargetDown"]
    cases = spec["tests"][0]["alert_rule_test"]
    fired = [c for c in cases if c["exp_alerts"]]
    quiet = [c for c in cases if not c["exp_alerts"]]
    assert fired and quiet
    for case in cases:
        assert case["alertname"] == "ApiTargetDown"
    expected = fired[0]["exp_alerts"][0]
    assert expected["exp_annotations"] == rule["annotations"]
    assert expected["exp_labels"]["severity"] == "page"
    series = {x["series"]: x["values"] for x in spec["tests"][0]["input_series"]}
    assert any(v.startswith("0x") for v in series.values()), "needs a never-up series"
    assert any(v.startswith("1x") for v in series.values()), "needs a was-up-then-down series"


def test_promtool_runs_the_unit_tests_when_available():
    promtool = shutil.which("promtool")
    if not promtool:
        pytest.skip("promtool not installed; run: docker run --rm --entrypoint promtool -v <repo>/infrastructure/observability/prometheus:/p prom/prometheus:v3.5.0 test rules /p/tests/alerts.test.yml")
    result = subprocess.run([promtool, "test", "rules", str(OBS / "prometheus" / "tests" / "alerts.test.yml")], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr


def test_observability_docs_describe_what_is_scrubbed():
    ops = (ROOT / "docs/operations/observability.md").read_text(encoding="utf-8")
    for phrase in ("exception.type", "http.target", "unauthenticated", "fluentd", "METRICS_ENABLED"):
        assert phrase in ops, phrase
    assert "nothing here records case ids" not in ops.lower()
