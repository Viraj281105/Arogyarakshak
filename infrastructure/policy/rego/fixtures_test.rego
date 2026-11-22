# Runs the SHARED fixture corpus (infrastructure/policy/fixtures/{good,bad}) through both Rego
# packages. The Python reference implementation and the generated `kyverno test` set read the
# same files, so the three engines are held to the same verdicts.
#
#   python infrastructure/policy/build_opa_data.py --out /tmp/opa-fixtures.json
#   opa test infrastructure/policy/rego /tmp/opa-fixtures.json -v
#
# (do NOT pass the fixtures directory: OPA merges every data file into one root and the fixtures'
# top-level keys collide. build_opa_data.py mounts each file as data.good.<name> / data.bad.<name>.
# Verified against the official openpolicyagent/opa image: 3/3 pass over 14 good and 35 bad fixtures.)
# Executed once against the official OPA image (see above); not part of the local pytest run.
package arogya.fixtures_test

import rego.v1

import data.arogya.compose
import data.arogya.workload

denied(c) := msgs if {
	c.kind == "k8s"
	msgs := workload.deny with input as c.object
}

denied(c) := msgs if {
	c.kind == "compose"
	msgs := compose.deny with input as c.object
}

test_fixture_corpus_is_loaded if {
	count(data.good) >= 10
	count(data.bad) >= 30
}

test_every_good_fixture_is_allowed if {
	every _, c in data.good {
		count(denied(c)) == 0
	}
}

# A bad fixture is a single-defect variant of a good one: it must be denied, and only for the rule
# named in its `rule` field.
test_every_bad_fixture_violates_exactly_its_rule if {
	every _, c in data.bad {
		count(denied(c)) > 0
		tag := sprintf("[%s]", [c.rule])
		every m in denied(c) {
			contains(m, tag)
		}
	}
}
