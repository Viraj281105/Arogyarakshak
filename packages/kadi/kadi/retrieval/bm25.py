"""Pure-Python, deterministic BM25 over in-memory chunks.

Kadi rule: retrieval only surfaces candidate clauses with a verbatim quote and a score. It
never decides anything, and when nothing qualifies it returns an empty list ("not found")
instead of a best guess.

SECURITY: ``Hit.quote`` and ``Hit.source`` are untrusted DATA (text from an uploaded
document). Callers must never treat them as instructions, put them in a prompt without the
"this is data" boundary, or log them; both are excluded from ``repr``.

Scoring (k1=1.5, b=0.75): idf = ln(1 + (N - n + 0.5) / (n + 0.5)), summed over the distinct
non-stop-word query terms. A chunk qualifies only if it clears ALL of:

- ``min_score``: an absolute floor (default 0, off);
- ``min_score_ratio``: its score must reach this fraction of the best score a chunk could get
  from this query, taken as the sum of the query terms' idf (an absent term counts with
  n = 0). Scaling to the query means a one-letter-rare term still works in a one-chunk index,
  which an absolute floor cannot do (with N=1 the maximum possible score is 0.29);
- ``min_coverage``: it must contain at least this share of the query's distinct content
  terms, and with one or two terms ALL of them ("PAN card" must not match "ration card").

Ties break on (source, page, chunk index), so output is stable. Limits (all loud, never silent
truncation of stored text): ``max_chunks`` per index; the query is cut to ``MAX_QUERY_CHARS`` /
``MAX_QUERY_TERMS`` and ``k`` to ``MAX_K`` (searching is read-only, so it truncates instead of
raising); a hit's quote is cut to ``max_quote_chars``.

Nothing here opens a file or a socket or logs document text (BYOD, zero retention). A
``threading.RLock`` makes add/search/purge safe to call from several threads.
"""

import heapq
import logging
import math
import threading
from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List

from kadi.retrieval.chunking import (
    DEFAULT_MAX_CHARS,
    DEFAULT_MAX_WORDS,
    Chunk,
    RetrievalLimitError,
    chunk_document,
)
from kadi.retrieval.tokens import tokenize

logger = logging.getLogger("arogyarakshak.retrieval")

K1 = 1.5
B = 0.75
DEFAULT_MIN_SCORE = 0.0
DEFAULT_MIN_SCORE_RATIO = 0.25
DEFAULT_MIN_COVERAGE = 0.5
DEFAULT_MAX_CHUNKS = 5000
MAX_QUERY_CHARS = 1000
MAX_QUERY_TERMS = 32
MAX_K = 100
DEFAULT_MAX_QUOTE_CHARS = DEFAULT_MAX_CHARS


@dataclass(frozen=True)
class Hit:
    source: str = field(repr=False)
    page: int
    quote: str = field(repr=False)
    score: float


