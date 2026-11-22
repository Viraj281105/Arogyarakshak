"""Policy-as-code checks (Wave 2 stream E).

Kyverno and OPA are not installed here, so these tests (1) hold the Python reference
implementation (infrastructure/policy/policy_checks.py) to a shared fixture corpus that the Rego
tests and the generated `kyverno test` set also use, (2) check that the three forms carry the same
rules and the very same host-path regex, (3) evaluate the Kyverno image and host-path expressions
with Python's `re` against the same inputs, and (4) run the checker over the repository and over
deliberately bad trees. Nothing here executes Kyverno or OPA.
"""

import importlib.util
import pathlib
import re
import sys

import pytest
import yaml

REPO = pathlib.Path(__file__).resolve().parents[2]
POLICY = REPO / "infrastructure" / "policy"
FIXTURES = POLICY / "fixtures"


def _load(name):
    spec = importlib.util.spec_from_file_location(name, POLICY / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


pc = _load("policy_checks")
kt = _load("build_kyverno_tests")


def _policies():
    return {p.stem: yaml.safe_load(p.read_text(encoding="utf-8")) for p in sorted((POLICY / "kyverno").glob("*.yaml"))}


def _fixtures(verdict):
    return {p.stem: yaml.safe_load(p.read_text(encoding="utf-8")) for p in sorted((FIXTURES / verdict).glob("*.yaml"))}


def _violations(fixture):
    check = pc.check_k8s if fixture["kind"] == "k8s" else pc.check_compose
    return check(fixture["object"])


GOOD, BAD = _fixtures("good"), _fixtures("bad")


# ---------------------------------------------------------------- shared fixture corpus


def test_the_corpus_is_big_enough_and_every_rule_has_a_bad_case():
    assert len(GOOD) >= 10 and len(BAD) >= 30
    assert {f["rule"] for f in BAD.values()} == set(pc.RULES)
    assert {f["kind"] for f in {**GOOD, **BAD}.values()} == {"k8s", "compose"}


@pytest.mark.parametrize("name", sorted(GOOD))
def test_good_fixture_passes(name):
    assert _violations(GOOD[name]) == []


@pytest.mark.parametrize("name", sorted(BAD))
def test_bad_fixture_violates_exactly_its_annotated_rule(name):
    fixture = BAD[name]
    assert {v.rule for v in _violations(fixture)} == {fixture["rule"]}


# ---------------------------------------------------------------- rule coverage in all three forms


def test_every_rule_has_a_kyverno_policy_and_nothing_extra():
    assert set(_policies()) == set(pc.RULES)


@pytest.mark.parametrize("name", pc.RULES)
def test_kyverno_policy_structure(name):
    doc = _policies()[name]
    assert doc["apiVersion"] == "kyverno.io/v1" and doc["kind"] == "ClusterPolicy"
    assert doc["metadata"]["name"] == name
    assert doc["spec"]["validationFailureAction"] == "Enforce"
    assert doc["metadata"]["annotations"]["policies.kyverno.io/description"].strip()
    for rule in doc["spec"]["rules"]:
        validate = rule["validate"]
        assert rule["name"] and validate["message"]
        assert sum(k in validate for k in ("pattern", "deny", "foreach")) == 1, rule["name"]
        [match] = rule["match"]["any"]
        assert "Pod" in match["resources"]["kinds"]
        assert match["resources"]["namespaces"] == ["arogyarakshak"], "scoped so cluster add-ons are unaffected"


def test_kyverno_rule_names_used_by_fixtures_exist():
    names = {p: [r["name"] for r in d["spec"]["rules"]] for p, d in _policies().items()}
    for fixture in BAD.values():
        for rule in fixture.get("kyverno_rules") or []:
            assert rule in names[fixture["rule"]]


def test_pattern_rules_cover_init_and_ephemeral_containers():
    for name in ("run-as-non-root", "require-resource-limits", "read-only-root-fs", "loopback-only-ports"):
        for rule in _policies()[name]["spec"]["rules"]:
            spec = rule["validate"]["pattern"]["spec"]
            if "containers" in spec:
                assert "=(initContainers)" in spec and "=(ephemeralContainers)" in spec, (name, rule["name"])


def test_foreach_rules_cover_every_container_list():
    for rule in _policies()["disallow-latest-tag"]["spec"]["rules"]:
        lists = " ".join(f["list"] for f in rule["validate"]["foreach"])
        assert "spec.containers" in lists and "initContainers" in lists and "ephemeralContainers" in lists


def test_kyverno_nonroot_and_hostport_patterns():
    p = _policies()
    pod = p["run-as-non-root"]["spec"]["rules"][0]["validate"]["pattern"]["spec"]["securityContext"]
    assert pod == {"runAsNonRoot": True, "=(runAsUser)": ">0"}
    container = p["run-as-non-root"]["spec"]["rules"][1]["validate"]["pattern"]["spec"]["containers"][0]
    assert container["=(securityContext)"] == {"=(runAsNonRoot)": True, "=(runAsUser)": ">0"}
    port = p["loopback-only-ports"]["spec"]["rules"][0]["validate"]["pattern"]["spec"]["containers"][0]
    assert port == {"=(ports)": [{"=(hostPort)": 0}]}  # 0 means unset, like the Python and Rego forms


def test_the_host_path_regex_is_identical_in_all_forms():
    expected = pc.FORBIDDEN_HOST_PATH
    for name in ("workload.rego", "compose.rego"):
        assert expected in (POLICY / "rego" / name).read_text(encoding="utf-8"), name
    [rule] = _policies()["disallow-docker-sock"]["spec"]["rules"]
    [foreach] = rule["validate"]["foreach"]
    key = foreach["deny"]["conditions"]["any"][0]["key"]
    assert key == "{{ regex_match('" + expected + "', element.hostPath.path || '') }}"


def test_the_kyverno_volume_expression_tolerates_a_pod_without_volumes():
    [rule] = _policies()["disallow-docker-sock"]["spec"]["rules"]
    assert rule["validate"]["foreach"][0]["list"] == "request.object.spec.volumes || `[]`"


def _kyverno_image_regexes():
    rules = {r["name"]: r for r in _policies()["disallow-latest-tag"]["spec"]["rules"]}

    def pull(rule):
        key = rule["validate"]["foreach"][0]["deny"]["conditions"]["any"][0]["key"]
        return re.search(r"regex_match\('(.*)', element\.image\)", key).group(1)

    return pull(rules["require-image-tag"]), pull(rules["disallow-latest"])


IMAGES = [
    "repo/app:1.2.3", "repo/app:latest", "repo/app", "localhost:5000/app", "localhost:5000/app:1.0",
    "localhost:5000/app:latest", "app", "app:2", "registry.example:443/team/app:v1",
    "repo/app@sha256:" + "a" * 64, "repo/app:1.0@sha256:" + "b" * 64,
]


@pytest.mark.parametrize("image", IMAGES)
def test_kyverno_image_expressions_agree_with_the_python_rule(image):
    tagged, latest = _kyverno_image_regexes()
    kyverno_denies = (re.search(tagged, image) is None) or (re.search(latest, image) is not None)
    assert kyverno_denies == (pc.image_problem(image) is not None), image


HOST_PATHS = {
    "/var/run/docker.sock": True, "/var/run/docker.sock/": True, "/run/docker.sock": True, "/var/run": True,
    "/var/run/": True, "/run": True, "/run/": True, "/": True, "///": True, "/var": True,
    "/var/lib/docker": True, "/var/lib/docker/overlay2": True, "/var/lib/containerd": True,
    "/var/lib/kubelet/": True, "/run/containerd/containerd.sock": True, "/var/run/crio/crio.sock": True,
    "/opt/app/crio.sock": True,
    "/mnt/data": False, "/data": False, "/var/lib/mysql": False, "/var/runner": False,
    "/home/docker.sock.d": False, "": False, "relative/path": False,
}


@pytest.mark.parametrize("path,forbidden", sorted(HOST_PATHS.items()))
def test_host_path_rule(path, forbidden):
    assert pc.forbidden_host_path(path) is forbidden
    pod = {"kind": "Pod", "metadata": {"name": "p"}, "spec": {
        "securityContext": {"runAsNonRoot": True}, "volumes": [{"name": "v", "hostPath": {"path": path}}],
        "containers": [{"name": "c", "image": "a:1", "resources": {"limits": {"cpu": "1", "memory": "1"}},
                        "securityContext": {"readOnlyRootFilesystem": True}}]}}
    assert bool(pc.check_k8s(pod)) is forbidden
    compose = {"services": {"s": {"volumes": [f"{path}:/target"]}}}
    assert bool(pc.check_compose(compose)) is (forbidden and bool(path))


@pytest.mark.parametrize("name,package", [("workload.rego", "arogya.workload"), ("compose.rego", "arogya.compose")])
def test_rego_files_are_structurally_sound(name, package):
    text = (POLICY / "rego" / name).read_text(encoding="utf-8")
    assert f"\npackage {package}\n" in text
    assert "import rego.v1" in text
    code = re.sub(r"`[^`]*`", "``", text)  # raw strings hold regex brackets
    code = re.sub(r'"(?:\\.|[^"\\])*"', '""', "\n".join(ln.split("#", 1)[0] for ln in code.splitlines()))
    for open_, close in ("{}", "[]", "()"):
        assert code.count(open_) == code.count(close), f"unbalanced {open_}{close} in {name}"
    assert "deny contains msg if {" in text
    for rule in pc.RULES:
        if name == "workload.rego" or rule in ("disallow-latest-tag", "loopback-only-ports", "disallow-docker-sock"):
            assert f"[{rule}]" in text, f"{name} lacks rule {rule}"


def test_rego_runs_the_shared_fixtures_and_covers_init_and_ephemeral_containers():
    text = (POLICY / "rego" / "fixtures_test.rego").read_text(encoding="utf-8")
    assert "package arogya.fixtures_test" in text and "data.good" in text and "data.bad" in text
    assert "build_opa_data.py" in text and "opa test infrastructure/policy/rego" in text
    assert "do NOT pass the fixtures directory" in text
    workload = (POLICY / "rego" / "workload.rego").read_text(encoding="utf-8")
    assert "pod_spec.initContainers" in workload and "pod_spec.ephemeralContainers" in workload
    assert "p.hostPort > 0" in workload, "hostPort: 0 is unset"


def test_the_generated_kyverno_test_set_is_up_to_date():
    assert kt.main(["--check"]) == 0, "run: python infrastructure/policy/build_kyverno_tests.py"
    test = yaml.safe_load((POLICY / "kyverno-tests" / "kyverno-test.yaml").read_text(encoding="utf-8"))
    text = (POLICY / "kyverno-tests" / "resources.yaml").read_text(encoding="utf-8")
    resources = {d["metadata"]["name"] for d in yaml.safe_load_all(text)}
    k8s = {n.replace("_", "-") for n, f in {**GOOD, **BAD}.items() if f["kind"] == "k8s"}
    assert resources == k8s
    outcomes = {(r["policy"], r["rule"], res): r["result"] for r in test["results"] for res in r["resources"]}
    assert outcomes[("loopback-only-ports", "no-host-port", "k8s-host-port")] == "fail"
    assert outcomes[("loopback-only-ports", "no-host-port", "k8s-host-port-zero-is-unset")] == "pass"


# ---------------------------------------------------------------- compose port parsing


@pytest.mark.parametrize(
    "spec,loopback",
    [
        ("8000", False), ("8000/tcp", False), ("8000:8000", False), ("9090:9090/udp", False),
        ("0.0.0.0:9090:9090", False), ("[::]:9090:9090", False), ("[::1]:9090:9090", True),
        ("127.0.0.1:9090:9090", True), ("127.0.0.1:9090:9090/tcp", True), ("localhost:80:80", True),
        ("${X:-127.0.0.1}:80:80", True), ("${X:-0.0.0.0}:80:80", False), ("${X}:80:80", False),
        ("${X:-[::1]}:80:80", True), ("127.0.0.1:${PORT:-80}:80", True), ("127.0.0.1::80", True),
        ({"target": 80, "published": 80, "host_ip": "::1"}, True),
        ({"target": 80, "published": 80, "host_ip": "127.0.0.1"}, True),
        ({"target": 80, "published": 80}, False),
        ({"target": 80}, False),
        ({"target": 80, "published": 80, "host_ip": "0.0.0.0"}, False),
        ({"target": 80, "published": 80, "host_ip": "::"}, False),
    ],
)
def test_compose_port_parsing(spec, loopback):
    assert pc.port_is_loopback(spec) is loopback


def test_a_bare_container_port_is_no_longer_compliant():
    assert [v.rule for v in pc.check_compose({"services": {"s": {"ports": ["8000"]}}})] == ["loopback-only-ports"]


def test_compose_override_tags_are_tolerated():
    path = REPO / "docker-compose.demo.yml"
    assert "!override" in path.read_text(encoding="utf-8")
    assert pc.load_yaml_docs(path)


def test_tempo_root_exception_is_documented_not_silently_allowed():
    text = (REPO / "docker-compose.observability.yml").read_text(encoding="utf-8")
    assert 'user: "0:0"' in text and "only container run as root" in text


# ---------------------------------------------------------------- the repository, and bad trees


def test_repository_manifests_and_compose_files_pass_every_rule():
    assert pc.check_repository() == []


def test_the_checker_actually_read_the_repository_files():
    assert len(pc.k8s_files()) >= 4 and len(pc.kustomization_files()) >= 2
    assert {p.name for p in pc.compose_files()} >= {
        "docker-compose.yml", "docker-compose.demo.yml", "docker-compose.observability.yml",
    }
    kinds = {d["kind"] for p in pc.k8s_files() for d in pc.load_yaml_docs(p)}
    assert {"Deployment", "Job"} <= kinds


def _tree(tmp_path, k8s=None, compose=None, kustomization=None):
    base = tmp_path / "infrastructure" / "kubernetes" / "base"
    base.mkdir(parents=True)
    if k8s is not None:
        (base / "bad.yaml").write_text(yaml.safe_dump(k8s), encoding="utf-8")
    if kustomization is not None:
        overlay = tmp_path / "infrastructure" / "kubernetes" / "overlays" / "x"
        overlay.mkdir(parents=True)
        (overlay / "kustomization.yaml").write_text(yaml.safe_dump(kustomization), encoding="utf-8")
    if compose is not None:
        (tmp_path / "docker-compose.yml").write_text(yaml.safe_dump(compose), encoding="utf-8")
    return tmp_path


def test_an_empty_tree_is_clean(tmp_path):
    assert pc.check_repository(_tree(tmp_path)) == []
    assert pc.main(["--root", str(tmp_path)]) == 0


@pytest.mark.parametrize("name", ["k8s_latest_tag", "k8s_docker_sock", "k8s_writable_root_fs"])
def test_a_bad_manifest_on_disk_fails_the_run(tmp_path, capsys, name):
    _tree(tmp_path, k8s=BAD[name]["object"])
    assert pc.check_repository(tmp_path)
    assert pc.main(["--root", str(tmp_path)]) == 1
    assert BAD[name]["rule"] in capsys.readouterr().out


@pytest.mark.parametrize("name", ["compose_bare_container_port", "compose_ipv6_any", "compose_docker_sock_bind"])
def test_a_bad_compose_file_on_disk_fails_the_run(tmp_path, capsys, name):
    _tree(tmp_path, compose=BAD[name]["object"])
    assert pc.check_repository(tmp_path)
    assert pc.main(["--root", str(tmp_path)]) == 1
    assert BAD[name]["rule"] in capsys.readouterr().out


@pytest.mark.parametrize("entry", [{"name": "a", "newTag": "latest"}, {"name": "a", "newTag": ""},
                                   {"name": "a", "newName": "registry.example/a"}])
def test_an_overlay_that_repoints_an_image_at_latest_fails(tmp_path, entry):
    _tree(tmp_path, kustomization={"images": [entry]})
    assert [v.rule for v in pc.check_repository(tmp_path)] == ["disallow-latest-tag"]
    assert pc.main(["--root", str(tmp_path)]) == 1


def test_an_overlay_with_a_tag_or_digest_passes(tmp_path):
    entries = [{"name": "a", "newTag": "1.2.3"}, {"name": "b", "newName": "r.example/b", "digest": "sha256:" + "a" * 64}]
    _tree(tmp_path, kustomization={"images": entries})
    assert pc.check_repository(tmp_path) == []
