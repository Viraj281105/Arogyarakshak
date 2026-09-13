"""Consent-bounded scheme recommendation trigger (#92) and the shared thresholds it uses."""

import math

import pytest
from pydantic import ValidationError

from schemesetu.agent import EligibilityRequest, check_eligibility
from schemesetu.reasoning_agent import reason_about_eligibility
from schemesetu.thresholds import MJPJAY, PMJAY, SCHEME_INCOME_CRITERIA, format_inr
from schemesetu.triggers import IncomeProfile, evaluate_income_trigger


def _request(income, state="Karnataka"):
    return EligibilityRequest(income=income, location_state=state, medical_need="Appendectomy")


def test_rule_engine_reads_the_shared_thresholds_at_the_boundary():
    at = {r.scheme_name: r.estimated_eligibility for r in check_eligibility(_request(PMJAY.max_annual_income_inr))}
    above = {r.scheme_name: r.estimated_eligibility for r in check_eligibility(_request(PMJAY.max_annual_income_inr + 1))}
    assert at[PMJAY.scheme_name] == "eligible"
    assert above[PMJAY.scheme_name] == "ineligible"

    mh = {r.scheme_name: r.estimated_eligibility for r in check_eligibility(_request(MJPJAY.max_annual_income_inr, "MH"))}
    assert mh[MJPJAY.scheme_name] == "eligible"


def test_reasoning_trace_renders_thresholds_from_the_same_source():
    trace = reason_about_eligibility(_request(100000, "Maharashtra")).reasoning_trace
    rules = {step.scheme: step.threshold_or_rule for step in trace if step.criterion == "annual_income"}
    assert rules[PMJAY.scheme_name] == "Annual family income <= Rs 2,50,000"
    assert rules[MJPJAY.scheme_name] == "Annual family income <= Rs 1,50,000"


def test_every_threshold_declares_unverified_provenance():
    assert all(c.provenance == "UNVERIFIED_PROJECT_HEURISTIC" for c in SCHEME_INCOME_CRITERIA)


def test_format_inr_uses_indian_grouping():
    assert format_inr(250000) == "2,50,000"
    assert format_inr(12500000) == "1,25,00,000"
    assert format_inr(999) == "999"


def test_missing_profile_never_fires():
    decision = evaluate_income_trigger(None)
    assert decision.status == "INSUFFICIENT_EVIDENCE"
    assert decision.schemes_within_threshold == []


def test_first_profile_within_thresholds_fires_for_each_applicable_scheme():
    decision = evaluate_income_trigger(IncomeProfile(annual_income_inr=120000, state="Maharashtra"))
    assert decision.status == "FIRE"
    assert [m.short_name for m in decision.newly_within_threshold] == ["PMJAY", "MJPJAY"]
    assert decision.threshold_provenance == "UNVERIFIED_PROJECT_HEURISTIC"


def test_state_scheme_does_not_apply_outside_its_state():
    decision = evaluate_income_trigger(IncomeProfile(annual_income_inr=120000, state="Karnataka"))
    assert [m.short_name for m in decision.newly_within_threshold] == ["PMJAY"]


def test_income_above_every_threshold_does_not_fire():
    decision = evaluate_income_trigger(IncomeProfile(annual_income_inr=300000, state="Maharashtra"))
    assert decision.status == "NO_THRESHOLD_CROSSED"


def test_income_dropping_below_a_threshold_fires_only_for_the_new_scheme():
    previous = IncomeProfile(annual_income_inr=200000, state="Maharashtra")  # PMJAY only
    current = IncomeProfile(annual_income_inr=140000, state="Maharashtra")   # PMJAY + MJPJAY
    decision = evaluate_income_trigger(current, previous)
    assert decision.status == "FIRE"
    assert [m.short_name for m in decision.newly_within_threshold] == ["MJPJAY"]


def test_unchanged_thresholds_do_not_refire():
    previous = IncomeProfile(annual_income_inr=120000, state="MH")
    current = IncomeProfile(annual_income_inr=110000, state="Maharashtra")
    assert evaluate_income_trigger(current, previous).status == "NO_THRESHOLD_CROSSED"


def test_moving_into_a_scheme_state_fires():
    previous = IncomeProfile(annual_income_inr=120000, state="Karnataka")
    current = IncomeProfile(annual_income_inr=120000, state="Maharashtra")
    decision = evaluate_income_trigger(current, previous)
    assert [m.short_name for m in decision.newly_within_threshold] == ["MJPJAY"]


@pytest.mark.parametrize("income", [-1, math.nan, math.inf])
def test_invalid_income_is_rejected(income):
    with pytest.raises(ValidationError):
        IncomeProfile(annual_income_inr=income, state="Maharashtra")
