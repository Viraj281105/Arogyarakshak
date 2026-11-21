"""Per-case, in-memory retrieval index (BYOD / zero retention).

The index holds only chunks of the active case's already-redacted text and exists only in
process memory. ``purge()`` (or leaving the ``with`` block) drops everything, after which
the index refuses new documents. Nothing is written to disk or logged.
"""

from typing import Optional

from kadi.retrieval.bm25 import DEFAULT_MIN_COVERAGE, DEFAULT_MIN_SCORE, Bm25Index, Chunk


class CaseRetrievalIndex(Bm25Index):
    def __init__(self, case_id: str, min_score: float = DEFAULT_MIN_SCORE, min_coverage: float = DEFAULT_MIN_COVERAGE) -> None:
        super().__init__(min_score=min_score, min_coverage=min_coverage)
        self.case_id = case_id
        self.purged = False

    def add(self, chunk: Chunk) -> None:
        if self.purged:
            raise RuntimeError("retrieval index for this case has been purged")
        super().add(chunk)

    def purge(self) -> None:
        super().purge()
        self.purged = True

    def __enter__(self) -> "CaseRetrievalIndex":
        return self

    def __exit__(self, exc_type: Optional[type], exc: Optional[BaseException], tb: object) -> None:
        self.purge()
