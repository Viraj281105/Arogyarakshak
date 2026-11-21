# Docker Compose policy (conftest / OPA): the compose-side rules of policy_checks.py.
#
#   conftest test --policy infrastructure/policy/rego --namespace arogya.compose docker-compose.yml
#
# Scope: image tags, loopback-only published ports and no Docker socket. Compose files here are
# local-development and demo stacks, so run-as-non-root, read-only root filesystem and resource
# limits are enforced for Kubernetes only (rego/workload.rego); see docs/operations/load-and-chaos.md.
# NOT EXECUTED here (no opa/conftest); structure is checked by the Python tests.
package arogya.compose

import rego.v1

docker_sockets := {"/var/run/docker.sock", "/run/docker.sock"}

loopback := {"127.0.0.1", "[::1]", "localhost"}

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

# loopback-only-ports: short syntax "HOST_IP:HOST:CONTAINER"
deny contains msg if {
	some name, svc in input.services
	some port in svc.ports
	is_string(port)
	parts := split(port, ":")
	count(parts) == 2
	msg := sprintf("%s: [loopback-only-ports] published port %q is not bound to 127.0.0.1", [name, port])
}

deny contains msg if {
	some name, svc in input.services
	some port in svc.ports
	is_string(port)
	parts := split(port, ":")
	count(parts) == 3
	not parts[0] in loopback
	msg := sprintf("%s: [loopback-only-ports] published port %q is not bound to 127.0.0.1", [name, port])
}

# loopback-only-ports: long syntax
deny contains msg if {
	some name, svc in input.services
	some port in svc.ports
	is_object(port)
	port.published
	not object.get(port, "host_ip", "") in loopback
	msg := sprintf("%s: [loopback-only-ports] published port %v is not bound to 127.0.0.1", [name, port.published])
}

# disallow-docker-sock
deny contains msg if {
	some name, svc in input.services
	some vol in svc.volumes
	source := volume_source(vol)
	source in docker_sockets
	msg := sprintf("%s: [disallow-docker-sock] mounts the Docker socket", [name])
}

volume_source(vol) := split(vol, ":")[0] if is_string(vol)

volume_source(vol) := vol.source if is_object(vol)
