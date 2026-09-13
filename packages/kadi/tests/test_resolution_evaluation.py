"""Evaluation harness and regression floors on the curated synthetic pair set.

The fixture is synthetic and was used during development; these floors guard behaviour on
known hard cases, they are not accuracy claims."""

import json
from pathlib import Path

import pytest

from kadi.resolution.evaluation import (
    DatasetMeta,
    LabeledPair,
    evaluate_pairs,
    evaluate_soundex_baseline,
    load_labeled_pairs,
)

FIXTURE = Path(__file__).parent / "fixtures" / "entity_pairs_curated_synthetic.jsonl"
LEXICAL_PHONETIC = frozenset({"lexical", "phonetic"})


@pytest.fixture(scope="module")
def dataset():
    return load_labeled_pairs(FIXTURE)


def test_fixture_declares_itself_synthetic(dataset):
    meta, pairs = dataset
    assert meta.synthetic is True
    assert "NOT real-world accuracy" in meta.provenance
    assert len(pairs) == 100
    assert len({p.id for p in pairs}) == 100


def test_no_false_merges_on_hard_negatives(dataset):
    meta, pairs = dataset
    report = evaluate_pairs(pairs, meta, enabled_signals=LEXICAL_PHONETIC)
    assert report.false_merges == 0, report.false_merge_ids
    assert report.merge_precision == 1.0
    assert report.categories["hard_negative_dosage"].merge == 0
    assert report.categories["hard_negative_dosage"].ask == 0
    assert report.categories["non_resolvable_type"].new == 1


def test_transliteration_recall_floor(dataset):
    meta, pairs = dataset
    report = evaluate_pairs(pairs, meta, enabled_signals=LEXICAL_PHONETIC)
    assert report.merge_recall >= 0.70
    hindi = report.categories["transliteration_hindi"]
    marathi = report.categories["transliteration_marathi"]
    assert hindi.new == 0 and marathi.new == 0


def test_translations_need_the_semantic_signal(dataset):
    """Without IndicSBERT, pure translations (बुखार / Fever) are not caught at all."""
    meta, pairs = dataset
    report = evaluate_pairs(pairs, meta, enabled_signals=LEXICAL_PHONETIC)
    assert report.categories["translation"].merge == 0
    assert report.categories["translation"].ask == 0


def test_phonetic_signal_improves_on_lexical_only(dataset):
    meta, pairs = dataset
    lexical = evaluate_pairs(pairs, meta, enabled_signals=frozenset({"lexical"}))
    combined = evaluate_pairs(pairs, meta, enabled_signals=LEXICAL_PHONETIC)
    assert combined.merge_recall > lexical.merge_recall
    assert combined.false_merges == lexical.false_merges == 0


def test_soundex_baseline_produces_false_matches_that_conflict_rules_prevent(dataset):
    meta, pairs = dataset
    baseline = evaluate_soundex_baseline(pairs)
    assert baseline.false_positives > 0
    assert "ER-060" in baseline.false_positive_ids  # Dolo 650 vs Dolo 500


def test_metric_arithmetic_on_a_hand_computed_set():
    meta = DatasetMeta(name="tiny", synthetic=True, provenance="unit test")
    pairs = [
        LabeledPair(id="1", entity_type="medicine", mention="Paracetmol", candidate="Paracetamol", same_entity=True, category="t"),
        LabeledPair(id="2", entity_type="medicine", mention="Amoxicillin", candidate="Ampicillin", same_entity=False, category="t"),
        LabeledPair(id="3", entity_type="diagnosis", mention="बुखार", candidate="Fever", same_entity=True, category="t"),
        LabeledPair(id="4", entity_type="medicine", mention="Crocin", candidate="Paracetamol", same_entity=None, category="t"),
    ]
    report = evaluate_pairs(pairs, meta, enabled_signals=LEXICAL_PHONETIC)
    # 1: MERGE (TP); 2: ASK (TN); 3: NEW (FN, silent miss); 4: ambiguous, excluded.
    assert (report.true_positives, report.false_positives, report.false_negatives, report.true_negatives) == (1, 0, 1, 1)
    assert report.merge_precision == 1.0
    assert report.merge_recall == 0.5
    assert report.merge_f1 == round(2 * 1.0 * 0.5 / 1.5, 4)
    assert report.review_recall == 0.5
    assert report.silent_miss_ids == ["3"]
    assert report.ambiguous_pairs == 1
    assert report.ask_rate == 0.25


def test_dataset_without_provenance_is_rejected(tmp_path):
    path = tmp_path / "pairs.jsonl"
    path.write_text(json.dumps({"id": "1", "entity_type": "medicine", "mention": "a", "candidate": "b", "same_entity": True, "category": "x"}) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="provenance"):
        load_labeled_pairs(path)
