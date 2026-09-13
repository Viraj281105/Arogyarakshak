from schemesetu.agent import EligibilityRequest
from schemesetu.reasoning_agent import reason_about_eligibility


def test_reasoning_trace_covers_pmjay_for_any_state():
    req = EligibilityRequest(income=120000.0, location_state="Karnataka", medical_need="Knee surgery")
    result = reason_about_eligibility(req)

    pmjay_steps = [s for s in result.reasoning_trace if s.scheme.startswith("PMJAY")]
    assert len(pmjay_steps) == 1
    assert pmjay_steps[0].satisfied is True
    assert "2,50,000" in pmjay_steps[0].threshold_or_rule


def test_mjpjay_income_criterion_only_applies_to_maharashtra():
    """MJPJAY's state_of_residence criterion is checked for every applicant (and fails
    for a non-Maharashtra resident); only its *income* criterion is Maharashtra-gated,
    since schemesetu.agent never evaluates a Maharashtra income threshold otherwise."""
    req = EligibilityRequest(income=120000.0, location_state="Karnataka", medical_need="Knee surgery")
    result = reason_about_eligibility(req)

    mjpjay_steps = [s for s in result.reasoning_trace if s.scheme.startswith("MJPJAY")]
    assert len(mjpjay_steps) == 1
    assert mjpjay_steps[0].criterion == "state_of_residence"
    assert mjpjay_steps[0].satisfied is False
    assert not any(s.criterion == "annual_income" for s in mjpjay_steps)


def test_mjpjay_steps_present_for_maharashtra():
    req = EligibilityRequest(income=100000.0, location_state="Maharashtra", medical_need="Knee surgery")
    result = reason_about_eligibility(req)

    mjpjay_steps = [s for s in result.reasoning_trace if s.scheme.startswith("MJPJAY")]
    assert len(mjpjay_steps) == 2  # state_of_residence + annual_income
    assert all(s.satisfied for s in mjpjay_steps)


def test_reasoning_result_matches_check_eligibility_verdict():
    req = EligibilityRequest(income=500000.0, location_state="Maharashtra", medical_need="Knee surgery")
    result = reason_about_eligibility(req)

    pmjay = next(r for r in result.scheme_results if "PMJAY" in r.scheme_name)
    assert pmjay.estimated_eligibility == "ineligible"
    pmjay_step = next(s for s in result.reasoning_trace if s.scheme.startswith("PMJAY"))
    assert pmjay_step.satisfied is False


def test_criteria_disclosure_is_present():
    req = EligibilityRequest(income=100000.0, location_state="Maharashtra", medical_need="Knee surgery")
    result = reason_about_eligibility(req)
    assert "annual_income" in result.criteria_considered
    assert len(result.criteria_not_considered) > 0
