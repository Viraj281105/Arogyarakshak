"""Deterministic document chunking.

A chunk's ``text`` is always an exact slice of the input (never rewritten), so a retrieval
hit can quote the source verbatim. Paragraphs (blank-line separated) are kept whole when
they fit in ``max_words``; longer ones are packed sentence by sentence, and a single
over-long sentence is cut into word windows so no text is ever dropped.
"""

import re
from dataclasses import dataclass
from typing import List, Tuple

DEFAULT_MAX_WORDS = 80

_PARAGRAPH = re.compile(r"\S(?:.*?\S)?(?=\s*\n\s*\n|\s*$)", re.DOTALL)
# A sentence ends at . ! ? । ॥ followed by whitespace/end, so "1.50" and "Rs. 5" survive.
_SENTENCE = re.compile(r".+?(?:[.!?।॥]+(?=\s|$)|$)", re.DOTALL)
_WORD = re.compile(r"\S+")


@dataclass(frozen=True)
class Chunk:
    source: str
    page: int
    index: int
    text: str


def _units(text: str, start: int, end: int, max_words: int) -> List[Tuple[int, int, int]]:
    """(start, end, word_count) spans for the sentences of text[start:end], word-windowed if long."""
    out: List[Tuple[int, int, int]] = []
    for m in _SENTENCE.finditer(text, start, end):
        s, e = m.start(), m.end()
        while s < e and text[s].isspace():
            s += 1
        while e > s and text[e - 1].isspace():
            e -= 1
        if s >= e:
            continue
        words = [w for w in _WORD.finditer(text, s, e)]
        if len(words) <= max_words:
            out.append((s, e, len(words)))
        else:
            for i in range(0, len(words), max_words):
                group = words[i : i + max_words]
                out.append((group[0].start(), group[-1].end(), len(group)))
    return out


def chunk_document(text: str, source: str, page: int, max_words: int = DEFAULT_MAX_WORDS) -> List[Chunk]:
    """Split ``text`` into chunks of at most ``max_words`` words, in document order."""
    if max_words < 1:
        raise ValueError("max_words must be at least 1")
    text = text or ""
    chunks: List[Chunk] = []

    def emit(s: int, e: int) -> None:
        chunks.append(Chunk(source=source, page=page, index=len(chunks), text=text[s:e]))

    for para in _PARAGRAPH.finditer(text):
        ps, pe = para.start(), para.end()
        if len(_WORD.findall(text, ps, pe)) <= max_words:
            emit(ps, pe)
            continue
        cur_start = cur_end = -1
        cur_words = 0
        for s, e, n in _units(text, ps, pe, max_words):
            if cur_words and cur_words + n > max_words:
                emit(cur_start, cur_end)
                cur_words = 0
            if not cur_words:
                cur_start = s
            cur_end = e
            cur_words += n
        if cur_words:
            emit(cur_start, cur_end)
    return chunks
