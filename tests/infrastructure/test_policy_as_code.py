"""Policy-as-code checks (Wave 2 stream E).

Kyverno and OPA are not installed here, so these tests (1) validate the structure of the
Kyverno ClusterPolicies and the Rego files, (2) run the Python reference implementation of the
same rules (infrastructure/policy/policy_checks.py) against the repository's own Kubernetes
manifests and compose files, which must pass, and (3) prove every rule rejects a bad example.
Nothing here executes Kyverno or OPA.
"""

import copy
import importlib.util
import pathlib
import re
import sys

import pytest
import yaml

REPO = pathlib.Path(__file__).resolve().parents[2]
POLICY = REPO / "infrastructure" / "policy"

_spec = importlib.util.spec_from_file_location("arogya_policy_checks", POLICY / "policy_checks.py")
pc = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = pc
_spec.loader.exec_module(pc)


def _policies():
    return {p.stem: yaml.safe_load(p.read_text(encoding="utf-8")) for p in sorted((POLICY / "kyverno").glob("*.yaml"))}


# ---------------------------------------------------------------- Kyverno structure


def test_every_rule_has_a_kyverno_policy_and_nothing_extra():
    assert set(_policies()) == set(pc.RULES)


@pytest.mark.parametrize("name", pc.RULES)
def test_kyverno_policy_structure(name):
    doc = _policies()[name]
    assert doc["apiVersion"] == "kyverno.io/v1" and doc["kind"] == "ClusterPolicy"
    assert doc["metadata"]["name"] == name
    assert doc["spec"]["validationFailureAction"] == "Enforce"
    assert doc["metadata"]["annotations"]["policies.kyverno.io/description"].strip()
    rules = doc["spec"]["rules"]
    assert rules, "a policy needs rules"
    for rule in rules:
        assert rule["name"] and rule["validate"]["message"]
        assert ("pattern" in rule["validate"]) ^ ("deny" in rule["validate"]), rule["name"]
        [match] = rule["match"]["any"]
        assert "Pod" in match["resources"]["kinds"]
        # Scoped to this application's namespace so enforcement cannot break cluster add-ons.
        assert match["resources"]["namespaces"] == ["arogyarakshak"]


def test_kyverno_patterns_encode_the_intended_rule():
    p = _policies()
    pattern = lambda n, i=0: p[n]["spec"]["rules"][i]["validate"]["pattern"]["spec"]  # noqa: E731
    assert pattern("run-as-non-root")["securityContext"]["runAsNonRoot"] is True
    assert pattern("read-only-root-fs")["containers"][0]["securityContext"]["readOnlyRootFilesystem"] is True
    assert pattern("disallow-latest-tag", 1)["containers"][0]["image"] == "!*:latest"
    assert pattern("disallow-latest-tag", 0)["containers"][0]["image"].startswith("*:*")
    assert set(pattern("require-resource-limits")["containers"][0]["resources"]["limits"]) == {"cpu", "memory"}
    sock = p["disallow-docker-sock"]["spec"]["rules"][0]["validate"]["deny"]["conditions"]["any"][0]
    assert "docker.sock" in sock["key"] and sock["operator"] == "GreaterThan"
    ports = pattern("loopback-only-ports")["containers"][0]["=(ports)"][0]
    assert ports == {"=(hostPort)": 0}


# ---------------------------------------------------------------- Rego structure


@pytest.mark.parametrize("name,package", [("workload.rego", "arogya.workload"), ("compose.rego", "arogya.compose")])
def test_rego_files_are_structurally_sound(name, package):
    text = (POLICY / "rego" / name).read_text(encoding="utf-8")
    assert f"\npackage {package}\n" in text
    assert "import rego.v1" in text
    # Balanced delimiters outside comments and strings (a cheap parse; opa itself is not run here).
    code = re.sub(r'"(?:\\.|[^"\\])*"', '""', "\n".join(ln.split("#", 1)[0] for ln in text.splitlines()))
    for open_, close in ("{}", "[]", "()"):
        assert code.count(open_) == code.count(close), f"unbalanced {open_}{close} in {name}"
    assert "deny contains msg if {" in text
    for rule in pc.RULES:
        if name == "workload.rego" or rule in ("disallow-latest-tag", "loopback-only-ports", "disallow-docker-sock"):
            assert f"[{rule}]" in text, f"{name} lacks rule {rule}"


def test_rego_unit_tests_cover_every_rule():
    text = (POLICY / "rego" / "workload_test.rego").read_text(encoding="utf-8")
    assert "package arogya.workload_test" in text
    tests = re.findall(r"^test_\w+ if \{", text, flags=re.M)
    assert len(tests) >= 10


# ---------------------------------------------------------------- the repository passes


def test_repository_manifests_and_compose_files_pass_every_rule():
    assert pc.check_repository() == []


def test_the_checker_actually_read_the_repository_files():
    assert len(pc.k8s_files()) >= 4
    assert {p.name for p in pc.compose_files()} >= {
        "docker-compose.yml", "docker-compose.demo.yml", "docker-compose.observability.yml",
    }
    kinds = {d["kind"] for p in pc.k8s_files() for d in pc.load_yaml_docs(p)}
    assert {"Deployment", "Job"} <= kinds


# ---------------------------------------------------------------- every rule rejects a bad example


