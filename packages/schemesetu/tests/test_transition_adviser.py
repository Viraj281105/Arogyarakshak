from schemesetu.agent import EligibilityRequest
from schemesetu.transition_adviser import advise_transition


def test_no_transition_when_eligibility_unchanged():
    req = EligibilityRequest(income=100000.0, location_state="Maharashtra", medical_need="Surgery")
    advice = advise_transition(req, req)
    assert advice.transition_detected is False
    assert advice.checklist == []


def test_relocating_out_of_maharashtra_loses_mjpjay():
    previous = EligibilityRequest(income=100000.0, location_state="Maharashtra", medical_need="Surgery")
    current = EligibilityRequest(income=100000.0, location_state="Karnataka", medical_need="Surgery")

    advice = advise_transition(previous, current)
    assert advice.transition_detected is True
    assert "Lost eligibility: MJPJAY" in advice.note
    assert any("ration card" in step.lower() for step in advice.checklist)


def test_relocating_into_maharashtra_gains_mjpjay():
    previous = EligibilityRequest(income=100000.0, location_state="Karnataka", medical_need="Surgery")
    current = EligibilityRequest(income=100000.0, location_state="Maharashtra", medical_need="Surgery")

    advice = advise_transition(previous, current)
    assert advice.transition_detected is True
    assert "Gained eligibility: MJPJAY" in advice.note
    assert any("mjpjay" in step.lower() for step in advice.checklist)


def test_income_rise_losing_pmjay_eligibility():
    previous = EligibilityRequest(income=200000.0, location_state="Karnataka", medical_need="Surgery")
    current = EligibilityRequest(income=500000.0, location_state="Karnataka", medical_need="Surgery")

    advice = advise_transition(previous, current)
    assert advice.transition_detected is True
    assert "Lost eligibility: PMJAY" in advice.note


def test_from_and_to_scheme_labels_reflect_eligible_sets():
    previous = EligibilityRequest(income=100000.0, location_state="Maharashtra", medical_need="Surgery")
    current = EligibilityRequest(income=500000.0, location_state="Karnataka", medical_need="Surgery")

    advice = advise_transition(previous, current)
    assert "MJPJAY" in advice.from_schemes
    assert advice.to_schemes == "None"
