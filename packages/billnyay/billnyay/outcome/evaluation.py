"""
Evaluation harness for the outcome estimator (#90), ready for when a real dataset exists.

    dataset -> train (decision_year < cutoff) / test (>= cutoff)
            -> estimate each test dispute from the training years only
            -> Brier score, log loss, base-rate Brier, reliability bins, interval coverage

A temporal hold-out is used because the estimator will always be applied to disputes
decided after its data was collected. Metrics computed on a synthetic dataset are labelled
as such in the result and mean nothing about real-world accuracy.
"""

import math
from typing import Dict, List, Optional, Sequence

from pydantic import BaseModel

from billnyay.outcome.dataset import FAVOURABLE_OUTCOMES, UNKNOWN_RESULT_OUTCOMES, DisputeOutcomeDataset
from billnyay.outcome.estimator import MIN_SAMPLES, OutcomeQuery, estimate_outcome


class ReliabilityBin(BaseModel):
    lower: float
    upper: float
    count: int
    mean_predicted: Optional[float]
    observed_rate: Optional[float]


class EstimatorEvaluation(BaseModel):
    dataset_name: str
    synthetic: bool
    test_from_year: int
    test_disputes: int
    estimated: int
    refused_insufficient_evidence: int
    brier_score: Optional[float]
    base_rate_brier_score: Optional[float]
    log_loss: Optional[float]
    reliability: List[ReliabilityBin]
    interval_coverage: Optional[float]


def brier_score(predictions: Sequence[float], outcomes: Sequence[bool]) -> float:
    if not predictions or len(predictions) != len(outcomes):
        raise ValueError("predictions and outcomes must be non-empty and the same length")
    return round(sum((p - float(o)) ** 2 for p, o in zip(predictions, outcomes)) / len(predictions), 6)


def log_loss(predictions: Sequence[float], outcomes: Sequence[bool], eps: float = 1e-12) -> float:
    if not predictions or len(predictions) != len(outcomes):
        raise ValueError("predictions and outcomes must be non-empty and the same length")
    total = 0.0
    for p, o in zip(predictions, outcomes):
        p = min(max(p, eps), 1 - eps)
        total += -(math.log(p) if o else math.log(1 - p))
    return round(total / len(predictions), 6)


def reliability_bins(predictions: Sequence[float], outcomes: Sequence[bool], bins: int = 5) -> List[ReliabilityBin]:
    result = []
    for i in range(bins):
        lower, upper = i / bins, (i + 1) / bins
        members = [
            (p, o) for p, o in zip(predictions, outcomes)
            if lower <= p < upper or (i == bins - 1 and p == 1.0)
        ]
        result.append(
            ReliabilityBin(
                lower=round(lower, 4),
                upper=round(upper, 4),
                count=len(members),
                mean_predicted=round(sum(p for p, _ in members) / len(members), 4) if members else None,
                observed_rate=round(sum(1 for _, o in members if o) / len(members), 4) if members else None,
            )
        )
    return result


def temporal_holdout_evaluation(
    dataset: DisputeOutcomeDataset, test_from_year: int, *, min_samples: int = MIN_SAMPLES
) -> EstimatorEvaluation:
    train = dataset.model_copy(update={"records": [r for r in dataset.records if r.decision_year < test_from_year]})
    test = [
        r for r in dataset.records
        if r.decision_year >= test_from_year and r.outcome not in UNKNOWN_RESULT_OUTCOMES
    ]

    predictions: List[float] = []
    outcomes: List[bool] = []
    refused = 0
    intervals: Dict[tuple, tuple] = {}
    for record in test:
        estimate = estimate_outcome(
            OutcomeQuery(dispute_category=record.dispute_category, forum=record.forum),
            train if train.records else None,
            min_samples=min_samples,
            allow_synthetic=dataset.is_synthetic,
        )
        if estimate.status != "ESTIMATED":
            refused += 1
            continue
        predictions.append(estimate.probability_favourable)
        outcomes.append(record.outcome in FAVOURABLE_OUTCOMES)
        intervals[(record.dispute_category.lower(), record.forum)] = estimate.interval_95

    decided_train = [r for r in train.records if r.outcome not in UNKNOWN_RESULT_OUTCOMES]
    base_rate = (
        sum(1 for r in decided_train if r.outcome in FAVOURABLE_OUTCOMES) / len(decided_train)
        if decided_train else None
    )

    coverage = None
    if intervals:
        covered = 0
        for (category, forum), (low, high) in intervals.items():
            group = [r for r in test if r.dispute_category.lower() == category and r.forum == forum]
            rate = sum(1 for r in group if r.outcome in FAVOURABLE_OUTCOMES) / len(group)
            covered += low <= rate <= high
        coverage = round(covered / len(intervals), 4)

    return EstimatorEvaluation(
        dataset_name=dataset.name,
        synthetic=dataset.is_synthetic,
        test_from_year=test_from_year,
        test_disputes=len(test),
        estimated=len(predictions),
        refused_insufficient_evidence=refused,
        brier_score=brier_score(predictions, outcomes) if predictions else None,
        base_rate_brier_score=(
            brier_score([base_rate] * len(outcomes), outcomes) if predictions and base_rate is not None else None
        ),
        log_loss=log_loss(predictions, outcomes) if predictions else None,
        reliability=reliability_bins(predictions, outcomes) if predictions else [],
        interval_coverage=coverage,
    )
