"""Consent-bounded scheme recommendation trigger (#92) and the shared scheme criteria it uses."""

import math

import pytest
from pydantic import ValidationError

from schemesetu.agent import EligibilityRequest, check_eligibility
from schemesetu.reasoning_agent import reason_about_eligibility
from schemesetu.thresholds import MJPJAY, PMJAY, SCHEME_CRITERIA, format_inr
from schemesetu.triggers import IncomeProfile, evaluate_income_trigger


def _request(income, state="Karnataka"):
    return EligibilityRequest(income=income, location_state=state, medical_need="Appendectomy")


def _verdicts(income, state):
    return {r.scheme_name: r.estimated_eligibility for r in check_eligibility(_request(income, state))}


# --- Criteria provenance ---------------------------------------------------------

def test_no_scheme_defines_an_income_ceiling():
    """The unverified Rs 2.5L / Rs 1.5L heuristics must not come back as eligibility rules."""
    for criteria in SCHEME_CRITERIA:
        assert criteria.income_role == "NON_DETERMINATIVE"
        assert not hasattr(criteria, "max_annual_income_inr")


def test_every_scheme_cites_official_government_sources():
    for criteria in SCHEME_CRITERIA:
        assert criteria.provenance in {"OFFICIAL_SOURCE_CITED", "OFFICIAL_RESTATEMENT_CITED"}
        assert criteria.citations
        for citation in criteria.citations:
            assert citation.url.startswith("https://")
            assert citation.url.split("/")[2].endswith(".gov.in")
            assert citation.document and citation.publisher and citation.supports
            assert citation.retrieved_on == "2026-09-13"


def test_mjpjay_discloses_that_the_gr_text_was_not_retrieved():
    assert MJPJAY.provenance == "OFFICIAL_RESTATEMENT_CITED"
    assert any("28 July 2023" in gap for gap in MJPJAY.verification_gaps)


# --- Income is non-determinative ---------------------------------------------------

@pytest.mark.parametrize("state", ["Maharashtra", "Karnataka"])
def test_income_never_changes_the_verdict(state):
    baseline = _verdicts(0, state)
    for income in (100000, 150000, 150001, 250000, 250001, 5_000_000):
        assert _verdicts(income, state) == baseline


@pytest.mark.parametrize("income", [0, 120000, 500000])
def test_pmjay_is_reported_as_needing_verification_at_any_income(income):
    pmjay = next(r for r in check_eligibility(_request(income)) if r.scheme_name == PMJAY.scheme_name)
    assert pmjay.estimated_eligibility == "ambiguous"
    assert pmjay.criteria_evaluated == []
    assert pmjay.non_determinative_factors == ["annual_income"]
    assert "age 70 or above (eligible irrespective of income)" in pmjay.criteria_not_evaluated
    assert pmjay.claim_guide_steps, "an ambiguous result must say how to verify"
    assert pmjay.is_provisional is True


def test_mjpjay_follows_state_of_residence_only():
    for state in ("Maharashtra", "MH", " mh "):
        mjpjay = next(r for r in check_eligibility(_request(5_000_000, state)) if r.scheme_name == MJPJAY.scheme_name)
        assert mjpjay.estimated_eligibility == "eligible"
        assert mjpjay.criteria_evaluated == ["state_of_residence"]
        assert mjpjay.is_provisional is True
    assert MJPJAY.scheme_name not in _verdicts(10000, "Karnataka")


def test_results_carry_the_citations_they_rely_on():
    for result in check_eligibility(_request(120000, "Maharashtra")):
        criteria = PMJAY if result.scheme_name == PMJAY.scheme_name else MJPJAY
        assert result.criteria_provenance == criteria.provenance
        assert [s.url for s in result.sources] == [c.url for c in criteria.citations]
        assert "Rs 1,20,000" in result.reason and "does not decide eligibility" in result.reason


def test_reasoning_trace_marks_income_as_non_determinative():
    trace = reason_about_eligibility(_request(100000, "Maharashtra")).reasoning_trace
    income_steps = [step for step in trace if step.criterion == "annual_income"]
    assert {step.scheme for step in income_steps} == {PMJAY.scheme_name, MJPJAY.scheme_name}
    for step in income_steps:
        assert step.determinative is False
        assert step.satisfied is None
        assert step.threshold_or_rule.startswith("No income ceiling")
        assert step.applicant_value == "Rs 1,00,000"


def test_format_inr_uses_indian_grouping():
    assert format_inr(250000) == "2,50,000"
    assert format_inr(12500000) == "1,25,00,000"
    assert format_inr(999) == "999"


# --- Trigger ------------------------------------------------------------------------

def test_missing_profile_never_fires():
    decision = evaluate_income_trigger(None)
    assert decision.status == "INSUFFICIENT_EVIDENCE"
    assert decision.schemes_applicable == []


def test_first_profile_fires_for_each_applicable_scheme():
    decision = evaluate_income_trigger(IncomeProfile(annual_income_inr=120000, state="Maharashtra"))
    assert decision.status == "FIRE"
    assert [m.short_name for m in decision.newly_applicable] == ["PMJAY", "MJPJAY"]
    assert decision.income_role == "NON_DETERMINATIVE"
    assert [m.provenance for m in decision.newly_applicable] == [PMJAY.provenance, MJPJAY.provenance]


def test_high_income_does_not_suppress_the_first_run():
    """Regression: Rs 3,00,000 used to be 'above every threshold' and never triggered a run."""
    decision = evaluate_income_trigger(IncomeProfile(annual_income_inr=300000, state="Maharashtra"))
    assert decision.status == "FIRE"
    assert [m.short_name for m in decision.newly_applicable] == ["PMJAY", "MJPJAY"]


def test_state_scheme_does_not_apply_outside_its_state():
    decision = evaluate_income_trigger(IncomeProfile(annual_income_inr=120000, state="Karnataka"))
    assert [m.short_name for m in decision.newly_applicable] == ["PMJAY"]


@pytest.mark.parametrize("before, after", [(200000, 140000), (90000, 900000), (300000, 0)])
def test_income_change_alone_never_fires(before, after):
    previous = IncomeProfile(annual_income_inr=before, state="Maharashtra")
    current = IncomeProfile(annual_income_inr=after, state="Maharashtra")
    decision = evaluate_income_trigger(current, previous)
    assert decision.status == "NO_CHANGE"
    assert decision.newly_applicable == []


def test_state_alias_is_not_a_change():
    previous = IncomeProfile(annual_income_inr=120000, state="MH")
    current = IncomeProfile(annual_income_inr=110000, state="Maharashtra")
    assert evaluate_income_trigger(current, previous).status == "NO_CHANGE"


def test_moving_into_a_scheme_state_fires():
    previous = IncomeProfile(annual_income_inr=120000, state="Karnataka")
    current = IncomeProfile(annual_income_inr=120000, state="Maharashtra")
    decision = evaluate_income_trigger(current, previous)
    assert decision.status == "FIRE"
    assert [m.short_name for m in decision.newly_applicable] == ["MJPJAY"]


@pytest.mark.parametrize("income", [-1, math.nan, math.inf])
def test_invalid_income_is_rejected(income):
    with pytest.raises(ValidationError):
        IncomeProfile(annual_income_inr=income, state="Maharashtra")
