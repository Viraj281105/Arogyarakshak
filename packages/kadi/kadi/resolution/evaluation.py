"""
Kadi entity resolution — evaluation harness.

    labeled pair -> resolve_mention -> decision -> compared with the label -> metrics

MERGE is the positive prediction. Reported metrics:

- merge precision / recall / F1 (ambiguous pairs, labeled ``same_entity: null``, are
  excluded and their actions reported separately)
- false merges (MERGE on a pair that is not the same entity) — the costly error
- review recall: share of true matches that were merged *or* sent to ASK, i.e. not
  silently created as a separate entity
- silent misses: true matches decided NEW
- ask rate, per-category breakdown, p50/p95 latency

The numbers are only as meaningful as the dataset. The fixture shipped with the tests is
hand-curated and synthetic; it measures behaviour on known hard cases, not real-world
accuracy.
"""

import json
import time
from pathlib import Path
from typing import Dict, FrozenSet, List, Optional, Sequence, Tuple

from pydantic import BaseModel, Field

from kadi.resolution.phonetic import soundex
from kadi.resolution.resolver import (
    ALL_SIGNALS,
    CandidateEntity,
    EntityMention,
    ResolutionThresholds,
    resolve_mention,
)
from kadi.resolution.semantic import SemanticEncoder


class DatasetMeta(BaseModel):
    name: str
    synthetic: bool
    provenance: str
    description: str = ""


class LabeledPair(BaseModel):
    id: str
    entity_type: str
    mention: str
    candidate: str
    same_entity: Optional[bool]
    category: str
    rationale: str = ""


def load_labeled_pairs(path: Path) -> Tuple[DatasetMeta, List[LabeledPair]]:
    """JSONL: the first line is {"_meta": {...}}, every following line one LabeledPair."""
    meta: Optional[DatasetMeta] = None
    pairs: List[LabeledPair] = []
    with Path(path).open(encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, start=1):
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            if "_meta" in record:
                meta = DatasetMeta(**record["_meta"])
                continue
            pairs.append(LabeledPair(**record))
    if meta is None:
        raise ValueError(f"{path} has no _meta header; provenance is required")
    return meta, pairs


class PairResult(BaseModel):
    pair_id: str
    category: str
    expected: Optional[bool]
    action: str
    confidence: float
    conflicts: List[str] = Field(default_factory=list)


class CategoryBreakdown(BaseModel):
    total: int = 0
    merge: int = 0
    ask: int = 0
    new: int = 0
    false_merges: int = 0
    silent_misses: int = 0


class EvaluationReport(BaseModel):
    dataset: str
    synthetic: bool
    provenance: str
    configuration: str
    enabled_signals: List[str]
    semantic_status: str
    thresholds: ResolutionThresholds
    pairs: int
    labeled_pairs: int
    ambiguous_pairs: int
    true_positives: int
    false_positives: int
    false_negatives: int
    true_negatives: int
    merge_precision: Optional[float]
    merge_recall: Optional[float]
    merge_f1: Optional[float]
    review_recall: Optional[float]
    false_merges: int
    false_merge_ids: List[str]
    silent_misses: int
    silent_miss_ids: List[str]
    ask_rate: float
    ambiguous_actions: Dict[str, int]
    categories: Dict[str, CategoryBreakdown]
    latency_ms_p50: float
    latency_ms_p95: float
    results: List[PairResult]


def _ratio(num: int, den: int) -> Optional[float]:
    return round(num / den, 4) if den else None


def _f1(precision: Optional[float], recall: Optional[float]) -> Optional[float]:
    if precision is None or recall is None or precision + recall == 0:
        return None
    return round(2 * precision * recall / (precision + recall), 4)


def _percentile(values: Sequence[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round(q * (len(ordered) - 1))))
    return round(ordered[index], 3)


