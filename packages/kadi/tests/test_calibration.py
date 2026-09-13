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
