import pytest

from schemesetu.trend_estimator import IncomeDataPoint, project_future_eligibility


def test_requires_at_least_two_data_points():
    with pytest.raises(ValueError):
        project_future_eligibility(
            income_history=[IncomeDataPoint(year=2024, annual_income=100000.0)],
            target_year=2026,
            location_state="Maharashtra",
        )


def test_zero_data_points_raises():
    with pytest.raises(ValueError):
        project_future_eligibility(income_history=[], target_year=2026, location_state="Maharashtra")


def test_flat_income_projects_the_same_value():
    history = [
        IncomeDataPoint(year=2022, annual_income=100000.0),
        IncomeDataPoint(year=2023, annual_income=100000.0),
        IncomeDataPoint(year=2024, annual_income=100000.0),
    ]
    result = project_future_eligibility(history, target_year=2026, location_state="Maharashtra")
    assert result.projected_income == 100000.0
    assert result.trend_slope_per_year == 0.0


def test_rising_income_trend_is_extrapolated_correctly():
    # Income rising by exactly 50,000/year.
    history = [
        IncomeDataPoint(year=2020, annual_income=100000.0),
        IncomeDataPoint(year=2021, annual_income=150000.0),
        IncomeDataPoint(year=2022, annual_income=200000.0),
    ]
    result = project_future_eligibility(history, target_year=2024, location_state="Maharashtra")
    assert result.trend_slope_per_year == 50000.0
    assert result.projected_income == 300000.0
    assert result.is_extrapolation is True


def test_target_year_within_range_is_not_extrapolation():
    history = [
        IncomeDataPoint(year=2020, annual_income=100000.0),
        IncomeDataPoint(year=2022, annual_income=200000.0),
    ]
    result = project_future_eligibility(history, target_year=2021, location_state="Maharashtra")
    assert result.is_extrapolation is False


def test_projected_eligibility_reflects_projected_income_not_raw_history():
    """The projected figure (not the raw last value) is what check_eligibility records —
    and, with no official income ceiling, a rising trend must not flip PMJAY to ineligible."""
    history = [
        IncomeDataPoint(year=2020, annual_income=100000.0),
        IncomeDataPoint(year=2021, annual_income=200000.0),
        IncomeDataPoint(year=2022, annual_income=300000.0),
    ]
    result = project_future_eligibility(history, target_year=2023, location_state="Maharashtra")
    assert result.projected_income == 400000.0
    pmjay = next(r for r in result.projected_eligibility if "PMJAY" in r.scheme_name)
    assert "Rs 4,00,000" in pmjay.reason
    assert pmjay.estimated_eligibility == "ambiguous"


def test_data_points_used_reflects_history_length():
    history = [
        IncomeDataPoint(year=2020, annual_income=100000.0),
        IncomeDataPoint(year=2021, annual_income=110000.0),
        IncomeDataPoint(year=2022, annual_income=120000.0),
        IncomeDataPoint(year=2023, annual_income=130000.0),
    ]
    result = project_future_eligibility(history, target_year=2025, location_state="Karnataka")
    assert result.data_points_used == 4


def test_projected_income_never_goes_negative():
    history = [
        IncomeDataPoint(year=2020, annual_income=100000.0),
        IncomeDataPoint(year=2021, annual_income=50000.0),
    ]
    # Steeply declining trend extrapolated far into the future would go negative.
    result = project_future_eligibility(history, target_year=2040, location_state="Maharashtra")
    assert result.projected_income >= 0.0
