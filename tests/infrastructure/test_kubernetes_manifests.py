"""Policy checks for infrastructure/kubernetes (ADR-021).

These parse the manifests; they do not need a cluster. They pin the properties the
deployment relies on: hardened pods, exactly one API replica, no committed secrets,
probe paths that exist in the API, and environment variables the API actually reads.
Rendering through kustomize is checked when kubectl is installed.
"""

import pathlib
import shutil
import subprocess

import pytest
import yaml

REPO = pathlib.Path(__file__).resolve().parents[2]
K8S = REPO / "infrastructure" / "kubernetes"


def _docs():
    out = []
    for path in sorted(K8S.rglob("*.yaml")):
        if path.name == "kustomization.yaml":
            continue
        out.extend((path, d) for d in yaml.safe_load_all(path.read_text(encoding="utf-8")) if d)
    return out


def _workloads():
    for path, doc in _docs():
        if doc["kind"] in ("Deployment", "Job"):
            yield path, doc, doc["spec"]["template"]["spec"]


def _kustomize_literals():
    base = yaml.safe_load((K8S / "base" / "kustomization.yaml").read_text(encoding="utf-8"))
    [generator] = base["configMapGenerator"]
    return dict(item.split("=", 1) for item in generator["literals"])


def test_no_secret_objects_are_committed():
    assert not [p for p, d in _docs() if d["kind"] == "Secret"], "create Secrets out of band"


def test_every_workload_is_hardened():
    for path, doc, pod in _workloads():
        name = f"{path.name}:{doc['metadata']['name']}"
        assert pod["securityContext"]["runAsNonRoot"] is True, name
        assert pod["securityContext"]["seccompProfile"]["type"] == "RuntimeDefault", name
        assert pod["automountServiceAccountToken"] is False, name
        for c in pod["containers"]:
            sc = c["securityContext"]
            assert sc["allowPrivilegeEscalation"] is False, name
            assert sc["readOnlyRootFilesystem"] is True, name
            assert sc["capabilities"]["drop"] == ["ALL"], name
            assert {"requests", "limits"} <= set(c["resources"]), f"{name}: requests and limits"
            assert not c["image"].endswith(":latest"), name


def test_api_runs_exactly_one_replica_and_is_never_autoscaled():
    [api] = [d for _, d in _docs() if d["kind"] == "Deployment" and d["metadata"]["name"] == "api"]
    assert api["spec"]["replicas"] == 1
    assert api["spec"]["strategy"]["type"] == "Recreate"
    assert not [d for _, d in _docs() if d["kind"] == "HorizontalPodAutoscaler"]


def test_services_are_internal():
    for _, d in _docs():
        if d["kind"] == "Service":
            assert d["spec"]["type"] == "ClusterIP", d["metadata"]["name"]


def test_probe_paths_exist_in_the_api():
    from app.main import app

    routes = {getattr(r, "path", None) for r in app.routes}
    [api] = [d for _, d in _docs() if d["kind"] == "Deployment" and d["metadata"]["name"] == "api"]
    container = api["spec"]["template"]["spec"]["containers"][0]
    for probe in ("startupProbe", "livenessProbe", "readinessProbe"):
        assert container[probe]["httpGet"]["path"] in routes, probe
    assert container["readinessProbe"]["httpGet"]["path"] == "/health/ready"
    assert container["livenessProbe"]["httpGet"]["path"] == "/health/live"


def test_every_configured_variable_is_a_real_setting_and_production_safe():
    from app.config import Settings

    fields = {name.upper() for name in Settings.model_fields}
    # Read by the Kadi package itself (kadi.resolution.semantic), not through Settings.
    fields |= {"KADI_SEMANTIC_MATCHING"}
    literals = _kustomize_literals()
    [api] = [d for _, d in _docs() if d["kind"] == "Deployment" and d["metadata"]["name"] == "api"]
    env_names = {e["name"] for e in api["spec"]["template"]["spec"]["containers"][0]["env"]}
    unknown = sorted((set(literals) | env_names) - fields)
    assert not unknown, f"not read by app.config.Settings: {unknown}"
    assert literals["APP_ENV"] == "production"
    assert literals["SCHEMA_MANAGEMENT"] in ("none", "migrate")
    assert literals["CLINICAL_DEMO_MODE"] == "false"


def test_migration_job_uses_alembic_and_does_not_retry_blindly():
    [job] = [d for _, d in _docs() if d["kind"] == "Job"]
    assert job["spec"]["backoffLimit"] == 0
    assert job["spec"]["template"]["spec"]["containers"][0]["command"] == ["alembic", "upgrade", "head"]


@pytest.mark.skipif(shutil.which("kubectl") is None, reason="kubectl not installed")
def test_overlay_renders_with_kustomize():
    out = subprocess.run(
        ["kubectl", "kustomize", str(K8S / "overlays" / "example")],
        capture_output=True, text=True, check=True,
    ).stdout
    kinds = sorted(d["kind"] for d in yaml.safe_load_all(out) if d)
    assert kinds == sorted(["ConfigMap", "Deployment", "Deployment", "Ingress", "Namespace",
                            "NetworkPolicy", "NetworkPolicy", "Service", "Service", "ServiceAccount"])
    assert all(d["metadata"].get("namespace") == "arogyarakshak"
               for d in yaml.safe_load_all(out) if d and d["kind"] != "Namespace")
