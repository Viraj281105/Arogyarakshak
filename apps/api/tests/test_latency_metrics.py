"""Unit tests for app/latency_metrics.py (#116)."""

from app.latency_metrics import LatencyTracker, TARGET_LATENCY_SECONDS, _percentile


def test_empty_tracker_summary_has_no_percentiles():
    tracker = LatencyTracker()
    summary = tracker.summary()
    assert summary.sample_count == 0
    assert summary.p50_seconds is None
    assert summary.compliance_rate is None


def test_records_and_summarizes_samples():
    tracker = LatencyTracker()
    for duration in [2.0, 4.0, 6.0, 8.0, 20.0]:
        tracker.record("CASE-x", duration, "completed")

    summary = tracker.summary()
    assert summary.sample_count == 5
    assert summary.min_seconds == 2.0
    assert summary.max_seconds == 20.0
    assert summary.p50_seconds == 6.0
    assert summary.target_seconds == TARGET_LATENCY_SECONDS


def test_violations_and_compliance_rate_are_computed_against_the_target():
    tracker = LatencyTracker()
    for duration in [1.0, 2.0, 3.0, 15.0]:  # one sample (15.0) exceeds the 10s target
        tracker.record("CASE-x", duration, "completed")

    summary = tracker.summary()
    assert summary.violations == 1
    assert summary.compliance_rate == 0.75


def test_all_within_target_has_zero_violations_and_full_compliance():
    tracker = LatencyTracker()
    for duration in [1.0, 2.0, 3.0]:
        tracker.record("CASE-x", duration, "completed")

    summary = tracker.summary()
    assert summary.violations == 0
    assert summary.compliance_rate == 1.0


def test_recent_returns_newest_first_and_respects_limit():
    tracker = LatencyTracker()
    for i in range(5):
        tracker.record(f"CASE-{i}", float(i), "completed")

    recent = tracker.recent(limit=2)
    assert len(recent) == 2
    assert recent[0].case_id == "CASE-4"
    assert recent[1].case_id == "CASE-3"


def test_sample_window_is_bounded():
    """Mirrors the bounded processing_status/rate-limiter pattern — must not grow
    without limit under sustained upload volume."""
    tracker = LatencyTracker()
    from app.latency_metrics import _MAX_SAMPLES

    for i in range(_MAX_SAMPLES + 100):
        tracker.record(f"CASE-{i}", 1.0, "completed")

    assert len(tracker._samples) == _MAX_SAMPLES
    # The oldest samples must have been evicted, not the newest.
    assert tracker._samples[-1].case_id == f"CASE-{_MAX_SAMPLES + 99}"


def test_reset_clears_all_samples():
    tracker = LatencyTracker()
    tracker.record("CASE-x", 1.0, "completed")
    tracker.reset()
    assert tracker.summary().sample_count == 0


def test_failed_outcomes_are_recorded_distinctly_from_completed():
    tracker = LatencyTracker()
    tracker.record("CASE-x", 3.0, "completed")
    tracker.record("CASE-y", 1.0, "failed")

    outcomes = {s.outcome for s in tracker.recent(limit=10)}
    assert outcomes == {"completed", "failed"}


def test_percentile_helper_matches_known_values():
    sorted_values = [1.0, 2.0, 3.0, 4.0, 5.0]
    assert _percentile(sorted_values, 0.0) == 1.0
    assert _percentile(sorted_values, 1.0) == 5.0
    assert _percentile(sorted_values, 0.5) == 3.0
