"""Feedback-calibrated thresholds (#88) — deterministic and bounded, not RLHF."""

import pytest

from kadi.resolution.calibration import (
    LabeledOutcome,
    calibrate_thresholds,
    compute_metrics,
    wilson_lower_bound,
)
from kadi.resolution.resolver import ResolutionThresholds


def _samples(*groups):
    out = []
    for confidence, same, count in groups:
        out.extend(LabeledOutcome(confidence=confidence, same_entity=same) for _ in range(count))
    return out


def test_wilson_lower_bound_reference_value():
    assert wilson_lower_bound(9, 10) == pytest.approx(0.5958, abs=1e-3)
    assert wilson_lower_bound(0, 0) is None


def test_too_little_feedback_keeps_current_thresholds():
    result = calibrate_thresholds(_samples((0.95, True, 6), (0.75, False, 4)))
    assert result.status == "INSUFFICIENT_EVIDENCE"
    assert result.thresholds == ResolutionThresholds()
    assert "10 labeled decisions (need 30)" in result.reasons[0]
    assert "4 rejected matches (need 8)" in result.reasons[0]


def test_calibration_picks_precision_and_recall_targets():
    samples = _samples(
        (0.95, True, 15), (0.85, True, 10), (0.75, True, 5),
        (0.80, False, 5), (0.72, False, 5),
    )
    result = calibrate_thresholds(samples)
    # Everything >= 0.85 is a true match; adding 0.80 drops precision to 25/30.
    assert result.proposed_merge == 0.85
    # All 30 true matches score >= 0.75.
    assert result.proposed_ask == 0.75
    assert result.status == "CALIBRATED"
    assert (result.thresholds.merge, result.thresholds.ask) == (0.85, 0.75)
    assert result.thresholds.source == "feedback_calibrated"
    assert result.metrics.merge_support == 25
    assert result.metrics.merge_precision == 1.0
    assert result.metrics.ask_recall == 1.0
    assert result.metrics.false_merge_rate == 0.0


def test_each_recalibration_moves_at_most_max_step():
    samples = _samples(
        (0.95, True, 15), (0.85, True, 10), (0.75, True, 5),
        (0.80, False, 5), (0.72, False, 5),
    )
    current = ResolutionThresholds(merge=0.99, ask=0.90)
    result = calibrate_thresholds(samples, current)
    assert (result.thresholds.merge, result.thresholds.ask) == (0.94, 0.85)
    assert any("step limited" in r for r in result.reasons)


def test_unreachable_precision_moves_toward_the_conservative_bound():
    samples = _samples((0.95, True, 10), (0.95, False, 10), (0.6, True, 10))
    result = calibrate_thresholds(samples)
    assert result.proposed_merge == 0.99
    assert result.thresholds.merge == 0.95  # 0.90 + max_step
    assert result.thresholds.ask <= result.thresholds.merge


def test_compute_metrics_counts_false_merges():
    samples = _samples((0.95, True, 3), (0.92, False, 1), (0.5, False, 3))
    metrics = compute_metrics(samples, merge=0.9, ask=0.7)
    assert metrics.merge_support == 4
    assert metrics.merge_precision == 0.75
    assert metrics.false_merge_rate == 0.25


# ---------------------------------------------------------------------------
# SEC-10: one case's feedback must not be able to recalibrate a threshold shared by
# every other case — global calibration poisoning.
# ---------------------------------------------------------------------------


def _samples_from_one_source(*groups, source_id="CASE-attacker"):
    out = []
    for confidence, same, count in groups:
        out.extend(
            LabeledOutcome(confidence=confidence, same_entity=same, source_id=source_id) for _ in range(count)
        )
    return out


def test_a_single_attacker_case_cannot_recalibrate_even_with_plenty_of_samples():
    """The exact attack: one actor creates many entities under ONE case and disputes
    them, feeding 40 systematically-wrong labels — easily clearing min_samples/
    min_per_class — trying to walk the merge threshold down toward garbage matches."""
    samples = _samples_from_one_source(
        (0.60, True, 20), (0.55, True, 15), (0.50, False, 5), source_id="CASE-attacker"
    )
    result = calibrate_thresholds(samples)
    assert result.status == "INSUFFICIENT_EVIDENCE"
    assert any("distinct case" in r for r in result.reasons)
    # Thresholds are untouched — the attacker's flood never reached the resolver.
    assert result.thresholds == ResolutionThresholds()


def test_feedback_from_enough_distinct_cases_still_calibrates():
    """The fix must not break honest calibration — genuine diversity still works."""
    samples = []
    groups = [(0.95, True, 15), (0.85, True, 10), (0.75, True, 5), (0.80, False, 5), (0.72, False, 5)]
    i = 0
    for confidence, same, count in groups:
        for _ in range(count):
            samples.append(LabeledOutcome(confidence=confidence, same_entity=same, source_id=f"CASE-{i % 6}"))
            i += 1
    result = calibrate_thresholds(samples)
    assert result.status == "CALIBRATED"


def test_one_dominant_case_is_capped_even_among_several_distinct_sources():
    """A more sophisticated attacker spins up exactly `min_distinct_sources` cases to
    clear the diversity bar, but pours the bulk of the (wrong) feedback through one of
    them. max_samples_per_source must stop that single case from dominating the pool."""
    honest = [
        LabeledOutcome(confidence=0.95, same_entity=True, source_id=f"CASE-honest-{i}") for i in range(20)
    ] + [
        LabeledOutcome(confidence=0.55, same_entity=False, source_id=f"CASE-honest-{i}") for i in range(20)
    ]
    # One attacker case tries to inject 200 wrong "same_entity=True" labels at low
    # confidence, far outnumbering every honest source individually.
    attacker_flood = [
        LabeledOutcome(confidence=0.55, same_entity=True, source_id="CASE-attacker") for _ in range(200)
    ]
    result = calibrate_thresholds(honest + attacker_flood, min_distinct_sources=5, max_samples_per_source=10)
    # The flood is capped to 10 samples — it cannot swamp the 40 honest, diverse labels.
    assert result.status == "CALIBRATED"
    assert result.metrics.sample_count <= 40 + 10


def test_samples_without_a_source_id_are_not_guarded_but_still_work():
    """Opt-in hardening: a caller that never attaches source_id (e.g. an older/simpler
    caller) gets the pre-SEC-10 behavior, not a silent INSUFFICIENT_EVIDENCE regression."""
    samples = _samples(
        (0.95, True, 15), (0.85, True, 10), (0.75, True, 5),
        (0.80, False, 5), (0.72, False, 5),
    )
    result = calibrate_thresholds(samples)
    assert result.status == "CALIBRATED"
