"""Context-sufficiency rules for Kadi auto-triggering (#32)."""

from kadi.triggers import ContextSnapshot, checks_to_run, count_entity_types, evaluate_readiness


def _by_check(readiness):
    return {r.module_check: r for r in readiness}


def test_without_consent_nothing_is_ready():
    readiness = evaluate_readiness(ContextSnapshot(consent_opt_in=False, entity_counts={"billing_item": 5, "medicine": 2}))
    assert {r.status for r in readiness} == {"BLOCKED_NO_CONSENT"}
    assert checks_to_run(readiness) == []


def test_missing_context_is_named_exactly():
    readiness = _by_check(
        evaluate_readiness(ContextSnapshot(consent_opt_in=True, entity_counts=count_entity_types(["billing_item", "billing_item"])))
    )
    assert readiness["billnyay_audit"].status == "READY"
    assert readiness["dawacheck_benchmark"].missing_context == ["medicine"]
    assert readiness["billnyay_icd_audit"].missing_context == ["diagnosis", "procedure"]
    assert readiness["schemesetu_eligibility"].missing_context == ["diagnosis or procedure", "income_profile"]


def test_scheme_check_needs_both_medical_context_and_an_income_profile():
    snapshot = ContextSnapshot(consent_opt_in=True, entity_counts={"procedure": 1})
    assert _by_check(evaluate_readiness(snapshot))["schemesetu_eligibility"].missing_context == ["income_profile"]
    snapshot.has_income_profile = True
    assert _by_check(evaluate_readiness(snapshot))["schemesetu_eligibility"].status == "READY"


def test_daavisetu_claim_is_never_auto_run_even_when_ready():
    snapshot = ContextSnapshot(consent_opt_in=True, entity_counts={"hospital": 1, "diagnosis": 1})
    readiness = evaluate_readiness(snapshot)
    assert _by_check(readiness)["daavisetu_claim"].status == "READY"
    assert "daavisetu_claim" not in checks_to_run(readiness)


def test_only_restricts_which_ready_checks_run():
    snapshot = ContextSnapshot(
        consent_opt_in=True,
        entity_counts={"billing_item": 1, "medicine": 1, "diagnosis": 1, "procedure": 1},
        has_income_profile=True,
    )
    readiness = evaluate_readiness(snapshot)
    assert checks_to_run(readiness) == ["billnyay_audit", "billnyay_icd_audit", "dawacheck_benchmark", "schemesetu_eligibility"]
    assert checks_to_run(readiness, only=["schemesetu_eligibility"]) == ["schemesetu_eligibility"]
