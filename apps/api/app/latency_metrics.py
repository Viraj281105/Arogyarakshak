"""
End-to-End Processing Time Monitoring (#116).

Measures wall-clock time from "upload received" to the pipeline's terminal event
(`completed` or `failed`) for the document -> OCR -> extraction -> entity-resolution ->
database-write flow in `app/api/v1/endpoints/kadi.py::process_document_background`, and
checks it against the project's stated target of under 10 seconds.

Same architectural pattern as `processing_status` (kadi.py) and the rate limiter
(app/rate_limit.py): a bounded, in-memory, single-process store. It is a metric
collection hook, not a distributed tracing system — a multi-worker deployment would
need this backed by a shared store (Prometheus, the database, etc.) to aggregate across
processes. That gap is disclosed, not hidden.
"""

import statistics
import time
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

# The stated E2E processing time target (issue #116).
TARGET_LATENCY_SECONDS = 10.0

# Bounded rolling window — mirrors processing_status's MAX_TRACKED_STATUS_CASES cap so
# this cannot itself become an unbounded-memory vector under sustained upload volume.
_MAX_SAMPLES = 500


class LatencySample(BaseModel):
    case_id: str
    duration_seconds: float
    outcome: str = Field(..., description="'completed' or 'failed' — which terminal event was reached.")
    timestamp: float


class LatencySummary(BaseModel):
    sample_count: int
    target_seconds: float = TARGET_LATENCY_SECONDS
    p50_seconds: Optional[float] = None
    p95_seconds: Optional[float] = None
    max_seconds: Optional[float] = None
    min_seconds: Optional[float] = None
    mean_seconds: Optional[float] = None
    violations: int = Field(
        0, description="How many recorded samples exceeded target_seconds."
    )
    compliance_rate: Optional[float] = Field(
        None, description="Fraction of samples within target_seconds. None when there are no samples."
    )
    single_process_only: bool = Field(
        True,
        description="This tracker is in-memory and per-process — see the module docstring. "
        "A multi-worker deployment needs a shared store to aggregate across processes.",
    )


class LatencyTracker:
    """In-memory bounded latency sample store."""

    def __init__(self) -> None:
        self._samples: List[LatencySample] = []

    def reset(self) -> None:
        self._samples.clear()

    def record(self, case_id: str, duration_seconds: float, outcome: str) -> None:
        if len(self._samples) >= _MAX_SAMPLES:
            self._samples.pop(0)
        self._samples.append(
            LatencySample(
                case_id=case_id,
                duration_seconds=duration_seconds,
                outcome=outcome,
                timestamp=time.time(),
            )
        )

    def summary(self) -> LatencySummary:
        durations = [s.duration_seconds for s in self._samples]
        if not durations:
            return LatencySummary(sample_count=0)

        sorted_durations = sorted(durations)
        violations = sum(1 for d in durations if d > TARGET_LATENCY_SECONDS)

        return LatencySummary(
            sample_count=len(durations),
            p50_seconds=round(statistics.median(sorted_durations), 3),
            p95_seconds=round(_percentile(sorted_durations, 0.95), 3),
            max_seconds=round(max(durations), 3),
            min_seconds=round(min(durations), 3),
            mean_seconds=round(statistics.mean(durations), 3),
            violations=violations,
            compliance_rate=round(1 - (violations / len(durations)), 4),
        )

    def recent(self, limit: int = 20) -> List[LatencySample]:
        return list(reversed(self._samples[-limit:]))


def _percentile(sorted_values: List[float], fraction: float) -> float:
    if len(sorted_values) == 1:
        return sorted_values[0]
    index = fraction * (len(sorted_values) - 1)
    lower = int(index)
    upper = min(lower + 1, len(sorted_values) - 1)
    weight = index - lower
    return sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight


tracker = LatencyTracker()
