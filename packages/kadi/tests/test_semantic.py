"""Optional IndicSBERT semantic signal (#30), exercised with fake encoders.

The real model is covered by test_semantic_model.py, which is opt-in."""

import logging
import sys

import numpy as np
import pytest

from kadi.resolution import semantic
from kadi.resolution.resolver import CandidateEntity, EntityMention, resolve_mention
from kadi.resolution.semantic import (
    DISABLED_REASON,
    IndicSBERTEncoder,
    SemanticUnavailable,
    get_default_semantic_encoder,
    semantic_similarities,
)


class TableEncoder:
    model_id = "fake-table-encoder"

    def __init__(self, table):
        self.table = table
        self.calls = 0

    def encode(self, texts):
        self.calls += 1
        return np.array([self.table[t] for t in texts], dtype=float)


def test_cosine_scores_are_clipped_to_unit_interval():
    enc = TableEncoder({"q": [1, 0], "same": [2, 0], "orthogonal": [0, 1], "opposite": [-1, 0]})
    scores = semantic_similarities("q", ["same", "orthogonal", "opposite"], enc)
    assert [s.status for s in scores] == ["AVAILABLE"] * 3
    assert [s.score for s in scores] == [1.0, 0.0, 0.0]


def test_disabled_encoder_is_unavailable_not_zero():
    scores = semantic_similarities("बुखार", ["Fever"], None)
    assert scores[0].status == "UNAVAILABLE"
    assert scores[0].score is None
    assert scores[0].reason == DISABLED_REASON


def test_encoder_failures_are_unavailable_and_never_log_the_text(caplog):
    class Missing:
        model_id = "missing"

        def encode(self, texts):
            raise SemanticUnavailable("sentence-transformers is not installed")

    class Broken:
        model_id = "broken"

        def encode(self, texts):
            raise RuntimeError("boom")

    semantic._warned.clear()
    with caplog.at_level(logging.WARNING):
        missing = semantic_similarities("Ramesh diabetic foot", ["Diabetes"], Missing())
        broken = semantic_similarities("Ramesh diabetic foot", ["Diabetes"], Broken())
    assert missing[0].status == "UNAVAILABLE" and "not installed" in missing[0].reason
    assert broken[0].status == "UNAVAILABLE" and broken[0].reason == "semantic encoder failed"
    assert "Ramesh" not in caplog.text


def test_wrong_embedding_shape_is_unavailable():
    class Wrong:
        model_id = "wrong"

        def encode(self, texts):
            return np.zeros((1, 3))

    assert semantic_similarities("a", ["b", "c"], Wrong())[0].status == "UNAVAILABLE"


def test_default_encoder_respects_the_env_flag_and_does_not_load_eagerly(monkeypatch):
    monkeypatch.delenv("KADI_SEMANTIC_MATCHING", raising=False)
    assert get_default_semantic_encoder() is None

    monkeypatch.setenv("KADI_SEMANTIC_MATCHING", "true")
    encoder = get_default_semantic_encoder()
    assert isinstance(encoder, IndicSBERTEncoder)
    assert encoder.model_id == "l3cube-pune/indic-sentence-similarity-sbert"
    assert encoder._model is None  # nothing downloaded or loaded yet


def test_missing_dependency_raises_semantic_unavailable(monkeypatch):
    monkeypatch.setitem(sys.modules, "sentence_transformers", None)
    with pytest.raises(SemanticUnavailable, match="not installed"):
        IndicSBERTEncoder()._load()


def test_resolver_encodes_all_candidates_in_one_batch():
    enc = TableEncoder({"बुखार": [1, 0], "Fever": [0.9, 0.1], "Cough": [0, 1], "Headache": [0.1, 0.9]})
    candidates = [
        CandidateEntity(id=f"E{i}", name=name, entity_type="diagnosis")
        for i, name in enumerate(["Fever", "Cough", "Headache"])
    ]
    resolve_mention(EntityMention(name="बुखार", entity_type="diagnosis"), candidates, encoder=enc)
    assert enc.calls == 1
