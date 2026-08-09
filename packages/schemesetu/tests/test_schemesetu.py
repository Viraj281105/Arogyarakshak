import pytest
from schemesetu.agent import check_eligibility, EligibilityRequest


def test_check_eligibility_eligible():
    req = EligibilityRequest(
        income=120000.0,
        location_state="Maharashtra",
        category="General",
        medical_need="Coronary artery bypass graft (CABG)",
    )
    results = check_eligibility(req)
    
    assert len(results) > 0
    pmjay = next(r for r in results if "PMJAY" in r.scheme_name)
    mjpjay = next(r for r in results if "MJPJAY" in r.scheme_name)
    
    assert pmjay.estimated_eligibility == "eligible"
    assert mjpjay.estimated_eligibility == "eligible"


def test_check_eligibility_ineligible():
    req = EligibilityRequest(
        income=500000.0,
        location_state="Karnataka",
        category="General",
        medical_need="Knee replacement",
    )
    results = check_eligibility(req)
    
    assert len(results) > 0
    pmjay = next(r for r in results if "PMJAY" in r.scheme_name)
    assert pmjay.estimated_eligibility == "ineligible"