def evaluate_pairs(
    pairs: Sequence[LabeledPair],
    meta: DatasetMeta,
    *,
    encoder: Optional[SemanticEncoder] = None,
    thresholds: Optional[ResolutionThresholds] = None,
    enabled_signals: FrozenSet[str] = ALL_SIGNALS,
    configuration: str = "",
) -> EvaluationReport:
    thresholds = thresholds or ResolutionThresholds()
    results: List[PairResult] = []
    latencies: List[float] = []
    categories: Dict[str, CategoryBreakdown] = {}
    tp = fp = fn = tn = 0
    reviewed_true = 0
    false_merge_ids: List[str] = []
    silent_miss_ids: List[str] = []
    ambiguous_actions: Dict[str, int] = {"MERGE": 0, "ASK": 0, "NEW": 0}
    semantic_seen: List[str] = []

    for pair in pairs:
        started = time.perf_counter()
        decision = resolve_mention(
            EntityMention(name=pair.mention, entity_type=pair.entity_type),
            [CandidateEntity(id="candidate", name=pair.candidate, entity_type=pair.entity_type)],
            thresholds=thresholds,
            encoder=encoder,
            enabled_signals=enabled_signals,
        )
        latencies.append((time.perf_counter() - started) * 1000)
        for signal in decision.signals:
            if signal.signal == "semantic":
                semantic_seen.append("AVAILABLE" if signal.status == "AVAILABLE" else signal.detail)

        bucket = categories.setdefault(pair.category, CategoryBreakdown())
        bucket.total += 1
        setattr(bucket, decision.action.lower(), getattr(bucket, decision.action.lower()) + 1)
        results.append(
            PairResult(
                pair_id=pair.id,
                category=pair.category,
                expected=pair.same_entity,
                action=decision.action,
                confidence=decision.confidence,
                conflicts=decision.conflicts,
            )
        )

        if pair.same_entity is None:
            ambiguous_actions[decision.action] += 1
            continue
        merged = decision.action == "MERGE"
        if pair.same_entity:
            if merged:
                tp += 1
            else:
                fn += 1
            if decision.action in ("MERGE", "ASK"):
                reviewed_true += 1
            else:
                silent_miss_ids.append(pair.id)
                bucket.silent_misses += 1
        else:
            if merged:
                fp += 1
                false_merge_ids.append(pair.id)
                bucket.false_merges += 1
            else:
                tn += 1

    labeled = tp + fp + fn + tn
    precision = _ratio(tp, tp + fp)
    recall = _ratio(tp, tp + fn)
    asks = sum(1 for r in results if r.action == "ASK")

    if "semantic" not in enabled_signals:
        semantic_status = "not enabled for this configuration"
    elif semantic_seen and all(s == "AVAILABLE" for s in semantic_seen):
        semantic_status = "AVAILABLE"
    else:
        semantic_status = next((s for s in semantic_seen if s != "AVAILABLE"), "UNAVAILABLE")

    return EvaluationReport(
        dataset=meta.name,
        synthetic=meta.synthetic,
        provenance=meta.provenance,
        configuration=configuration or "+".join(sorted(enabled_signals)),
        enabled_signals=sorted(enabled_signals),
        semantic_status=semantic_status,
        thresholds=thresholds,
        pairs=len(results),
        labeled_pairs=labeled,
        ambiguous_pairs=len(results) - labeled,
        true_positives=tp,
        false_positives=fp,
        false_negatives=fn,
        true_negatives=tn,
        merge_precision=precision,
        merge_recall=recall,
        merge_f1=_f1(precision, recall),
        review_recall=_ratio(reviewed_true, tp + fn),
        false_merges=fp,
        false_merge_ids=false_merge_ids,
        silent_misses=len(silent_miss_ids),
        silent_miss_ids=silent_miss_ids,
        ask_rate=round(asks / len(results), 4) if results else 0.0,
        ambiguous_actions=ambiguous_actions,
        categories=categories,
        latency_ms_p50=_percentile(latencies, 0.5),
        latency_ms_p95=_percentile(latencies, 0.95),
        results=results,
    )


class BaselineReport(BaseModel):
    name: str
    precision: Optional[float]
    recall: Optional[float]
    f1: Optional[float]
    true_positives: int
    false_positives: int
    false_negatives: int
    true_negatives: int
    false_positive_ids: List[str]


def evaluate_soundex_baseline(pairs: Sequence[LabeledPair]) -> BaselineReport:
    """Predicts 'same entity' when the classic Soundex codes of the first words match."""
    tp = fp = fn = tn = 0
    fp_ids: List[str] = []
    for pair in pairs:
        if pair.same_entity is None:
            continue
        code_a, code_b = soundex(pair.mention), soundex(pair.candidate)
        predicted = bool(code_a) and code_a == code_b
        if pair.same_entity and predicted:
            tp += 1
        elif pair.same_entity:
            fn += 1
        elif predicted:
            fp += 1
            fp_ids.append(pair.id)
        else:
            tn += 1
    precision, recall = _ratio(tp, tp + fp), _ratio(tp, tp + fn)
    return BaselineReport(
        name="soundex(first word)",
        precision=precision,
        recall=recall,
        f1=_f1(precision, recall),
        true_positives=tp,
        false_positives=fp,
        false_negatives=fn,
        true_negatives=tn,
        false_positive_ids=fp_ids,
    )

