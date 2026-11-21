"""Per-case, in-memory retrieval index (BYOD / zero retention).

The index holds only chunks of the active case's already-redacted text and exists only in
process memory. ``purge()`` (or leaving the ``with`` block, including on an exception) drops
everything, after which the index refuses new documents and every search returns ``[]``.
Nothing is written to disk or logged. Hit quotes are untrusted data (see ``bm25``).
"""

from typing import List, Optional

from kadi.retrieval.bm25 import (
    DEFAULT_MAX_CHUNKS,
    DEFAULT_MAX_QUOTE_CHARS,
    DEFAULT_MIN_COVERAGE,
    DEFAULT_MIN_SCORE,
    DEFAULT_MIN_SCORE_RATIO,
    Bm25Index,
    Chunk,
    Hit,
)
from kadi.retrieval.chunking import DEFAULT_MAX_CHARS, DEFAULT_MAX_WORDS


class CaseRetrievalIndex(Bm25Index):
    def __init__(
        self,
        case_id: str,
        min_score: float = DEFAULT_MIN_SCORE,
        min_coverage: float = DEFAULT_MIN_COVERAGE,
        min_score_ratio: float = DEFAULT_MIN_SCORE_RATIO,
        max_chunks: int = DEFAULT_MAX_CHUNKS,
        max_quote_chars: int = DEFAULT_MAX_QUOTE_CHARS,
    ) -> None:
        super().__init__(
            min_score=min_score,
            min_coverage=min_coverage,
            min_score_ratio=min_score_ratio,
            max_chunks=max_chunks,
            max_quote_chars=max_quote_chars,
        )
        self.case_id = case_id
        self._purged = False

    @property
    def purged(self) -> bool:
        return self._purged

    def _check_open(self) -> None:
        if self._purged:
            raise RuntimeError("retrieval index for this case has been purged")

    def add(self, chunk: Chunk) -> None:
        with self._lock:
            self._check_open()
            super().add(chunk)

    def add_document(
        self,
        text: str,
        source: str,
        page: int,
        max_words: int = DEFAULT_MAX_WORDS,
        max_chars: int = DEFAULT_MAX_CHARS,
    ) -> int:
        with self._lock:
            self._check_open()
            return super().add_document(text, source, page, max_words=max_words, max_chars=max_chars)

    def search(self, query: str, k: int = 5) -> List[Hit]:
        with self._lock:
            if self._purged:
                return []
            return super().search(query, k)

    def purge(self) -> None:
        with self._lock:
            super().purge()
            self._purged = True

    def __enter__(self) -> "CaseRetrievalIndex":
        return self

    def __exit__(self, exc_type: Optional[type], exc: Optional[BaseException], tb: object) -> None:
        self.purge()
