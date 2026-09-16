"""Signal combination and merge / ask-user / new-entity branching (#31)."""

import numpy as np
import pytest

from kadi.resolution.resolver import (
    CandidateEntity,
    EntityMention,
    ResolutionThresholds,
    combine_signals,
    resolve_mention,
)
from kadi.resolution.types import SignalScore


def _resolve(name, entity_type, *candidates, **kwargs):
    pool = [
        c if isinstance(c, CandidateEntity) else CandidateEntity(id=f"E{i}", name=c, entity_type=entity_type)
        for i, c in enumerate(candidates)
    ]
    return resolve_mention(EntityMention(name=name, entity_type=entity_type), pool, **kwargs)


class FixedEncoder:
    """Every pair gets the same cosine similarity."""

    model_id = "fixed"

    def __init__(self, cosine):
        self.cosine = cosine

    def encode(self, texts):
        angle = np.arccos(self.cosine)
        rows = [[1.0, 0.0]] + [[np.cos(angle), np.sin(angle)]] * (len(texts) - 1)
        return np.array(rows)


def test_noisy_or_combination_is_exact_and_ignores_unavailable_signals():
    signals = [
        SignalScore(signal="lexical", status="AVAILABLE", score=0.8),
        SignalScore(signal="phonetic", status="AVAILABLE", score=1.0),
        SignalScore(signal="semantic", status="UNAVAILABLE"),
    ]
    assert combine_signals(signals) == round(1 - (1 - 0.9 * 0.8) * (1 - 0.7 * 1.0), 4)
    assert combine_signals([SignalScore(signal="semantic", status="UNAVAILABLE")]) == 0.0


def test_spelling_variant_merges_into_the_existing_entity():
    decision = _resolve("Paracetmol", "medicine", "Paracetamol")
    assert decision.action == "MERGE"
    assert decision.matched_candidate_id == "E0"
    assert decision.thresholds.source == "default_uncalibrated"


def test_devanagari_mention_merges_with_latin_entity():
    decision = _resolve("क्रोसिन", "medicine", "Crocin")
    assert decision.action == "MERGE"
    lexical = next(s for s in decision.signals if s.signal == "lexical")
    assert "cross-script" in lexical.detail


def test_confirmed_alias_is_matched():
    candidate = CandidateEntity(id="E9", name="Crocin", entity_type="medicine", aliases=["क्रोसिन"])
    decision = resolve_mention(EntityMention(name="क्रोसिन", entity_type="medicine"), [candidate])
    assert decision.action == "MERGE"
    assert decision.matched_text == "क्रोसिन"


def test_billing_items_are_never_resolved_even_when_identical():
    decision = _resolve("Consultation charges", "billing_item", "Consultation charges")
    assert decision.action == "NEW"
    assert "never auto-resolved" in decision.reasons[0]


def test_blocking_by_type_and_empty_case():
    assert _resolve("Dengue", "diagnosis").action == "NEW"
    other_type = CandidateEntity(id="P1", name="Dengue", entity_type="procedure")
    decision = resolve_mention(EntityMention(name="Dengue", entity_type="diagnosis"), [other_type])
    assert decision.action == "NEW"
    assert decision.candidates_considered == 0


@pytest.mark.parametrize(
    "a,b,conflict",
    [
        ("Dolo 650", "Dolo 500", "quantity_conflict"),
        ("Tab Ondansetron 4 mg", "Inj Ondansetron 4 mg", "dosage_form_conflict"),
        ("Hepatitis A", "Hepatitis B", "variant_conflict"),
        ("Knee replacement (left)", "Knee replacement (right)", "laterality_conflict"),
        ("Hyperthyroidism", "Hypothyroidism", "opposing_prefix_conflict"),
        ("डोलो 650", "Dolo 500", "quantity_conflict"),
    ],
)
def test_conflicts_force_a_new_entity(a, b, conflict):
    entity_type = "procedure" if "Knee" in a else "diagnosis" if a.startswith("H") else "medicine"
    decision = _resolve(a, entity_type, b)
    assert decision.action == "NEW"
    assert conflict in decision.conflicts
    assert decision.matched_candidate_id is None


def test_look_alike_drug_goes_to_the_user_not_merged():
    decision = _resolve("Amoxicillin", "medicine", "Ampicillin")
    assert decision.action == "ASK"
    assert 0.70 <= decision.confidence < 0.90


def test_semantic_similarity_alone_asks_the_user():
    decision = _resolve("बुखार", "diagnosis", "Fever", encoder=FixedEncoder(0.9))
    assert decision.action == "ASK"
    assert "semantic" in decision.reasons[0]
    semantic = next(s for s in decision.signals if s.signal == "semantic")
    assert semantic.status == "AVAILABLE" and semantic.score == pytest.approx(0.9, abs=1e-3)


def test_semantic_similarity_alone_never_merges_even_with_low_thresholds():
    thresholds = ResolutionThresholds(merge=0.4, ask=0.3)
    decision = _resolve("बुखार", "diagnosis", "Fever", encoder=FixedEncoder(1.0), thresholds=thresholds)
    assert decision.confidence >= thresholds.merge
    assert decision.action == "ASK"
    assert "lexical or phonetic support" in decision.reasons[0]


def test_two_candidates_above_the_merge_threshold_is_ambiguous():
    decision = _resolve("Paracetamol", "medicine", "Paracetamol", "Tab Paracetamol")
    assert decision.action == "ASK"
    assert "more than one" in decision.reasons[0]


def test_calibrated_thresholds_change_the_branch():
    strict = ResolutionThresholds(merge=0.95, ask=0.90, source="feedback_calibrated", calibration_id="CAL-1")
    default_decision = _resolve("Crosin", "medicine", "Crocin")
    strict_decision = _resolve("Crosin", "medicine", "Crocin", thresholds=strict)
    assert default_decision.action == "MERGE"
    assert strict_decision.action == "ASK"
    assert strict_decision.thresholds.calibration_id == "CAL-1"


def test_thresholds_validate_ordering():
    with pytest.raises(ValueError):
        ResolutionThresholds(merge=0.6, ask=0.8)


def test_semantic_similarity_can_raise_a_pair_to_ask_but_never_to_merge():
    """Regression: with real IndicSBERT, Prednisone / Prednisolone (different drugs) crossed
    the merge threshold only because of embedding similarity."""
    lexical_only = _resolve("Prednisone", "medicine", "Prednisolone", enabled_signals=frozenset({"lexical", "phonetic"}))
    assert lexical_only.action == "ASK" and lexical_only.confidence < 0.90

    boosted = _resolve("Prednisone", "medicine", "Prednisolone", encoder=FixedEncoder(0.95))
    assert boosted.confidence >= 0.90
    assert boosted.action == "ASK"
    assert "never merge" in boosted.reasons[0]
