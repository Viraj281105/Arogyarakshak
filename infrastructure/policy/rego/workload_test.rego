# Unit tests for workload.rego and compose.rego. Run: opa test infrastructure/policy/rego
# NOT EXECUTED in this repository (no opa binary); written against the documented opa test format.
package arogya.workload_test

import rego.v1

import data.arogya.compose
import data.arogya.workload

good_deployment := {
	"kind": "Deployment",
	"metadata": {"name": "api"},
	"spec": {"template": {"spec": {
		"securityContext": {"runAsNonRoot": true},
		"containers": [{
			"name": "api",
			"image": "arogyarakshak-api:1.0.0",
			"resources": {"limits": {"cpu": "1", "memory": "1Gi"}},
			"securityContext": {"readOnlyRootFilesystem": true},
		}],
	}}},
}

test_good_deployment_is_allowed if {
	count(workload.deny) == 0 with input as good_deployment
}

test_latest_tag_is_denied if {
	bad := json.patch(good_deployment, [{"op": "replace", "path": "/spec/template/spec/containers/0/image", "value": "x:latest"}])
	count(workload.deny) > 0 with input as bad
}

test_missing_tag_is_denied if {
	bad := json.patch(good_deployment, [{"op": "replace", "path": "/spec/template/spec/containers/0/image", "value": "x"}])
	count(workload.deny) > 0 with input as bad
}

test_root_pod_is_denied if {
	bad := json.patch(good_deployment, [{"op": "replace", "path": "/spec/template/spec/securityContext/runAsNonRoot", "value": false}])
	count(workload.deny) > 0 with input as bad
}

test_writable_root_fs_is_denied if {
	bad := json.patch(good_deployment, [{"op": "replace", "path": "/spec/template/spec/containers/0/securityContext/readOnlyRootFilesystem", "value": false}])
	count(workload.deny) > 0 with input as bad
}

test_missing_limits_is_denied if {
	bad := json.patch(good_deployment, [{"op": "remove", "path": "/spec/template/spec/containers/0/resources/limits/memory"}])
	count(workload.deny) > 0 with input as bad
}

test_docker_socket_is_denied if {
	bad := json.patch(good_deployment, [{"op": "add", "path": "/spec/template/spec/volumes", "value": [{"name": "d", "hostPath": {"path": "/var/run/docker.sock"}}]}])
	count(workload.deny) > 0 with input as bad
}

test_host_port_is_denied if {
	bad := json.patch(good_deployment, [{"op": "add", "path": "/spec/template/spec/containers/0/ports", "value": [{"containerPort": 8000, "hostPort": 8000}]}])
	count(workload.deny) > 0 with input as bad
}

test_compose_loopback_port_is_allowed if {
	count(compose.deny) == 0 with input as {"services": {"p": {"image": "prom/prometheus:v3.5.0", "ports": ["127.0.0.1:9090:9090"]}}}
}

test_compose_public_port_is_denied if {
	count(compose.deny) > 0 with input as {"services": {"p": {"image": "prom/prometheus:v3.5.0", "ports": ["9090:9090"]}}}
}

test_compose_docker_socket_is_denied if {
	count(compose.deny) > 0 with input as {"services": {"p": {"image": "x:1", "volumes": ["/var/run/docker.sock:/var/run/docker.sock"]}}}
}

test_compose_latest_is_denied if {
	count(compose.deny) > 0 with input as {"services": {"p": {"image": "x:latest"}}}
}