def _deployment():
    return {
        "kind": "Deployment",
        "metadata": {"name": "t"},
        "spec": {"template": {"spec": {
            "securityContext": {"runAsNonRoot": True},
            "containers": [{
                "name": "c", "image": "repo/app:1.2.3",
                "resources": {"limits": {"cpu": "1", "memory": "1Gi"}},
                "securityContext": {"readOnlyRootFilesystem": True},
            }],
        }}},
    }


def _rules(doc):
    return {v.rule for v in pc.check_k8s(doc)}


def test_a_compliant_deployment_passes():
    assert pc.check_k8s(_deployment()) == []


def _mutated(fn):
    d = copy.deepcopy(_deployment())
    fn(d["spec"]["template"]["spec"])
    return d


@pytest.mark.parametrize(
    "rule,mutate",
    [
        ("run-as-non-root", lambda s: s["securityContext"].update(runAsNonRoot=False)),
        ("run-as-non-root", lambda s: s.pop("securityContext")),
        ("disallow-latest-tag", lambda s: s["containers"][0].update(image="repo/app:latest")),
        ("disallow-latest-tag", lambda s: s["containers"][0].update(image="repo/app")),
        ("disallow-latest-tag", lambda s: s["containers"][0].update(image="localhost:5000/app")),
        ("require-resource-limits", lambda s: s["containers"][0]["resources"]["limits"].pop("memory")),
        ("require-resource-limits", lambda s: s["containers"][0].pop("resources")),
        ("read-only-root-fs", lambda s: s["containers"][0]["securityContext"].update(readOnlyRootFilesystem=False)),
        ("read-only-root-fs", lambda s: s["containers"][0].pop("securityContext")),
        ("disallow-docker-sock", lambda s: s.update(volumes=[{"name": "d", "hostPath": {"path": "/var/run/docker.sock"}}])),
        ("disallow-docker-sock", lambda s: s.update(volumes=[{"name": "d", "hostPath": {"path": "/run/docker.sock/"}}])),
        ("loopback-only-ports", lambda s: s["containers"][0].update(ports=[{"containerPort": 80, "hostPort": 80}])),
    ],
)
def test_each_k8s_rule_rejects_a_bad_manifest(rule, mutate):
    assert rule in _rules(_mutated(mutate))


def test_init_containers_are_checked_too():
    d = _mutated(lambda s: s.update(initContainers=[{"name": "i", "image": "busybox:latest"}]))
    assert {"disallow-latest-tag", "require-resource-limits", "read-only-root-fs"} <= _rules(d)


def test_digest_pinned_and_registry_port_images_pass():
    assert pc.image_problem("repo/app@sha256:" + "a" * 64) is None
    assert pc.image_problem("localhost:5000/app:1.0") is None
    assert pc.image_problem("localhost:5000/app") is not None


def test_cronjob_pod_template_is_found():
    cron = {"kind": "CronJob", "metadata": {"name": "c"},
            "spec": {"jobTemplate": {"spec": {"template": {"spec": {"containers": [{"name": "x", "image": "a:latest"}]}}}}}}
    assert "disallow-latest-tag" in _rules(cron)


def test_non_workloads_are_ignored():
    assert pc.check_k8s({"kind": "Service", "metadata": {"name": "s"}, "spec": {"type": "ClusterIP"}}) == []


@pytest.mark.parametrize(
    "rule,service",
    [
        ("loopback-only-ports", {"ports": ["9090:9090"]}),
        ("loopback-only-ports", {"ports": ["0.0.0.0:9090:9090"]}),
        ("loopback-only-ports", {"ports": [{"target": 80, "published": 8080}]}),
        ("loopback-only-ports", {"ports": [{"target": 80, "published": 8080, "host_ip": "0.0.0.0"}]}),
        ("disallow-docker-sock", {"volumes": ["/var/run/docker.sock:/var/run/docker.sock"]}),
        ("disallow-docker-sock", {"volumes": [{"type": "bind", "source": "/var/run/docker.sock", "target": "/s"}]}),
        ("disallow-latest-tag", {"image": "grafana/grafana:latest"}),
        ("disallow-latest-tag", {"image": "grafana/grafana"}),
    ],
)
def test_each_compose_rule_rejects_a_bad_service(rule, service):
    assert rule in {v.rule for v in pc.check_compose({"services": {"s": service}})}


@pytest.mark.parametrize(
    "service",
    [
        {"image": "prom/prometheus:v3.5.0", "ports": ["127.0.0.1:9090:9090"]},
        {"ports": ["[::1]:9090:9090"]},
        {"ports": [{"target": 80, "published": 80, "host_ip": "127.0.0.1"}]},
        {"ports": ["8000"]},
        {"volumes": ["pgdata:/var/lib/postgresql/data", "./cfg:/etc/cfg:ro"]},
    ],
)
def test_compliant_compose_services_pass(service):
    assert pc.check_compose({"services": {"s": service}}) == []


def test_compose_override_tags_are_tolerated():
    path = REPO / "docker-compose.demo.yml"
    assert "!override" in path.read_text(encoding="utf-8")
    assert pc.load_yaml_docs(path)


def test_tempo_root_exception_is_documented_not_silently_allowed():
    # Compose files are not subject to the K8s run-as-non-root rule (see compose.rego); the
    # one root container must stay a visible, commented exception.
    text = (REPO / "docker-compose.observability.yml").read_text(encoding="utf-8")
    assert 'user: "0:0"' in text and "only container run as root" in text
