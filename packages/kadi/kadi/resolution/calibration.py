"""
Kadi entity resolution — feedback-calibrated confidence thresholds (#88).

This is **not RLHF**. There is no reward model and no policy optimization. It is a
deterministic, bounded, online recalibration of the resolver's two thresholds from the
confirm/reject answers users give to ASK prompts (and to automatic merges they dispute):

- merge threshold: the lowest confidence level t such that, for every level from the top
  down to t with at least ``min_merge_support`` labeled samples at/above it, the share of
  true matches is >= ``target_precision``. Wrong merges are the expensive error, so this
  is set by precision.
- ask threshold: the highest level t at which at least ``target_recall`` of all true
  matches score >= t, i.e. are merged or shown to the user rather than silently created as
  a new entity.

Guards:

- fewer than ``min_samples`` labels, or fewer than ``min_per_class`` of either class,
  returns ``INSUFFICIENT_EVIDENCE`` and keeps the current thresholds
- thresholds are clamped to ``bounds`` and move at most ``max_step`` per recalibration,
  so one batch of feedback cannot swing the resolver
- ask <= merge always

Known bias (disclosed, not corrected): labels only exist for pairs that reached ASK or a
disputed MERGE, so pairs the resolver confidently called NEW are under-represented.

Known attack surface (P2, examined 2026-09-16, NOT fixed this pass — disclosed rather
than silently left): recalibration is GLOBAL (scope is an entity type, or "all_types"),
aggregating ``KadiResolutionDecision.feedback_same_entity`` across every case, with no
per-source attribution or trust weighting. With no authentication beyond a per-case
access token (ADR-009), nothing stops one actor from creating many cases and submitting
systematically wrong feedback to walk the merge/ask thresholds toward an extreme —
``min_merge_support`` defaults to just 5 labeled samples. The existing ``max_step`` /
``bounds`` clamp (see Guards above) is real, deliberate poisoning resistance: it already
prevents any single recalibration event from swinging the resolver, so this is not an
unmitigated hole — but it does not prevent a patient attacker from repeating small,
bounded nudges over many recalibration cycles to walk a threshold to its bound over
time. A real fix needs either per-source (not per-sample) diversity requirements before
counting feedback, or outlier/anomaly detection on submitted labels — both are
non-trivial statistics work, not a "smallest real fix," and were not built in this
security-remediation pass. Recorded here as a known, examined limitation rather than
either silently ignored or overstated as solved.
"""

import math
from typing import List, Literal, Optional, Sequence, Tuple

from pydantic import BaseModel, Field

from kadi.resolution.resolver import ResolutionThresholds


class LabeledOutcome(BaseModel):
    confidence: float = Field(..., ge=0.0, le=1.0)
    same_entity: bool
    entity_type: Optional[str] = None


class CalibrationMetrics(BaseModel):
    sample_count: int
    positives: int
    negatives: int
    merge_threshold: float
    ask_threshold: float
    merge_support: int
    merge_precision: Optional[float]
    merge_precision_wilson_lower: Optional[float]
    ask_recall: Optional[float]
    false_merge_rate: Optional[float]


class CalibrationResult(BaseModel):
    status: Literal["CALIBRATED", "INSUFFICIENT_EVIDENCE"]
    scope: str
    thresholds: ResolutionThresholds
    proposed_merge: Optional[float] = None
    proposed_ask: Optional[float] = None
    metrics: CalibrationMetrics
    reasons: List[str] = Field(default_factory=list)


def wilson_lower_bound(successes: int, n: int, z: float = 1.96) -> Optional[float]:
    if n <= 0:
        return None
    p = successes / n
    denom = 1 + z * z / n
    centre = p + z * z / (2 * n)
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return round((centre - margin) / denom, 4)


