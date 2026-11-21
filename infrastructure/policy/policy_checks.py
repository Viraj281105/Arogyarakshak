"""Reference implementation of the policy-as-code rules, in Python.

The authoritative policies for a cluster are the Kyverno ClusterPolicies in ``kyverno/`` and the
Rego in ``rego/``. Neither engine is available in CI here, so this module implements the SAME
rules over the repository's own manifests and compose files. ``tests/infrastructure/
test_policy_as_code.py`` runs it, proves each rule rejects a bad example, and checks that every
rule has a Kyverno policy and a Rego rule of the same name. It is a guard against drift in this
repository, not a substitute for running Kyverno or OPA where they are deployed.

Rules (rule id -> what it forbids):

    run-as-non-root            a pod that does not set runAsNonRoot: true
    disallow-latest-tag        an image with no tag, or the tag ``latest``
    require-resource-limits    a container without cpu and memory limits
    read-only-root-fs          a container without readOnlyRootFilesystem: true
    disallow-docker-sock       a hostPath volume (or compose bind) of the Docker socket
    loopback-only-ports        a published port not bound to loopback (compose), or a hostPort (k8s)

Usage: ``python infrastructure/policy/policy_checks.py`` exits 1 and prints violations.
"""

from __future__ import annotations

import pathlib
import sys
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Iterator, List, Optional

import yaml

REPO = pathlib.Path(__file__).resolve().parents[2]
RULES = (
    "run-as-non-root",
    "disallow-latest-tag",
    "require-resource-limits",
    "read-only-root-fs",
    "disallow-docker-sock",
    "loopback-only-ports",
)
DOCKER_SOCKETS = ("/var/run/docker.sock", "/run/docker.sock")
LOOPBACK_HOSTS = ("127.0.0.1", "[::1]", "localhost")


@dataclass(frozen=True)
class Violation:
    rule: str
    resource: str
    message: str

    def __str__(self) -> str:
        return f"[{self.rule}] {self.resource}: {self.message}"


class _ComposeLoader(yaml.SafeLoader):
    """SafeLoader that tolerates Compose-only tags such as ``!override`` and ``!reset``."""


def _ignore_tag(loader: yaml.SafeLoader, tag_suffix: str, node: yaml.Node) -> Any:
    if isinstance(node, yaml.SequenceNode):
        return loader.construct_sequence(node, deep=True)
    if isinstance(node, yaml.MappingNode):
        return loader.construct_mapping(node, deep=True)
    return loader.construct_scalar(node)


_ComposeLoader.add_multi_constructor("!", _ignore_tag)


# --------------------------------------------------------------------------- Kubernetes

WORKLOAD_KINDS = ("Pod", "Deployment", "StatefulSet", "DaemonSet", "ReplicaSet", "Job", "CronJob")


