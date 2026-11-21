"""Deterministic, linear-time document chunking.

A chunk's ``text`` is always an exact slice of the input (never rewritten), so a retrieval
hit can quote the source verbatim. Paragraphs (blank-line separated) are kept whole when they
fit in ``max_words`` words and ``max_chars`` characters; longer ones are packed sentence by
sentence, with the last sentence of a chunk repeated at the start of the next when it fits
(so a clause cut at a boundary is still whole in one chunk). A single over-long sentence is
cut into word windows, and a single over-long "word" is cut by characters, so no text is ever
dropped and no chunk exceeds the limits.

Every scan here is a single left-to-right pass: a sentence ends at ``. ! ? । ॥`` only when the
run of terminators (capped) is followed by whitespace or the end of the text, which keeps
"1.50", "Rs. 5" and "a.b.c" inside one sentence and keeps adversarial punctuation runs linear.

Limits are loud: a document larger than ``max_doc_chars`` raises ``RetrievalLimitError``.
"""

from dataclasses import dataclass, field
from typing import List, Tuple

DEFAULT_MAX_WORDS = 80
DEFAULT_MAX_CHARS = 1000
MAX_DOCUMENT_CHARS = 1_000_000
_MAX_TERMINATOR_RUN = 8
_TERMINATORS = ".!?।॥"
# Abbreviations after which a single '.' does not end a sentence ("Rs. 5,00,000").
_ABBREVIATIONS = frozenset(
    "rs no dr mr mrs ms sec art cl reg fig vs approx govt st e.g i.e".split()
)


class RetrievalLimitError(ValueError):
    """A configured size limit was exceeded; nothing was truncated or stored."""


@dataclass(frozen=True)
class Chunk:
    source: str
    page: int
    index: int
    text: str = field(repr=False)  # untrusted document text: never in logs or tracebacks


_Unit = Tuple[int, int, int, bool]  # start, end, words, overlappable (a whole sentence)


def _paragraphs(text: str) -> List[Tuple[int, int]]:
    """Spans of runs of non-blank lines, stripped. One pass over the lines."""
    spans: List[Tuple[int, int]] = []
    start = end = -1
    pos, n = 0, len(text)
    while pos <= n:
        nl = text.find("\n", pos)
        line_end = n if nl == -1 else nl
        line = text[pos:line_end]
        stripped = line.strip()
        if stripped:
            s = pos + (len(line) - len(line.lstrip()))
            e = s + len(stripped)
            if start == -1:
                start = s
            end = e
        elif start != -1:
            spans.append((start, end))
            start = -1
        if nl == -1:
            break
        pos = nl + 1
    if start != -1:
        spans.append((start, end))
    return spans


def _is_abbreviation(text: str, dot: int) -> bool:
    a = dot
    while a > 0 and dot - a < 16 and not text[a - 1].isspace():
        a -= 1
    token = text[a:dot].lstrip("(['\"")
    low = token.casefold()
    return low in _ABBREVIATIONS or (token.isdigit() and len(token) <= 3) or (len(token) == 1 and token.isalpha())


def _sentence_spans(text: str, start: int, end: int) -> List[Tuple[int, int]]:
    spans: List[Tuple[int, int]] = []
    s = i = start
    while i < end:
        if text[i] not in _TERMINATORS:
            i += 1
            continue
        j = i + 1
        while j < end and j - i < _MAX_TERMINATOR_RUN and text[j] in _TERMINATORS:
            j += 1
        boundary = j >= end or text[j].isspace()
        if boundary and j - i == 1 and text[i] == "." and _is_abbreviation(text, i):
            boundary = False
        if boundary:
            spans.append((s, j))
            while j < end and text[j].isspace():
                j += 1
            s = j
        i = j
    if s < end:
        spans.append((s, end))
    return spans


def _pieces(text: str, start: int, end: int, max_chars: int) -> List[Tuple[int, int]]:
    """Word spans of text[start:end]; a word longer than ``max_chars`` is cut by characters."""
    out: List[Tuple[int, int]] = []
    i = start
    while i < end:
        while i < end and text[i].isspace():
            i += 1
        j = i
        while j < end and not text[j].isspace():
            j += 1
        for k in range(i, j, max_chars):
            out.append((k, min(k + max_chars, j)))
        i = j
    return out


def _units(text: str, start: int, end: int, max_words: int, max_chars: int) -> List[_Unit]:
    units: List[_Unit] = []
    for s, e in _sentence_spans(text, start, end):
        pieces = _pieces(text, s, e, max_chars)
        if not pieces:
            continue
        if len(pieces) <= max_words and e - s <= max_chars:
            units.append((s, e, len(pieces), True))
            continue
        w_start, count = pieces[0][0], 0
        for idx, (ps, pe) in enumerate(pieces):
            if count and (count >= max_words or pe - w_start > max_chars):
                units.append((w_start, pieces[idx - 1][1], count, False))
                w_start, count = ps, 0
            count += 1
        units.append((w_start, pieces[-1][1], count, False))
    return units


def chunk_document(
    text: str,
    source: str,
    page: int,
    max_words: int = DEFAULT_MAX_WORDS,
    max_chars: int = DEFAULT_MAX_CHARS,
    max_doc_chars: int = MAX_DOCUMENT_CHARS,
) -> List[Chunk]:
    """Split ``text`` into chunks of at most ``max_words`` words / ``max_chars`` characters."""
    if max_words < 1 or max_chars < 1:
        raise ValueError("max_words and max_chars must be at least 1")
    text = text or ""
    if len(text) > max_doc_chars:
        raise RetrievalLimitError(f"document of {len(text)} characters exceeds the limit of {max_doc_chars}")
    chunks: List[Chunk] = []

    def emit(s: int, e: int) -> None:
        chunks.append(Chunk(source=source, page=page, index=len(chunks), text=text[s:e]))

    for ps, pe in _paragraphs(text):
        pieces = _pieces(text, ps, pe, max_chars)
        if len(pieces) <= max_words and pe - ps <= max_chars:
            emit(ps, pe)
            continue
        cur: List[_Unit] = []
        words = 0
        for unit in _units(text, ps, pe, max_words, max_chars):
            s, e, n, _ov = unit
            if cur and (words + n > max_words or e - cur[0][0] > max_chars):
                emit(cur[0][0], cur[-1][1])
                last = cur[-1]
                if last[3] and last[2] + n <= max_words and e - last[0] <= max_chars:
                    cur, words = [last], last[2]  # one-sentence overlap
                else:
                    cur, words = [], 0
            cur.append(unit)
            words += n
        if cur:
            emit(cur[0][0], cur[-1][1])
    return chunks
