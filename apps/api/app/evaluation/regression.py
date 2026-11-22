"""CI evaluation regression gate (WS2, ADR-024).

Compares the Phase-4 harness metrics (``runner.run_all()``) with a committed baseline
(``baseline/phase4_baseline.json``). What it guards: the OFFLINE heuristic/rule code paths
on the SYNTHETIC, hand-written datasets in ``data/evaluation/`` — see
``docs/evaluation/phase4-harnesses.md``. It does NOT measure LLM accuracy, real-world
accuracy, or anything on real documents.

Tolerances: every harness is deterministic offline code on fixed data, so a re-run
reproduces the numbers exactly and the tolerance is 0.0 for every metric (plus 1e-9 float
slack). Any drop fails; an improvement passes and is reported so the baseline can be
raised in a reviewed commit. Dataset sizes must match exactly. A non-zero tolerance is an
explicit, reviewed edit of the committed baseline file.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

BASELINE_PATH = Path(__file__).resolve().parent / "baseline" / "phase4_baseline.json"
FLOAT_SLACK = 1e-9
HONESTY_NOTE = (
    "Offline heuristic/rule code paths scored on SYNTHETIC hand-written datasets "
    "(docs/evaluation/phase4-harnesses.md). A regression gate, not LLM accuracy and not "
    "real-world accuracy."
)


@dataclass(frozen=True)
class MetricSpec:
    path: str  # "<harness>.<key>[.<key>]" into run_all()'s report
    direction: str  # "higher" or "lower" is better


HEADLINE_METRICS: Tuple[MetricSpec, ...] = (
    MetricSpec("bma.accuracy", "higher"),
    MetricSpec("bma.mapping.f1", "higher"),
    MetricSpec("pea.procedures.f1", "higher"),
    MetricSpec("pea.medicines.f1", "higher"),
    MetricSpec("pea.all_items.f1", "higher"),
    MetricSpec("pea.total_amount_accuracy", "higher"),
    MetricSpec("anomaly.line_level.f1", "higher"),
    MetricSpec("anomaly.bill_level.f1", "higher"),
    MetricSpec("crma.crma", "higher"),
    MetricSpec("crma.wrongful.f1", "higher"),
    MetricSpec("crma.clause_accuracy", "higher"),
    MetricSpec("crma.clinical_accuracy", "higher"),
    MetricSpec("ocr.corpus_wer", "lower"),
    MetricSpec("ocr.corpus_cer", "lower"),
    MetricSpec("dawacheck.accuracy", "higher"),
    MetricSpec("dawacheck.mapping.f1", "higher"),
    MetricSpec("dawacheck.ceiling_accuracy", "higher"),
    MetricSpec("appeal.mean_score", "higher"),
    MetricSpec("appeal.per_category.clauses", "higher"),
    MetricSpec("appeal.per_category.justification", "higher"),
    MetricSpec("appeal.per_category.references", "higher"),
    MetricSpec("grounding.production.grounding_score", "higher"),
    MetricSpec("grounding.production.hallucination_rate", "lower"),
    MetricSpec("grounding.detector.precision", "higher"),
    MetricSpec("grounding.detector.recall", "higher"),
    # Wave 2. Retrieval is measured on a SYNTHETIC tuning set (optimistic by construction); the gate only
    # guards against regressions. Context reuse gates the modelled DPR and the counts, NOT the hit rate
    # (it measures non-emptiness and is ~1 by construction).
    MetricSpec("retrieval.mrr", "higher"),
    MetricSpec("retrieval.recall_at_k", "higher"),
    MetricSpec("retrieval.pcra", "higher"),
    MetricSpec("retrieval.precision", "higher"),
    MetricSpec("retrieval.abstention_rate", "higher"),
    MetricSpec("retrieval.at_k.3.hit_rate", "higher"),
    MetricSpec("context_reuse.dpr", "higher"),
)

# Dataset sizes: a change means the dataset changed, which needs a reviewed baseline update.
COUNT_METRICS: Tuple[str, ...] = (
    "bma.rows", "pea.bills", "anomaly.bills", "anomaly.lines", "crma.scenarios",
    "ocr.rows_total", "dawacheck.rows", "appeal.letters", "grounding.detector_rows",
    "grounding.production.letters", "retrieval.queries", "retrieval.answerable",
    "context_reuse.n_scenarios", "context_reuse.n_requests",
)

_MISSING = object()


def _get(reports: Dict[str, Any], path: str) -> Any:
    node: Any = reports
    for part in path.split("."):
        if not isinstance(node, dict) or part not in node:
            return _MISSING
        node = node[part]
    return node


def extract_metrics(reports: Dict[str, Any]) -> Dict[str, Optional[float]]:
    """{path: value} for every headline and count metric present in ``reports``."""
    out: Dict[str, Optional[float]] = {}
    for path in [m.path for m in HEADLINE_METRICS] + list(COUNT_METRICS):
        value = _get(reports, path)
        if value is not _MISSING:
            out[path] = value
    return out


def build_baseline(reports: Dict[str, Any]) -> Dict[str, Any]:
    """A baseline document from a run_all() report set (deterministic: no timestamps)."""
    values = extract_metrics(reports)
    return {
        "_meta": {
            "description": "Committed baseline for scripts/check_eval_regression.py (WS2, ADR-024).",
            "synthetic": True,
            "note": HONESTY_NOTE,
            "regenerate": "python scripts/check_eval_regression.py --write-baseline "
                          "apps/api/app/evaluation/baseline/phase4_baseline.json",
            "tolerance_rationale": "Deterministic offline harnesses on fixed data: 0.0 for every "
                                   "metric (1e-9 float slack). Any drop fails.",
        },
        "metrics": {
            m.path: {"value": values.get(m.path), "direction": m.direction, "tolerance": 0.0}
            for m in HEADLINE_METRICS
        },
        "counts": {p: values.get(p) for p in COUNT_METRICS},
    }


def load_baseline(path: Path) -> Dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


@dataclass(frozen=True)
class MetricDelta:
    name: str
    baseline: Optional[float]
    current: Optional[float]
    delta: Optional[float]
    tolerance: float
    direction: str
    status: str  # ok | improved | regressed | count_changed


@dataclass
class RegressionReport:
    rows: List[MetricDelta] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors and all(r.status in ("ok", "improved") for r in self.rows)

    def format_table(self) -> str:
        def f(v):
            if v is None:
                return "n/a"
            return str(v) if isinstance(v, int) else f"{v:.4f}"

        lines = [f"{'metric':32} {'baseline':>9} {'current':>9} {'delta':>9} {'tol':>6}  status"]
        for r in self.rows:
            if r.delta is None:
                delta = "n/a"
            else:
                delta = f"{r.delta:+d}" if isinstance(r.delta, int) else f"{r.delta:+.4f}"
            lines.append(f"{r.name:32} {f(r.baseline):>9} {f(r.current):>9} {delta:>9} "
                         f"{r.tolerance:>6.3f}  {r.status.upper()}")
        return "\n".join(lines)


def _classify(base: Optional[float], cur: Optional[float], direction: str, tolerance: float) -> Tuple[Optional[float], str]:
    if base is None and cur is None:
        return None, "ok"
    if base is None or cur is None:
        return None, "regressed"  # a metric becoming (un)defined is a behaviour change
    delta = cur - base
    signed = delta if direction == "higher" else -delta  # >0 means better
    if signed < -(tolerance + FLOAT_SLACK):
        return delta, "regressed"
    if signed > FLOAT_SLACK:
        return delta, "improved"
    return delta, "ok"


def compare(baseline: Dict[str, Any], reports: Dict[str, Any],
            only: Optional[Iterable[str]] = None) -> RegressionReport:
    """Gate ``reports`` against ``baseline``. ``only`` restricts the check to those
    harnesses (``evaluate_phase4.py --only X --check-baseline``); the others are then
    neither required nor compared."""
    result = RegressionReport()
    selected = set(only) if only else None

    def wanted(path: str) -> bool:
        return selected is None or path.split(".")[0] in selected

    metrics = baseline.get("metrics") if isinstance(baseline, dict) else None
    counts = baseline.get("counts") if isinstance(baseline, dict) else None
    if not isinstance(metrics, dict) or not isinstance(counts, dict):
        result.errors.append("baseline is missing its 'metrics'/'counts' sections")
        return result

    for name, r in reports.items():
        if not (isinstance(r, dict) and isinstance(r.get("dataset"), dict) and r["dataset"].get("synthetic") is True):
            result.errors.append(f"{name}: dataset is not flagged synthetic; refusing to gate on it")

    harnesses = {m.path.split(".")[0] for m in HEADLINE_METRICS}
    if selected is not None:
        for h in sorted(selected - harnesses):
            result.errors.append(f"{h}: not a gated harness")
        harnesses &= selected
    for h in sorted(harnesses - set(reports)):
        result.errors.append(f"{h}: harness missing from the current report")

    current = extract_metrics(reports)
    for spec in HEADLINE_METRICS:
        if not wanted(spec.path):
            continue
        entry = metrics.get(spec.path)
        if not isinstance(entry, dict) or "value" not in entry:
            result.errors.append(f"{spec.path}: missing from the baseline")
            continue
        if spec.path not in current:
            if spec.path.split(".")[0] in reports:
                result.errors.append(f"{spec.path}: missing from the current report")
            continue
        direction = entry.get("direction", spec.direction)
        tolerance = float(entry.get("tolerance", 0.0))
        delta, status = _classify(entry["value"], current[spec.path], direction, tolerance)
        result.rows.append(MetricDelta(spec.path, entry["value"], current[spec.path], delta,
                                       tolerance, direction, status))

    for path in COUNT_METRICS:
        if not wanted(path):
            continue
        if path not in counts:
            result.errors.append(f"{path}: missing from the baseline")
            continue
        if path not in current:
            continue  # the missing harness is already reported above
        status = "ok" if counts[path] == current[path] else "count_changed"
        delta = None if counts[path] is None or current[path] is None else current[path] - counts[path]
        result.rows.append(MetricDelta(path, counts[path], current[path], delta, 0.0, "equal", status))
    return result
