"""CRR and DPR for Kadi's shared case context (#112, Phase 4 decision D8).

Definitions (fixed before measuring):

- A **context request** is a module asking Kadi's stored case context for entities, line
  items or the timeline (``app.telemetry.context_metrics``).
- **CRR** (context reuse rate) = requests served from context the case already held /
  all context requests.
- **DPR** (duplicate-processing reduction) = (baseline work - current work) / baseline
  work, where work is counted OCR + extraction units and the *baseline* is the run with
  ``CONTEXT_REUSE_ENABLED=false`` (every request counted as repeating the extraction).

This scorer is pure: it only does arithmetic on counts. The counts themselves come from the
instrumented pipeline run over the synthetic demo scenarios A-E
(``data/evaluation/context_reuse_synthetic.jsonl``); they are instrumented counts on
synthetic scenarios, not production traffic, and they say nothing about extraction quality.

Row shape (both runs use the same layout)::

    {"id": "A", "documents": 2,
     "reuse_on":  {"requests": {"billnyay": {"reused": 3, "fresh": 1}},
                   "work": {"ingest": {"ocr": 2, "extraction": 2}, "repeat": {}}},
     "reuse_off": {...}}
"""

from collections import defaultdict
from typing import Any, Dict, List, Optional


def _count(value: Any, where: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{where}: counts must be non-negative integers, got {value!r}")
    return value


def _request_totals(run: Dict[str, Any], where: str) -> Dict[str, Dict[str, int]]:
    out: Dict[str, Dict[str, int]] = {}
    for module, outcomes in (run.get("requests") or {}).items():
        unknown = set(outcomes) - {"reused", "fresh"}
        if unknown:
            raise ValueError(f"{where}: unknown outcome(s) {sorted(unknown)} for {module}")
        out[module] = {o: _count(outcomes.get(o, 0), f"{where}.{module}.{o}") for o in ("reused", "fresh")}
    return out


def _work_total(run: Dict[str, Any], where: str) -> int:
    total = 0
    for phase, kinds in (run.get("work") or {}).items():
        for kind, units in kinds.items():
            total += _count(units, f"{where}.work.{phase}.{kind}")
    return total


def _ratio(numerator: float, denominator: float) -> Optional[float]:
    return round(numerator / denominator, 4) if denominator > 0 else None


def evaluate_context_reuse(scenarios: List[Dict[str, Any]]) -> Dict[str, Any]:
    per_scenario: List[Dict[str, Any]] = []
    module_reused: Dict[str, int] = defaultdict(int)
    module_total: Dict[str, int] = defaultdict(int)
    reused = requests = current = baseline = 0
    for row in scenarios:
        sid = str(row.get("id"))
        on = _request_totals(row["reuse_on"], f"{sid}.reuse_on")
        s_reused = sum(v["reused"] for v in on.values())
        s_total = sum(v["reused"] + v["fresh"] for v in on.values())
        s_current = _work_total(row["reuse_on"], f"{sid}.reuse_on")
        s_baseline = _work_total(row["reuse_off"], f"{sid}.reuse_off")
        for module, v in on.items():
            module_reused[module] += v["reused"]
            module_total[module] += v["reused"] + v["fresh"]
        per_scenario.append({
            "id": sid, "requests": s_total, "reused": s_reused,
            "crr": _ratio(s_reused, s_total),
            "current_work": s_current, "baseline_work": s_baseline,
            "dpr": _ratio(s_baseline - s_current, s_baseline),
        })
        reused += s_reused
        requests += s_total
        current += s_current
        baseline += s_baseline
    return {
        "n_scenarios": len(scenarios),
        "n_requests": requests,
        "reused": reused,
        "crr": _ratio(reused, requests),
        "current_work": current,
        "baseline_work": baseline,
        "dpr": _ratio(baseline - current, baseline),
        "per_module_crr": {m: _ratio(module_reused[m], module_total[m]) for m in sorted(module_total)},
        "per_scenario": per_scenario,
    }