def compute_metrics(samples: Sequence[LabeledOutcome], merge: float, ask: float) -> CalibrationMetrics:
    positives = [s for s in samples if s.same_entity]
    negatives = [s for s in samples if not s.same_entity]
    merged = [s for s in samples if s.confidence >= merge]
    merged_true = sum(1 for s in merged if s.same_entity)
    return CalibrationMetrics(
        sample_count=len(samples),
        positives=len(positives),
        negatives=len(negatives),
        merge_threshold=merge,
        ask_threshold=ask,
        merge_support=len(merged),
        merge_precision=round(merged_true / len(merged), 4) if merged else None,
        merge_precision_wilson_lower=wilson_lower_bound(merged_true, len(merged)),
        ask_recall=(
            round(sum(1 for s in positives if s.confidence >= ask) / len(positives), 4) if positives else None
        ),
        false_merge_rate=(
            round(sum(1 for s in negatives if s.confidence >= merge) / len(negatives), 4) if negatives else None
        ),
    )


def _bounded_step(old: float, new: float, max_step: float, bounds: Tuple[float, float]) -> float:
    new = min(max(new, bounds[0]), bounds[1])
    delta = new - old
    if abs(delta) > max_step:
        new = old + math.copysign(max_step, delta)
    return round(new, 4)


def calibrate_thresholds(
    samples: Sequence[LabeledOutcome],
    current: Optional[ResolutionThresholds] = None,
    *,
    scope: str = "all_types",
    target_precision: float = 0.95,
    target_recall: float = 0.95,
    min_samples: int = 30,
    min_per_class: int = 8,
    min_merge_support: int = 5,
    max_step: float = 0.05,
    bounds: Tuple[float, float] = (0.5, 0.99),
) -> CalibrationResult:
    current = current or ResolutionThresholds()
    positives = [s for s in samples if s.same_entity]
    negatives = [s for s in samples if not s.same_entity]

    shortfalls = []
    if len(samples) < min_samples:
        shortfalls.append(f"{len(samples)} labeled decisions (need {min_samples})")
    if len(positives) < min_per_class:
        shortfalls.append(f"{len(positives)} confirmed matches (need {min_per_class})")
    if len(negatives) < min_per_class:
        shortfalls.append(f"{len(negatives)} rejected matches (need {min_per_class})")
    if shortfalls:
        return CalibrationResult(
            status="INSUFFICIENT_EVIDENCE",
            scope=scope,
            thresholds=current,
            metrics=compute_metrics(samples, current.merge, current.ask),
            reasons=["not enough feedback to recalibrate: " + "; ".join(shortfalls)],
        )

    reasons: List[str] = []
    levels = sorted({round(s.confidence, 4) for s in samples}, reverse=True)

    proposed_merge: Optional[float] = None
    for level in levels:
        above = [s for s in samples if s.confidence >= level]
        if len(above) < min_merge_support:
            continue
        precision = sum(1 for s in above if s.same_entity) / len(above)
        if precision < target_precision:
            break
        proposed_merge = level
    if proposed_merge is None:
        proposed_merge = bounds[1]
        reasons.append(
            "no confidence level reached the target merge precision with enough support; "
            "the merge threshold moves toward the conservative bound"
        )

    proposed_ask = levels[-1]
    for level in levels:
        recall = sum(1 for s in positives if s.confidence >= level) / len(positives)
        if recall >= target_recall:
            proposed_ask = level
            break
    proposed_ask = min(proposed_ask, proposed_merge)

    merge = _bounded_step(current.merge, proposed_merge, max_step, bounds)
    ask = _bounded_step(current.ask, proposed_ask, max_step, bounds)
    if ask > merge:
        ask = merge
    if (merge, ask) != (proposed_merge, proposed_ask):
        reasons.append(f"step limited to ±{max_step} per recalibration and clamped to {bounds}")

    return CalibrationResult(
        status="CALIBRATED",
        scope=scope,
        thresholds=ResolutionThresholds(merge=merge, ask=ask, source="feedback_calibrated"),
        proposed_merge=proposed_merge,
        proposed_ask=proposed_ask,
        metrics=compute_metrics(samples, merge, ask),
        reasons=reasons,
    )