def pod_spec(doc: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    kind = doc.get("kind")
    spec = doc.get("spec") or {}
    if kind == "Pod":
        return spec
    if kind == "CronJob":
        return (((spec.get("jobTemplate") or {}).get("spec") or {}).get("template") or {}).get("spec")
    if kind in WORKLOAD_KINDS:
        return (spec.get("template") or {}).get("spec")
    return None


def _containers(pod: Dict[str, Any]) -> Iterator[Dict[str, Any]]:
    for key in ("initContainers", "containers"):
        yield from pod.get(key) or []


def image_problem(image: str) -> Optional[str]:
    """None when the reference is pinned by a tag other than ``latest`` or by digest."""
    if "@sha256:" in image:
        return None
    name = image.rsplit("/", 1)[-1]
    if ":" not in name:
        return "has no tag (an untagged image means latest)"
    if name.rsplit(":", 1)[1] == "latest":
        return "uses the latest tag"
    return None


def check_k8s(doc: Dict[str, Any]) -> List[Violation]:
    pod = pod_spec(doc)
    if pod is None:
        return []
    ident = f"{doc.get('kind')}/{(doc.get('metadata') or {}).get('name', '?')}"
    out: List[Violation] = []

    if (pod.get("securityContext") or {}).get("runAsNonRoot") is not True:
        out.append(Violation("run-as-non-root", ident, "pod securityContext.runAsNonRoot must be true"))

    for volume in pod.get("volumes") or []:
        path = (volume.get("hostPath") or {}).get("path")
        if path and path.rstrip("/") in DOCKER_SOCKETS:
            out.append(Violation("disallow-docker-sock", ident, f"volume {volume.get('name')} mounts {path}"))

    for c in _containers(pod):
        cid = f"{ident}:{c.get('name')}"
        problem = image_problem(str(c.get("image", "")))
        if problem:
            out.append(Violation("disallow-latest-tag", cid, f"image {c.get('image')!r} {problem}"))
        limits = (c.get("resources") or {}).get("limits") or {}
        for key in ("cpu", "memory"):
            if not limits.get(key):
                out.append(Violation("require-resource-limits", cid, f"resources.limits.{key} is required"))
        if (c.get("securityContext") or {}).get("readOnlyRootFilesystem") is not True:
            out.append(Violation("read-only-root-fs", cid, "securityContext.readOnlyRootFilesystem must be true"))
        for port in c.get("ports") or []:
            if port.get("hostPort"):
                out.append(Violation("loopback-only-ports", cid, "hostPort binds every node interface; use a Service"))
    return out


# --------------------------------------------------------------------------- Compose


def _port_host(spec: Any) -> Optional[str]:
    """The bind address of a published compose port, '' when unspecified (all interfaces),
    None when the port is not published (container-only)."""
    if isinstance(spec, dict):
        if not spec.get("published"):
            return None
        return str(spec.get("host_ip") or "")
    text = str(spec)
    parts = text.split(":")
    if len(parts) == 1:
        return None  # "8000": container port only, ephemeral host port on all interfaces
    if text.startswith("["):
        host = text[: text.index("]") + 1]
        return host
    if len(parts) == 2:
        return ""  # "8000:8000": all interfaces
    return parts[0]


def _volume_source(spec: Any) -> str:
    if isinstance(spec, dict):
        return str(spec.get("source") or "")
    return str(spec).split(":", 1)[0]


def check_compose(doc: Dict[str, Any], source: str = "compose") -> List[Violation]:
    out: List[Violation] = []
    for name, service in (doc.get("services") or {}).items():
        ident = f"{source}:{name}"
        image = service.get("image")
        if image:
            problem = image_problem(str(image))
            if problem:
                out.append(Violation("disallow-latest-tag", ident, f"image {image!r} {problem}"))
        for spec in service.get("ports") or []:
            host = _port_host(spec)
            if host is not None and host not in LOOPBACK_HOSTS:
                out.append(Violation("loopback-only-ports", ident, f"published port {spec!r} is not bound to 127.0.0.1"))
        for spec in service.get("volumes") or []:
            if _volume_source(spec).rstrip("/") in DOCKER_SOCKETS:
                out.append(Violation("disallow-docker-sock", ident, f"mounts the Docker socket ({spec!r})"))
    return out


# --------------------------------------------------------------------------- Loading


def load_yaml_docs(path: pathlib.Path) -> List[Dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    return [d for d in yaml.load_all(text, Loader=_ComposeLoader) if isinstance(d, dict)]


def k8s_files(root: pathlib.Path = REPO) -> List[pathlib.Path]:
    base = root / "infrastructure" / "kubernetes"
    return [p for p in sorted(base.rglob("*.yaml")) if p.name != "kustomization.yaml"]


def compose_files(root: pathlib.Path = REPO) -> List[pathlib.Path]:
    return sorted(root.glob("docker-compose*.yml"))


def check_repository(root: pathlib.Path = REPO) -> List[Violation]:
    out: List[Violation] = []
    for path in k8s_files(root):
        for doc in load_yaml_docs(path):
            out.extend(check_k8s(doc))
    for path in compose_files(root):
        for doc in load_yaml_docs(path):
            out.extend(check_compose(doc, path.name))
    return out


def main(argv: Iterable[str] = ()) -> int:
    violations = check_repository()
    for v in violations:
        print(v)
    print(f"{len(violations)} policy violation(s)")
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
