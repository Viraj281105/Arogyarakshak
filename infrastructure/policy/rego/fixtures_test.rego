# Runs the SHARED fixture corpus (infrastructure/policy/fixtures/{good,bad}) through both Rego
# packages. The Python reference implementation and the generated `kyverno test` set read the
# same files, so the three engines are held to the same verdicts.
#
#   opa test infrastructure/policy/rego infrastructure/policy/fixtures
#
# (the fixtures directory must be loaded too: its files become data.good.<name> and data.bad.<name>)
# NOT EXECUTED in this repository (no opa binary); written against the documented opa test format.
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
