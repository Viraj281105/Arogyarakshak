"""
IRDAI appeal outcome estimation (#90) — evidence first, or no number at all.

Given a dispute category and forum, the estimator returns the empirical share of decided
historical disputes in that category that were allowed or partially allowed, with a Wilson
95% interval and the dataset's citation. It refuses to return any probability when:

- no historical dataset is loaded (the situation today)    -> INSUFFICIENT_EVIDENCE
- fewer than ``min_samples`` decided disputes match        -> INSUFFICIENT_EVIDENCE
- the dataset is synthetic (outside evaluation code)       -> SYNTHETIC_DATA_REFUSED

It is deterministic and deliberately simple: a historical base rate for similar disputes,
not a per-case prediction, and not an LLM judgement. Withdrawn or settled disputes are
excluded because their result for the complainant is unknown; the count is disclosed.

Procedural admissibility (for example whether a complaint is within the Insurance
Ombudsman's time limits) is reported as UNEVALUATED: the repository cites no Insurance
Ombudsman Rules provisions, and unverified legal thresholds are not added here.
"""

import math
from typing import List, Literal, Optional, Tuple

from pydantic import BaseModel, Field

from billnyay.outcome.dataset import (
    FAVOURABLE_OUTCOMES,
    UNKNOWN_RESULT_OUTCOMES,
    DatasetProvenance,
    DisputeOutcomeDataset,
    Forum,
)

MIN_SAMPLES = 30

EstimateStatus = Literal["ESTIMATED", "INSUFFICIENT_EVIDENCE", "SYNTHETIC_DATA_REFUSED"]

NOT_A_PREDICTION = "A historical base rate for similar disputes, not a prediction for this specific case."


class OutcomeQuery(BaseModel):
    dispute_category: str = Field(..., min_length=1, max_length=64)
    forum: Forum = "insurance_ombudsman"


class OutcomeEstimate(BaseModel):
    status: EstimateStatus
    dispute_category: str
    forum: str
    probability_favourable: Optional[float] = None
    interval_95: Optional[Tuple[float, float]] = None
    sample_size: int = 0
    excluded_withdrawn_or_settled: int = 0
    basis: str
    dataset_name: Optional[str] = None
    dataset_citation: Optional[DatasetProvenance] = None
    admissibility_checks: Literal["UNEVALUATED"] = "UNEVALUATED"
    caveats: List[str] = Field(default_factory=list)


def wilson_interval(successes: int, n: int, z: float = 1.96) -> Tuple[float, float]:
    if n <= 0:
        raise ValueError("n must be positive")
    p = successes / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return round(max(0.0, centre - margin), 4), round(min(1.0, centre + margin), 4)


def _normalize_category(category: str) -> str:
    return " ".join(category.strip().lower().replace("-", "_").split())


def estimate_outcome(
    query: OutcomeQuery,
    dataset: Optional[DisputeOutcomeDataset],
    *,
    min_samples: int = MIN_SAMPLES,
    allow_synthetic: bool = False,
) -> OutcomeEstimate:
    base = {"dispute_category": query.dispute_category, "forum": query.forum}

    if dataset is None:
        return OutcomeEstimate(
            status="INSUFFICIENT_EVIDENCE",
            basis=(
                "No historical IRDAI / Insurance Ombudsman dispute-outcome dataset is loaded, "
                "so no outcome probability can be established."
            ),
            caveats=[NOT_A_PREDICTION],
            **base,
        )

    if dataset.is_synthetic and not allow_synthetic:
        return OutcomeEstimate(
            status="SYNTHETIC_DATA_REFUSED",
            basis="The loaded dataset is synthetic; synthetic outcomes are never presented as evidence.",
            dataset_name=dataset.name,
            caveats=[NOT_A_PREDICTION],
            **base,
        )

    wanted = _normalize_category(query.dispute_category)
    matching = [
        r for r in dataset.records
        if _normalize_category(r.dispute_category) == wanted and r.forum == query.forum
    ]
    decided = [r for r in matching if r.outcome not in UNKNOWN_RESULT_OUTCOMES]
    excluded = len(matching) - len(decided)

    caveats = [NOT_A_PREDICTION]
    if excluded:
        caveats.append(f"{excluded} withdrawn or settled disputes were excluded because their result is unknown.")
    if dataset.is_synthetic:
        caveats.append("SYNTHETIC DATA: evaluation only, not valid for real decisions.")

    if len(decided) < min_samples:
        return OutcomeEstimate(
            status="INSUFFICIENT_EVIDENCE",
            sample_size=len(decided),
            excluded_withdrawn_or_settled=excluded,
            basis=(
                f"Only {len(decided)} decided disputes match this category and forum "
                f"(at least {min_samples} are required)."
            ),
            dataset_name=dataset.name,
            dataset_citation=dataset.provenance,
            caveats=caveats,
            **base,
        )

    favourable = sum(1 for r in decided if r.outcome in FAVOURABLE_OUTCOMES)
    return OutcomeEstimate(
        status="ESTIMATED",
        probability_favourable=round(favourable / len(decided), 4),
        interval_95=wilson_interval(favourable, len(decided)),
        sample_size=len(decided),
        excluded_withdrawn_or_settled=excluded,
        basis=(
            f"Share of {len(decided)} decided {query.forum} disputes in category "
            f"'{query.dispute_category}' that were allowed or partially allowed."
        ),
        dataset_name=dataset.name,
        dataset_citation=dataset.provenance,
        caveats=caveats,
        **base,
    )
