from schemesetu.agent import EligibilityRequest
from schemesetu.reasoning_agent import reason_about_eligibility


def test_reasoning_trace_covers_pmjay_for_any_state():
    req = EligibilityRequest(income=120000.0, location_state="Karnataka", medical_need="Knee surgery")
    result = reason_about_eligibility(req)

    pmjay_steps = {s.criterion: s for s in result.reasoning_trace if s.scheme.startswith("PMJAY")}
    assert set(pmjay_steps) == {"beneficiary_identification", "annual_income"}

    identification = pmjay_steps["beneficiary_identification"]
    assert identification.determinative is True
    assert identification.satisfied is None  # not collected, so never assumed either way
    assert "70" in identification.threshold_or_rule

    income = pmjay_steps["annual_income"]
    assert income.determinative is False
    assert income.satisfied is None
    assert "2,50,000" not in income.threshold_or_rule


def test_mjpjay_income_criterion_only_applies_to_maharashtra():
    """MJPJAY's state_of_residence criterion is checked for every applicant (and fails
    for a non-Maharashtra resident); its income factor is only shown for Maharashtra,
    since schemesetu.agent never assesses MJPJAY otherwise."""
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

    mjpjay_steps = {s.criterion: s for s in result.reasoning_trace if s.scheme.startswith("MJPJAY")}
    assert set(mjpjay_steps) == {"state_of_residence", "annual_income"}
    assert mjpjay_steps["state_of_residence"].satisfied is True
    assert mjpjay_steps["annual_income"].determinative is False
    assert mjpjay_steps["annual_income"].satisfied is None


def test_reasoning_result_matches_check_eligibility_verdict():
    req = EligibilityRequest(income=500000.0, location_state="Maharashtra", medical_need="Knee surgery")
    result = reason_about_eligibility(req)

    verdicts = {r.scheme_name.split(" ")[0]: r.estimated_eligibility for r in result.scheme_results}
    assert verdicts == {"PMJAY": "ambiguous", "MJPJAY": "eligible"}

    # An ambiguous verdict has no satisfied/failed determinative step; an eligible one does.
    pmjay_decided = [s for s in result.reasoning_trace if s.scheme.startswith("PMJAY") and s.satisfied is not None]
    assert pmjay_decided == []
    mjpjay_state = next(s for s in result.reasoning_trace if s.criterion == "state_of_residence")
    assert mjpjay_state.satisfied is True


def test_criteria_disclosure_is_present():
    req = EligibilityRequest(income=100000.0, location_state="Maharashtra", medical_need="Knee surgery")
    result = reason_about_eligibility(req)
    assert result.criteria_considered == ["state_of_residence"]
    assert result.non_determinative_factors == ["annual_income"]
    assert "annual_income" not in result.criteria_considered
    assert "SECC-2011 deprivation/occupational listing or state-verified beneficiary database" in result.criteria_not_considered
    assert "medical_need" in result.criteria_not_considered
