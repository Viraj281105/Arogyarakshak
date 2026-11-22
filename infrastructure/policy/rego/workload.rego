# Kubernetes workload policy (conftest / OPA). Same rules as kyverno/ and policy_checks.py.
#
#   conftest test --policy infrastructure/policy/rego --namespace arogya.workload <rendered.yaml>
#   opa test infrastructure/policy/rego
#
# NOT EXECUTED in this repository's CI yet: neither opa nor conftest was available when this
# was written, so the Rego is parsed for structure by tests/infrastructure/test_policy_as_code.py
# but not run. Run `opa test` before relying on it.
package arogya.workload

import rego.v1

workload_kinds := {"Deployment", "StatefulSet", "DaemonSet", "ReplicaSet", "Job"}

pod_spec := input.spec if input.kind == "Pod"

pod_spec := input.spec.template.spec if input.kind in workload_kinds

pod_spec := input.spec.jobTemplate.spec.template.spec if input.kind == "CronJob"

containers contains c if some c in pod_spec.containers

containers contains c if some c in pod_spec.initContainers

containers contains c if some c in pod_spec.ephemeralContainers

# Same string as FORBIDDEN_HOST_PATH in policy_checks.py and kyverno/disallow-docker-sock.yaml
# (a test asserts they are identical): runtime sockets, their parents, / and runtime state dirs.
forbidden_host_path := `^(/|/var|/var/run|/run)/*$|(^|/)(docker|containerd|crio)\.sock/*$|^/var/lib/(docker|containerd|kubelet)(/.*)?$`

# run-as-non-root
deny contains msg if {
	object.get(pod_spec, ["securityContext", "runAsNonRoot"], false) != true
	msg := sprintf("%s/%s: [run-as-non-root] pod securityContext.runAsNonRoot must be true", [input.kind, input.metadata.name])
}

# run-as-non-root: pod and container overrides
deny contains msg if {
	object.get(pod_spec, ["securityContext", "runAsUser"], null) == 0
	msg := sprintf("%s/%s: [run-as-non-root] pod securityContext.runAsUser must not be 0", [input.kind, input.metadata.name])
}

deny contains msg if {
	some c in containers
	root_container(c)
	msg := sprintf("%s/%s:%s: [run-as-non-root] container must not set runAsNonRoot: false or runAsUser: 0", [input.kind, input.metadata.name, c.name])
}

root_container(c) if object.get(c, ["securityContext", "runAsNonRoot"], null) == false

root_container(c) if object.get(c, ["securityContext", "runAsUser"], null) == 0

# disallow-latest-tag
deny contains msg if {
	some c in containers
	not image_pinned(c.image)
	msg := sprintf("%s/%s: [disallow-latest-tag] image %q needs an explicit tag other than latest", [input.kind, input.metadata.name, c.image])
}

image_pinned(image) if contains(image, "@sha256:")

image_pinned(image) if {
	parts := split(image, "/")
	last := parts[count(parts) - 1]
	tagged := split(last, ":")
	count(tagged) == 2
	tagged[1] != "latest"
}

# require-resource-limits
deny contains msg if {
	some c in containers
	some key in {"cpu", "memory"}
	object.get(c, ["resources", "limits", key], "") == ""
	msg := sprintf("%s/%s:%s: [require-resource-limits] resources.limits.%s is required", [input.kind, input.metadata.name, c.name, key])
}

# read-only-root-fs
deny contains msg if {
	some c in containers
	object.get(c, ["securityContext", "readOnlyRootFilesystem"], false) != true
	msg := sprintf("%s/%s:%s: [read-only-root-fs] securityContext.readOnlyRootFilesystem must be true", [input.kind, input.metadata.name, c.name])
}

# disallow-docker-sock
deny contains msg if {
	some v in pod_spec.volumes
	regex.match(forbidden_host_path, v.hostPath.path)
	msg := sprintf("%s/%s: [disallow-docker-sock] volume %s mounts a runtime socket or node path", [input.kind, input.metadata.name, v.name])
}

# loopback-only-ports (Kubernetes form: no hostPort)
deny contains msg if {
	some c in containers
	some p in c.ports
	p.hostPort > 0
	msg := sprintf("%s/%s:%s: [loopback-only-ports] hostPort binds every node interface; use a Service", [input.kind, input.metadata.name, c.name])
}
