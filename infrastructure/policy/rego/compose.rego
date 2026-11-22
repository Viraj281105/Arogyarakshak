# Docker Compose policy (conftest / OPA): the compose-side rules of policy_checks.py.
#
#   conftest test --policy infrastructure/policy/rego --namespace arogya.compose docker-compose.yml
#
# Scope: image tags, loopback-only published ports and no runtime socket / node path binds.
# Compose files here are local-development and demo stacks, so run-as-non-root, read-only root
# filesystem and resource limits are enforced for Kubernetes only (rego/workload.rego).
# NOT EXECUTED here (no opa/conftest); the shared fixtures in ../fixtures are run by the Python
# reference implementation, which this file must agree with.
package arogya.compose

import rego.v1

# Same string as FORBIDDEN_HOST_PATH in policy_checks.py (a test asserts they are identical).
forbidden_host_path := `^(/|/var|/var/run|/run)/*$|(^|/)(docker|containerd|crio)\.sock/*$|^/var/lib/(docker|containerd|kubelet)(/.*)?$`

loopback := {"127.0.0.1", "[::1]", "localhost"}

loopback_ip := {"127.0.0.1", "::1", "[::1]", "localhost"}

# disallow-latest-tag
deny contains msg if {
	some name, svc in input.services
	svc.image
	not image_pinned(svc.image)
	msg := sprintf("%s: [disallow-latest-tag] image %q needs an explicit tag other than latest", [name, svc.image])
}

image_pinned(image) if contains(image, "@sha256:")

image_pinned(image) if {
	parts := split(image, "/")
	last := parts[count(parts) - 1]
	tagged := split(last, ":")
	count(tagged) == 2
	tagged[1] != "latest"
}

# Interpolation: ${X:-default} becomes its default, any other ${...} cannot be proven safe.
resolve(text) := regex.replace(regex.replace(text, `\$\{[^}:]+:?-([^}]*)\}`, "$1"), `\$\{[^}]*\}`, "UNRESOLVED")

# loopback-only-ports, short syntax. "8000" and "8000:8000" publish on every interface.
deny contains msg if {
	some name, svc in input.services
	some port in svc.ports
	is_string(port)
	not short_port_loopback(port)
	msg := sprintf("%s: [loopback-only-ports] published port %q is not bound to loopback", [name, port])
}

short_port_loopback(port) if {
	text := regex.replace(resolve(port), `/[A-Za-z]+$`, "")
	bind_host(text) in loopback
}

# "[::1]:9090:9090": the bracketed address is the host
bind_host(text) := host if {
	m := regex.find_all_string_submatch_n(`^(\[[^\]]+\]):.+`, text, 1)
	count(m) == 1
	host := m[0][1]
}

# "ip:host:container" (exactly two colons, no brackets)
bind_host(text) := host if {
	not startswith(text, "[")
	parts := split(text, ":")
	count(parts) == 3
	host := parts[0]
}

# loopback-only-ports, long syntax: an entry without a loopback host_ip binds every interface
deny contains msg if {
	some name, svc in input.services
	some port in svc.ports
	is_object(port)
	not resolve(object.get(port, "host_ip", "")) in loopback_ip
	msg := sprintf("%s: [loopback-only-ports] published port %v is not bound to loopback", [name, object.get(port, "target", "?")])
}

# disallow-docker-sock
deny contains msg if {
	some name, svc in input.services
	some vol in svc.volumes
	source := volume_source(vol)
	regex.match(forbidden_host_path, source)
	msg := sprintf("%s: [disallow-docker-sock] mounts a runtime socket or node path (%s)", [name, source])
}

volume_source(vol) := split(vol, ":")[0] if is_string(vol)

volume_source(vol) := object.get(vol, "source", "") if is_object(vol)
