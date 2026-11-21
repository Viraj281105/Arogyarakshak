"""Pure-Python, deterministic BM25 over in-memory chunks.

Kadi rule: retrieval only surfaces candidate clauses with a verbatim quote and a score. It
never decides anything, and when nothing scores at or above the floor it returns an empty
list ("not found") instead of a best guess.

Scoring (k1=1.5, b=0.75): idf = ln(1 + (N - n + 0.5) / (n + 0.5)), summed over the distinct
non-stop-word query terms. Ties break on (source, page, chunk index), so output is stable.

Nothing here opens a file, a socket or a log line containing document text (BYOD, zero
retention): the index is a plain in-memory object and ``purge()`` drops it.
"""

import logging
import math
from collections import Counter
from dataclasses import dataclass
from typing import Dict, List

from kadi.retrieval.chunking import DEFAULT_MAX_WORDS, Chunk, chunk_document
from kadi.retrieval.tokens import tokenize

logger = logging.getLogger("arogyarakshak.retrieval")

K1 = 1.5
B = 0.75
# Hits scoring below this are dropped. 1.0 is roughly "one moderately rare term matched";
# tuned against the synthetic gold sets (docs/evaluation/retrieval.md), not a universal value.
DEFAULT_MIN_SCORE = 1.0
# A chunk must also contain at least this share of the query's distinct content terms. Without
# it a single shared rare word ("card" in "PAN card" vs "ration card") clears any score floor.
DEFAULT_MIN_COVERAGE = 1 / 3


@dataclass(frozen=True)
class Hit:
    source: str
    page: int
    quote: str
    score: float


class Bm25Index:
    def __init__(self, min_score: float = DEFAULT_MIN_SCORE, min_coverage: float = DEFAULT_MIN_COVERAGE) -> None:
        self.min_score = min_score
        self.min_coverage = min_coverage
        self._chunks: List[Chunk] = []
        self._tf: List[Counter] = []
        self._len: List[int] = []
        self._df: Dict[str, int] = {}
        self._total_len = 0

    def __len__(self) -> int:
        return len(self._chunks)

    def add(self, chunk: Chunk) -> None:
        tokens = tokenize(chunk.text)
        tf = Counter(tokens)
        self._chunks.append(chunk)
        self._tf.append(tf)
        self._len.append(len(tokens))
        self._total_len += len(tokens)
        for term in tf:
            self._df[term] = self._df.get(term, 0) + 1

    def add_document(self, text: str, source: str, page: int, max_words: int = DEFAULT_MAX_WORDS) -> int:
        """Chunk ``text`` and index every chunk; returns the number of chunks added."""
        chunks = chunk_document(text, source, page, max_words=max_words)
        for chunk in chunks:
            self.add(chunk)
        return len(chunks)

    def search(self, query: str, k: int = 5) -> List[Hit]:
        """Top-``k`` chunks with score >= ``min_score`` that also cover >= ``min_coverage`` of the
        query terms; ``[]`` when none do."""
        terms = list(dict.fromkeys(tokenize(query, drop_stopwords=True)))
        n_docs = len(self._chunks)
        if k <= 0 or not terms or n_docs == 0:
            return []
        avgdl = self._total_len / n_docs
        scored = []
        for i, tf in enumerate(self._tf):
            score = 0.0
            matched = 0
            norm = K1 * (1 - B + B * self._len[i] / avgdl) if avgdl else K1
            for term in terms:
                f = tf.get(term)
                if not f:
                    continue
                matched += 1
                n = self._df[term]
                idf = math.log(1 + (n_docs - n + 0.5) / (n + 0.5))
                score += idf * f * (K1 + 1) / (f + norm)
            if score > 0 and score >= self.min_score and matched / len(terms) >= self.min_coverage:
                c = self._chunks[i]
                scored.append((-score, c.source, c.page, c.index, c))
        scored.sort(key=lambda s: s[:4])
        hits = [Hit(c.source, c.page, c.text, -neg) for neg, _s, _p, _i, c in scored[:k]]
        logger.debug("retrieval search: %d terms, %d chunks, %d hits", len(terms), n_docs, len(hits))
        return hits

    def purge(self) -> None:
        self._chunks = []
        self._tf = []
        self._len = []
        self._df = {}
        self._total_len = 0
