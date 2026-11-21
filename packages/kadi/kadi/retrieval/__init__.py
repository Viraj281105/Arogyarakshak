"""Clause retrieval for Kadi: deterministic BM25 over per-case in-memory chunks.

Retrieval surfaces cited, verbatim quotes and returns an empty list when nothing qualifies.
It never decides eligibility, a verdict or a citation's correctness. Hit text is untrusted
document data.
"""

from kadi.retrieval.bm25 import (
    DEFAULT_MAX_CHUNKS,
    DEFAULT_MIN_COVERAGE,
    DEFAULT_MIN_SCORE,
    DEFAULT_MIN_SCORE_RATIO,
    Bm25Index,
    Hit,
)
from kadi.retrieval.case_index import CaseRetrievalIndex
from kadi.retrieval.chunking import Chunk, RetrievalLimitError, chunk_document
from kadi.retrieval.tokens import fold, tokenize

__all__ = [
    "Bm25Index",
    "CaseRetrievalIndex",
    "Chunk",
    "DEFAULT_MAX_CHUNKS",
    "DEFAULT_MIN_COVERAGE",
    "DEFAULT_MIN_SCORE",
    "DEFAULT_MIN_SCORE_RATIO",
    "Hit",
    "RetrievalLimitError",
    "chunk_document",
    "fold",
    "tokenize",
]
