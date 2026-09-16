import pytest
from schemesetu.agent import check_eligibility, EligibilityRequest


def test_check_eligibility_maharashtra_resident():
    req = EligibilityRequest(
        income=120000.0,
        location_state="Maharashtra",
        category="General",
        medical_need="Coronary artery bypass graft (CABG)",
    )
    results = check_eligibility(req)

    assert len(results) == 2
    pmjay = next(r for r in results if "PMJAY" in r.scheme_name)
    mjpjay = next(r for r in results if "MJPJAY" in r.scheme_name)

    # PM-JAY rests on SECC-2011 listing, ASHA/AWW/AWH status or age 70+, none collected.
    assert pmjay.estimated_eligibility == "ambiguous"
    # MJPJAY covers all families in Maharashtra (GR dated 28 July 2023).
    assert mjpjay.estimated_eligibility == "eligible"
    assert all(r.is_provisional for r in results)


def test_high_income_is_not_reported_as_ineligible():
    """No official income ceiling exists, so a high income must not produce "ineligible"."""
    req = EligibilityRequest(
        income=500000.0,
        location_state="Karnataka",
        category="General",
        medical_need="Knee replacement",
    )
    results = check_eligibility(req)

    assert [r.scheme_name.split(" ")[0] for r in results] == ["PMJAY"]
    pmjay = results[0]
    assert pmjay.estimated_eligibility == "ambiguous"
    assert "annual_income" in pmjay.non_determinative_factors
    assert "annual_income" not in pmjay.criteria_evaluated
