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

Known attack surface, FIXED (SEC-10, 2026-09-16): recalibration is GLOBAL (scope is an
entity type, or "all_types"), aggregating ``KadiResolutionDecision.feedback_same_entity``
across every case, with no per-source attribution or trust weighting by default. With no
authentication beyond a per-case access token (ADR-009), nothing stops one actor from
creating many cases and submitting systematically wrong feedback to walk the merge/ask
thresholds toward an extreme — ``min_merge_support`` defaults to just 5 labeled samples.
The existing ``max_step``/``bounds`` clamp (see Guards above) already prevents any single
recalibration event from swinging the resolver, but did not stop a patient attacker from
repeating small, bounded nudges over many recalibration cycles to walk a threshold to its
bound over time, since every sample counted equally regardless of who submitted it.

The fix is the per-source diversity requirement flagged above as the real remedy:
``LabeledOutcome`` now optionally carries a ``source_id`` (the case id the feedback came
from). When source ids are supplied, two additional guards apply before any recalibration
is trusted:

- ``min_distinct_sources`` — at least this many DISTINCT cases must have contributed a
  label, not just this many labels. A single case creating many entities and disputing
  them cannot manufacture ``min_samples`` worth of "evidence" alone.
- ``max_samples_per_source`` — any one case's labels are capped at this many before being
  counted, so even a case that clears the distinct-source bar cannot dominate the sample
  pool and drag the computed precision/recall — and therefore the proposed threshold —
  toward whatever answer it keeps giving.

When no ``source_id`` is supplied (older callers, or tests that only care about the
statistics), these guards are skipped entirely — this is opt-in hardening, not a breaking
change to the calibration math itself.
"""

import math
from typing import Dict, List, Literal, Optional, Sequence, Tuple

from pydantic import BaseModel, Field

from kadi.resolution.resolver import ResolutionThresholds


class LabeledOutcome(BaseModel):
    confidence: float = Field(..., ge=0.0, le=1.0)
    same_entity: bool
    entity_type: Optional[str] = None
    # SEC-10: the case this feedback came from. Optional so existing callers that don't
    # (or can't) attribute a source keep working unchanged; supplying it enables the
    # per-source diversity guards in calibrate_thresholds below.
    source_id: Optional[str] = None


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


def _apply_source_diversity_guard(
    samples: Sequence[LabeledOutcome],
    *,
    min_distinct_sources: int,
    max_samples_per_source: int,
) -> "Tuple[List[LabeledOutcome], int, bool]":
    """SEC-10: caps each source's contribution and reports how many distinct sources
    are represented. Samples with no source_id are passed through uncapped and do not
    count toward distinct-source diversity — attribution is opt-in, not assumed."""
    attributed = [s for s in samples if s.source_id is not None]
    unattributed = [s for s in samples if s.source_id is None]

    if not attributed:
        return list(samples), 0, True

    distinct_sources = len({s.source_id for s in attributed})
    per_source_count: Dict[str, int] = {}
    capped: List[LabeledOutcome] = []
    for s in attributed:
        seen = per_source_count.get(s.source_id, 0)
        if seen >= max_samples_per_source:
            continue
        per_source_count[s.source_id] = seen + 1
        capped.append(s)

    enough_sources = distinct_sources >= min_distinct_sources
    return capped + unattributed, distinct_sources, enough_sources


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
    min_distinct_sources: int = 5,
    max_samples_per_source: int = 10,
) -> CalibrationResult:
    current = current or ResolutionThresholds()

    samples, distinct_sources, enough_sources = _apply_source_diversity_guard(
        samples, min_distinct_sources=min_distinct_sources, max_samples_per_source=max_samples_per_source
    )

    positives = [s for s in samples if s.same_entity]
    negatives = [s for s in samples if not s.same_entity]

    shortfalls = []
    if not enough_sources:
        shortfalls.append(
            f"feedback from only {distinct_sources} distinct case(s) (need {min_distinct_sources}) — "
            "one case's feedback cannot recalibrate a threshold shared by every case"
        )
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
