"""Reference implementation of the policy-as-code rules, in Python.

The authoritative policies for a cluster are the Kyverno ClusterPolicies in ``kyverno/`` and the
Rego in ``rego/``. Neither engine is available in CI here, so this module implements the SAME
rules over the repository's own manifests and compose files. ``tests/infrastructure/
test_policy_as_code.py`` runs it against the shared fixture corpus (``fixtures/``, which the Rego
tests and the generated ``kyverno test`` set also use) and against the repository, and checks that
every rule exists in all three forms. It is a guard against drift in this repository, not a
substitute for running Kyverno or OPA where they are deployed.

Rules (rule id -> what it forbids):

    run-as-non-root            a pod without runAsNonRoot: true, or runAsUser/runAsNonRoot overridden
                               to root on a container
    disallow-latest-tag        an image with no tag (a registry port is not a tag), or the tag latest
    require-resource-limits    a container without cpu and memory limits
    read-only-root-fs          a container without readOnlyRootFilesystem: true
    disallow-docker-sock       a hostPath or bind of a runtime socket, its parent directory, / or the
                               runtime and kubelet state directories (see FORBIDDEN_HOST_PATH)
    loopback-only-ports        a compose port not bound to loopback (a bare "8000" binds all
                               interfaces), or a Kubernetes hostPort (0 is unset)

Containers means initContainers, containers and ephemeralContainers.
Usage: ``python infrastructure/policy/policy_checks.py [--root DIR]`` exits 1 and prints violations.
"""

from __future__ import annotations

import pathlib
import re
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

# One regex, carried verbatim by this module, rego/workload.rego, rego/compose.rego and
# kyverno/disallow-docker-sock.yaml (a test asserts every file contains exactly this string). It
# matches a host path that exposes the container runtime or the node: runtime sockets, their
# parent directories (mounting /var/run exposes docker.sock), the node root, and the runtime and
# kubelet state directories. Trailing slashes are tolerated; no other normalisation is done.
FORBIDDEN_HOST_PATH = (
    r"^(/|/var|/var/run|/run)/*$"
    r"|(^|/)(docker|containerd|crio)\.sock/*$"
    r"|^/var/lib/(docker|containerd|kubelet)(/.*)?$"
)
LOOPBACK_HOSTS = ("127.0.0.1", "[::1]", "localhost")  # short syntax
LOOPBACK_HOST_IPS = ("127.0.0.1", "::1", "[::1]", "localhost")  # long syntax `host_ip`


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
CONTAINER_LISTS = ("initContainers", "containers", "ephemeralContainers")


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
    for key in CONTAINER_LISTS:
        yield from pod.get(key) or []


def image_problem(image: str) -> Optional[str]:
    """None when the reference is pinned by a tag other than ``latest`` or by digest."""
    if "@sha256:" in image:
        return None
    name = image.rsplit("/", 1)[-1]  # a registry port (localhost:5000/app) is not a tag
    if ":" not in name:
        return "has no tag (an untagged image means latest)"
    if name.rsplit(":", 1)[1] == "latest":
        return "uses the latest tag"
    return None


def forbidden_host_path(path: str) -> bool:
    return bool(path) and re.search(FORBIDDEN_HOST_PATH, path) is not None


def check_k8s(doc: Dict[str, Any]) -> List[Violation]:
    pod = pod_spec(doc)
    if pod is None:
        return []
    ident = f"{doc.get('kind')}/{(doc.get('metadata') or {}).get('name', '?')}"
    out: List[Violation] = []

    pod_sc = pod.get("securityContext") or {}
    if pod_sc.get("runAsNonRoot") is not True:
        out.append(Violation("run-as-non-root", ident, "pod securityContext.runAsNonRoot must be true"))
    if pod_sc.get("runAsUser") == 0:
        out.append(Violation("run-as-non-root", ident, "pod securityContext.runAsUser must not be 0"))

    for volume in pod.get("volumes") or []:
        path = (volume.get("hostPath") or {}).get("path") or ""
        if forbidden_host_path(path):
            out.append(Violation("disallow-docker-sock", ident, f"volume {volume.get('name')} mounts {path}"))

    for c in _containers(pod):
        cid = f"{ident}:{c.get('name')}"
        sc = c.get("securityContext") or {}
        if sc.get("runAsNonRoot") is False or sc.get("runAsUser") == 0:
            out.append(Violation("run-as-non-root", cid, "container must not set runAsNonRoot: false or runAsUser: 0"))
        problem = image_problem(str(c.get("image", "")))
        if problem:
            out.append(Violation("disallow-latest-tag", cid, f"image {c.get('image')!r} {problem}"))
        limits = (c.get("resources") or {}).get("limits") or {}
        for key in ("cpu", "memory"):
            if not limits.get(key):
                out.append(Violation("require-resource-limits", cid, f"resources.limits.{key} is required"))
        if sc.get("readOnlyRootFilesystem") is not True:
            out.append(Violation("read-only-root-fs", cid, "securityContext.readOnlyRootFilesystem must be true"))
        for port in c.get("ports") or []:
            if port.get("hostPort"):  # 0 is "unset" in Kubernetes
                out.append(Violation("loopback-only-ports", cid, "hostPort binds every node interface; use a Service"))
    return out


