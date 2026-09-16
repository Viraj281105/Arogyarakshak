"""Real IndicSBERT model checks (#30). Opt-in: they need packages/kadi[semantic], torch >= 2.6
and the ~950 MB model (downloaded from the Hugging Face Hub on first run).

    KADI_RUN_MODEL_TESTS=1 python -m pytest packages/kadi/tests/test_semantic_model.py
"""

import os

import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("KADI_RUN_MODEL_TESTS") != "1",
    reason="real IndicSBERT model test; set KADI_RUN_MODEL_TESTS=1 to run",
)


@pytest.fixture(scope="module")
def encoder():
    from kadi.resolution.semantic import IndicSBERTEncoder

    return IndicSBERTEncoder()


def test_model_loads_and_returns_normalized_embeddings(encoder):
    import numpy as np

    vectors = encoder.encode(["fever", "बुखार"])
    assert vectors.shape[0] == 2
    assert np.allclose(np.linalg.norm(vectors, axis=1), 1.0, atol=1e-4)


@pytest.mark.parametrize(
    "mention,translation,distractors",
    [
        ("बुखार", "fever", ["headache", "fracture"]),
        ("मधुमेह", "diabetes", ["hypertension", "fracture"]),
        ("खोकला", "cough", ["fever", "fracture"]),
    ],
)
def test_translation_scores_above_distractors(encoder, mention, translation, distractors):
    from kadi.resolution.semantic import semantic_similarities

    scores = semantic_similarities(mention, [translation, *distractors], encoder)
    assert all(s.status == "AVAILABLE" for s in scores)
    assert scores[0].score > max(s.score for s in scores[1:])


def test_real_semantic_signal_never_auto_merges_a_translation(encoder):
    from kadi.resolution.resolver import CandidateEntity, EntityMention, resolve_mention

    decision = resolve_mention(
        EntityMention(name="बुखार", entity_type="diagnosis"),
        [CandidateEntity(id="E1", name="Fever", entity_type="diagnosis")],
        encoder=encoder,
    )
    assert decision.action in ("ASK", "NEW")


def test_real_semantic_signal_adds_no_false_merges_on_the_synthetic_set(encoder):
    from pathlib import Path

    from kadi.resolution.evaluation import evaluate_pairs, load_labeled_pairs

    meta, pairs = load_labeled_pairs(Path(__file__).parent / "fixtures" / "entity_pairs_curated_synthetic.jsonl")
    report = evaluate_pairs(pairs, meta, encoder=encoder)
    assert report.semantic_status == "AVAILABLE"
    assert report.false_merges == 0, report.false_merge_ids
