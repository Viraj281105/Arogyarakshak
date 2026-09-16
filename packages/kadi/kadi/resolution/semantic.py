"""
Kadi entity resolution — cross-lingual semantic similarity via IndicSBERT (#30).

Model: ``l3cube-pune/indic-sentence-similarity-sbert`` (L3Cube Pune, CC-BY-4.0), loaded
through ``sentence-transformers``. It catches *translations* that no spelling or phonetic
rule can: बुखार / ताप ↔ fever, मधुमेह ↔ diabetes.

The signal is optional and **off by default**:

- the dependency is the ``kadi[semantic]`` extra (``sentence-transformers>=4.1,<5``)
- the model (~950 MB) is downloaded from the Hugging Face Hub on first use
- it is enabled only when ``KADI_SEMANTIC_MATCHING`` is ``true``/``1``/``yes``

When disabled, not installed, or failing to load, every semantic score is reported as
``UNAVAILABLE`` with a reason — it is never silently replaced by a fallback embedding,
and it never counts as evidence either way.

Embedding similarity is topical, not identity: two different analgesics can score high.
The resolver therefore never merges on semantic similarity alone (see
``kadi.resolution.resolver``).
"""

import logging
import os
import threading
from typing import List, Optional, Protocol, Sequence

import numpy as np
from pydantic import BaseModel

from kadi.resolution.types import SignalStatus

logger = logging.getLogger("Kadi.Resolution.Semantic")

MODEL_ID = "l3cube-pune/indic-sentence-similarity-sbert"
ENV_FLAG = "KADI_SEMANTIC_MATCHING"
_TRUTHY = {"1", "true", "yes", "on"}

_warned: set = set()


def _warn_once(reason: str) -> None:
    # Log the reason only — never the texts being compared.
    if reason not in _warned:
        _warned.add(reason)
        logger.warning("Semantic matching unavailable: %s", reason)


class SemanticUnavailable(RuntimeError):
    """The encoder cannot produce embeddings (dependency missing, model not loadable)."""


class SemanticEncoder(Protocol):
    model_id: str

    def encode(self, texts: Sequence[str]) -> np.ndarray:
        """Returns one L2-normalized embedding row per input text."""


class IndicSBERTEncoder:
    """Lazily loads IndicSBERT once per process; thread-safe."""

    def __init__(self, model_id: str = MODEL_ID, device: str = "cpu"):
        self.model_id = model_id
        self.device = device
        self._model = None
        self._lock = threading.Lock()

    def _load(self):
        if self._model is not None:
            return self._model
        with self._lock:
            if self._model is not None:
                return self._model
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as exc:
                raise SemanticUnavailable(
                    "sentence-transformers is not installed (install packages/kadi[semantic])"
                ) from exc
            try:
                self._model = SentenceTransformer(self.model_id, device=self.device)
            except Exception as exc:  # network, disk, corrupt cache
                raise SemanticUnavailable(f"model '{self.model_id}' could not be loaded") from exc
        return self._model

    def encode(self, texts: Sequence[str]) -> np.ndarray:
        model = self._load()
        return model.encode(
            list(texts),
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )


def semantic_matching_enabled() -> bool:
    return os.environ.get(ENV_FLAG, "").strip().lower() in _TRUTHY


_default_encoder: Optional[IndicSBERTEncoder] = None
_default_lock = threading.Lock()


def get_default_semantic_encoder() -> Optional[SemanticEncoder]:
    """The process-wide IndicSBERT encoder, or None when semantic matching is disabled."""
    global _default_encoder
    if not semantic_matching_enabled():
        return None
    with _default_lock:
        if _default_encoder is None:
            _default_encoder = IndicSBERTEncoder()
    return _default_encoder


class SemanticSimilarity(BaseModel):
    status: SignalStatus
    score: Optional[float] = None
    reason: str = ""


def _unavailable(reason: str) -> SemanticSimilarity:
    return SemanticSimilarity(status="UNAVAILABLE", score=None, reason=reason)


DISABLED_REASON = f"semantic matching disabled ({ENV_FLAG} is not enabled)"


def semantic_similarities(
    text: str, others: Sequence[str], encoder: Optional[SemanticEncoder]
) -> List[SemanticSimilarity]:
    """Cosine similarity (clipped to [0, 1]) between `text` and each of `others`, computed
    in one encoder batch."""
    if not others:
        return []
    if encoder is None:
        return [_unavailable(DISABLED_REASON) for _ in others]
    try:
        vectors = np.asarray(encoder.encode([text, *others]), dtype=float)
    except SemanticUnavailable as exc:
        _warn_once(str(exc))
        return [_unavailable(str(exc)) for _ in others]
    except Exception:
        _warn_once("semantic encoder raised an unexpected error")
        return [_unavailable("semantic encoder failed") for _ in others]

    if vectors.ndim != 2 or vectors.shape[0] != len(others) + 1:
        _warn_once("semantic encoder returned an unexpected shape")
        return [_unavailable("semantic encoder returned an unexpected shape") for _ in others]

    base = vectors[0]
    base_norm = np.linalg.norm(base)
    results: List[SemanticSimilarity] = []
    for row in vectors[1:]:
        denom = base_norm * np.linalg.norm(row)
        if denom == 0:
            results.append(_unavailable("empty embedding"))
            continue
        cosine = float(np.dot(base, row) / denom)
        results.append(
            SemanticSimilarity(
                status="AVAILABLE",
                score=round(min(max(cosine, 0.0), 1.0), 4),
                reason=getattr(encoder, "model_id", "encoder"),
            )
        )
    return results