def check_kustomization(doc: Dict[str, Any], source: str = "kustomization.yaml") -> List[Violation]:
    """An overlay can re-point an image at ``latest`` (images: newTag) after the base passed.
    Python only: a Kustomization is not a workload, so Kyverno and Rego never see it."""
    out: List[Violation] = []
    for entry in doc.get("images") or []:
        tag = entry.get("newTag")
        if tag is not None and str(tag).strip() in ("", "latest"):
            out.append(Violation("disallow-latest-tag", source, f"images: {entry.get('name')} newTag {tag!r}"))
        new_name = str(entry.get("newName") or "")
        if new_name and tag is None and not entry.get("digest") and image_problem(new_name):
            out.append(Violation("disallow-latest-tag", source, f"images: newName {new_name!r} has no tag or digest"))
    return out


# --------------------------------------------------------------------------- Compose

_DEFAULTED = re.compile(r"\$\{[^}:]+:?-([^}]*)\}")
_UNRESOLVED = re.compile(r"\$\{[^}]*\}")
_PROTOCOL = re.compile(r"/[A-Za-z]+$")
_BRACKETED = re.compile(r"^(\[[^\]]+\]):.+")


def resolve_interpolation(text: str) -> str:
    """``${X:-default}`` becomes its default; any other ``${...}`` cannot be proven safe."""
    return _UNRESOLVED.sub("UNRESOLVED", _DEFAULTED.sub(r"\1", text))


def port_bind_host(spec: Any) -> str:
    """The host address a compose ``ports`` entry binds ('' when it binds every interface).
    A bare container port ("8000") and "8000:8000" both publish on all interfaces."""
    if isinstance(spec, dict):
        return resolve_interpolation(str(spec.get("host_ip") or ""))
    text = _PROTOCOL.sub("", resolve_interpolation(str(spec)))
    bracket = _BRACKETED.match(text)
    if bracket:
        return bracket.group(1)
    parts = text.split(":")
    return parts[0] if len(parts) == 3 else ""


def port_is_loopback(spec: Any) -> bool:
    allowed = LOOPBACK_HOST_IPS if isinstance(spec, dict) else LOOPBACK_HOSTS
    return port_bind_host(spec) in allowed


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
            if not port_is_loopback(spec):
                out.append(Violation("loopback-only-ports", ident, f"published port {spec!r} is not bound to loopback"))
        for spec in service.get("volumes") or []:
            if forbidden_host_path(_volume_source(spec)):
                out.append(Violation("disallow-docker-sock", ident, f"mounts a runtime socket or node path ({spec!r})"))
    return out


# --------------------------------------------------------------------------- Loading


def load_yaml_docs(path: pathlib.Path) -> List[Dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    return [d for d in yaml.load_all(text, Loader=_ComposeLoader) if isinstance(d, dict)]


def k8s_files(root: pathlib.Path = REPO) -> List[pathlib.Path]:
    base = root / "infrastructure" / "kubernetes"
    return [p for p in sorted(base.rglob("*.yaml")) if p.name != "kustomization.yaml"]


def kustomization_files(root: pathlib.Path = REPO) -> List[pathlib.Path]:
    return sorted((root / "infrastructure" / "kubernetes").rglob("kustomization.yaml"))


def compose_files(root: pathlib.Path = REPO) -> List[pathlib.Path]:
    return sorted(root.glob("docker-compose*.yml"))


def check_repository(root: pathlib.Path = REPO) -> List[Violation]:
    out: List[Violation] = []
    for path in k8s_files(root):
        for doc in load_yaml_docs(path):
            out.extend(check_k8s(doc))
    for path in kustomization_files(root):
        for doc in load_yaml_docs(path):
            out.extend(check_kustomization(doc, str(path.relative_to(root))))
    for path in compose_files(root):
        for doc in load_yaml_docs(path):
            out.extend(check_compose(doc, path.name))
    return out


def main(argv: Iterable[str] = ()) -> int:
    args = list(argv)
    root = pathlib.Path(args[args.index("--root") + 1]) if "--root" in args else REPO
    violations = check_repository(root)
    for v in violations:
        print(v)
    print(f"{len(violations)} policy violation(s)")
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