class Bm25Index:
    def __init__(
        self,
        min_score: float = DEFAULT_MIN_SCORE,
        min_coverage: float = DEFAULT_MIN_COVERAGE,
        min_score_ratio: float = DEFAULT_MIN_SCORE_RATIO,
        max_chunks: int = DEFAULT_MAX_CHUNKS,
        max_quote_chars: int = DEFAULT_MAX_QUOTE_CHARS,
    ) -> None:
        self.min_score = min_score
        self.min_coverage = min_coverage
        self.min_score_ratio = min_score_ratio
        self.max_chunks = max_chunks
        self.max_quote_chars = max_quote_chars
        self._lock = threading.RLock()
        self._reset()

    def _reset(self) -> None:
        self._chunks: List[Chunk] = []
        self._tf: List[Counter] = []
        self._len: List[int] = []
        self._df: Dict[str, int] = {}
        self._postings: Dict[str, List[int]] = {}
        self._total_len = 0

    def __len__(self) -> int:
        return len(self._chunks)

    def __repr__(self) -> str:  # counts only, never content
        return f"<{type(self).__name__} chunks={len(self._chunks)}>"

    def add(self, chunk: Chunk) -> None:
        with self._lock:
            if len(self._chunks) >= self.max_chunks:
                raise RetrievalLimitError(f"index already holds the maximum of {self.max_chunks} chunks")
            self._add(chunk)

    def _add(self, chunk: Chunk) -> None:
        tokens = tokenize(chunk.text)
        tf = Counter(tokens)
        idx = len(self._chunks)
        self._chunks.append(chunk)
        self._tf.append(tf)
        self._len.append(len(tokens))
        self._total_len += len(tokens)
        for term in tf:
            self._df[term] = self._df.get(term, 0) + 1
            self._postings.setdefault(term, []).append(idx)

    def add_document(
        self,
        text: str,
        source: str,
        page: int,
        max_words: int = DEFAULT_MAX_WORDS,
        max_chars: int = DEFAULT_MAX_CHARS,
    ) -> int:
        """Chunk ``text`` and index every chunk; returns the number of chunks added.

        All-or-nothing: if the chunks would exceed ``max_chunks`` nothing is added and
        ``RetrievalLimitError`` is raised."""
        with self._lock:
            chunks = chunk_document(text, source, page, max_words=max_words, max_chars=max_chars)
            if len(self._chunks) + len(chunks) > self.max_chunks:
                raise RetrievalLimitError(
                    f"adding {len(chunks)} chunks would exceed the maximum of {self.max_chunks} per index"
                )
            for chunk in chunks:
                self._add(chunk)
            return len(chunks)

    def _required_terms(self, n_terms: int) -> int:
        if self.min_coverage <= 0:
            return 0
        if n_terms <= 2:
            return n_terms
        return math.ceil(self.min_coverage * n_terms - 1e-9)

    def search(self, query: str, k: int = 5) -> List[Hit]:
        """Top-``k`` qualifying chunks (see the module docstring); ``[]`` when none qualify."""
        with self._lock:
            terms = list(dict.fromkeys(tokenize((query or "")[:MAX_QUERY_CHARS], drop_stopwords=True)))
            terms = terms[:MAX_QUERY_TERMS]
            k = min(k, MAX_K)
            n_docs = len(self._chunks)
            if k <= 0 or not terms or n_docs == 0:
                return []
            avgdl = self._total_len / n_docs
            idf: Dict[str, float] = {}
            reference = 0.0
            for term in terms:
                n = self._df.get(term, 0)
                idf[term] = math.log(1 + (n_docs - n + 0.5) / (n + 0.5))
                reference += idf[term]
            floor = max(self.min_score, self.min_score_ratio * reference)
            required = self._required_terms(len(terms))
            scores: Dict[int, float] = {}
            matched: Dict[int, int] = {}
            for term in terms:
                for i in self._postings.get(term, ()):
                    f = self._tf[i][term]
                    norm = K1 * (1 - B + B * self._len[i] / avgdl) if avgdl else K1
                    scores[i] = scores.get(i, 0.0) + idf[term] * f * (K1 + 1) / (f + norm)
                    matched[i] = matched.get(i, 0) + 1
            candidates = []
            for i, score in scores.items():
                if score > 0 and score >= floor and matched[i] >= required:
                    c = self._chunks[i]
                    candidates.append((-score, c.source, c.page, c.index, i))
            best = heapq.nsmallest(k, candidates, key=lambda t: t[:4])
            hits = [
                Hit(self._chunks[i].source, self._chunks[i].page, self._chunks[i].text[: self.max_quote_chars], -neg)
                for neg, _s, _p, _x, i in best
            ]
            logger.debug("retrieval search: %d terms, %d chunks, %d hits", len(terms), n_docs, len(hits))
            return hits

    def purge(self) -> None:
        with self._lock:
            self._reset()
