"""
SchemeSetu — Eligibility Trend Estimator (#70).

Projects a family's income from data points the caller actually supplies (e.g. declared
income over the last few years) using ordinary least-squares linear regression, and runs
`schemesetu.agent.check_eligibility` on the projected figure.

Neither PMJAY nor MJPJAY defines an annual income ceiling in the official sources cited in
`schemesetu.thresholds`, so income is non-determinative: the projected income is reported
in each result's reason but cannot change a verdict. Only the state of residence can.

ArogyaRakshak has no real historical demographic dataset to draw from — no SECC-2011
microdata, no scheme-enrolment trend data, nothing wired into any code path (see
docs/architecture/components.md) — so this never invents one. It only fits a trend
line to data the caller provides; it cannot be called with zero data points.
"""

from typing import List, Tuple
from pydantic import BaseModel, Field

from schemesetu.agent import EligibilityRequest, SchemeResult, check_eligibility


class IncomeDataPoint(BaseModel):
    year: int = Field(..., description="Calendar year this income figure applies to")
    annual_income: float = Field(..., ge=0)


class EligibilityTrendResult(BaseModel):
    target_year: int
    projected_income: float
    trend_slope_per_year: float
    data_points_used: int
    projected_eligibility: List[SchemeResult]
    is_extrapolation: bool = Field(
        ...,
        description="True when target_year falls outside the supplied data's year "
        "range — an extrapolation, not an interpolation, and should be treated with "
        "lower confidence than a target year within the supplied range.",
    )


def _linear_regression(points: List[Tuple[float, float]]) -> Tuple[float, float]:
    """Ordinary least squares. Returns (slope, intercept)."""
    n = len(points)
    sum_x = sum(p[0] for p in points)
    sum_y = sum(p[1] for p in points)
    sum_xy = sum(p[0] * p[1] for p in points)
    sum_x2 = sum(p[0] ** 2 for p in points)

    denom = n * sum_x2 - sum_x ** 2
    if denom == 0:
        # All years identical — no trend can be computed; treat as flat at the mean.
        return 0.0, sum_y / n
    slope = (n * sum_xy - sum_x * sum_y) / denom
    intercept = (sum_y - slope * sum_x) / n
    return slope, intercept


def project_future_eligibility(
    income_history: List[IncomeDataPoint],
    target_year: int,
    location_state: str,
    category: str = "General",
    medical_need: str = "Not specified",
) -> EligibilityTrendResult:
    """Projects income at `target_year` via linear trend and runs the eligibility
    rules on it (income is recorded there, never decisive).

    Requires at least 2 historical data points — a single point has no trend to
    project, and zero points would mean inventing one.
    """
    if len(income_history) < 2:
        raise ValueError(
            f"At least 2 income data points are required to compute a trend; got {len(income_history)}."
        )

    points = [(float(p.year), p.annual_income) for p in income_history]
    slope, intercept = _linear_regression(points)
    projected_income = max(0.0, slope * target_year + intercept)

    years = [p.year for p in income_history]
    is_extrapolation = target_year < min(years) or target_year > max(years)

    eligibility = check_eligibility(
        EligibilityRequest(
            income=projected_income,
            location_state=location_state,
            category=category,
            medical_need=medical_need,
        )
    )

    return EligibilityTrendResult(
        target_year=target_year,
        projected_income=round(projected_income, 2),
        trend_slope_per_year=round(slope, 2),
        data_points_used=len(income_history),
        projected_eligibility=eligibility,
        is_extrapolation=is_extrapolation,
    )
