"""Devanagari-aware tokenisation for clause retrieval.

The folding mirrors ``kadi.injection._matching_view`` (hidden characters removed, NFKC,
Devanagari digits to ASCII, nukta dropped, chandrabindu -> anusvara). It is copied here on
purpose rather than imported: the two modules are owned by different workstreams and the
retrieval index must not depend on the injection scanner.

The English stop-word list is deliberately short. No Hindi or Marathi stop-words are
shipped: a list written by an engineer would be UNREVIEWED (NEEDS NATIVE-SPEAKER QA), and
BM25's idf already down-weights frequent terms.
"""

import re
import unicodedata
from typing import List

_DEVANAGARI_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")
# Spelling variants folded for matching only: nukta dropped (ज़ -> ज), chandrabindu -> anusvara.
_FOLD = {ord("़"): None, ord("ँ"): "ं"}
_GROUPED_NUMBER = re.compile(r"(?<=\d),(?=\d)")

ENGLISH_STOPWORDS = frozenset(
    "a an and are as at be but by for from has have in is it its of on or that the their this "
    "to was were what when which who will with".split()
)


def fold(text: str) -> str:
    """Casefolded, hidden-character-free, digit- and spelling-folded view of ``text``."""
    t = unicodedata.normalize("NFKC", text or "")
    t = "".join(
        ch
        for ch in t
        if unicodedata.category(ch) != "Cf" and (unicodedata.category(ch) != "Cc" or ch in "\n\r\t")
    )
    t = t.translate(_DEVANAGARI_DIGITS).translate(_FOLD).casefold()
    return _GROUPED_NUMBER.sub("", t)  # 2,50,000 -> 250000


def _is_word_char(ch: str) -> bool:
    # Devanagari matras are combining marks (Mn/Mc), which str.isalnum() rejects.
    return ch.isalnum() or unicodedata.category(ch) in ("Mn", "Mc")


def tokenize(text: str, drop_stopwords: bool = False) -> List[str]:
    """Split into folded word tokens. A '.' between two digits stays inside the token (1.50)."""
    t = fold(text)
    tokens: List[str] = []
    buf: List[str] = []
    for i, ch in enumerate(t):
        if _is_word_char(ch):
            buf.append(ch)
        elif ch == "." and buf and buf[-1].isdigit() and i + 1 < len(t) and t[i + 1].isdigit():
            buf.append(ch)
        elif buf:
            tokens.append("".join(buf))
            buf = []
    if buf:
        tokens.append("".join(buf))
    if drop_stopwords:
        tokens = [tok for tok in tokens if tok not in ENGLISH_STOPWORDS]
    return tokens
