"""Devanagari-aware tokenisation for clause retrieval.

The folding mirrors ``kadi.injection._matching_view`` (hidden characters removed, NFKC,
Devanagari digits to ASCII, nukta dropped, chandrabindu -> anusvara). It is copied here on
purpose rather than imported: the two modules are owned by different workstreams and the
retrieval index must not depend on the injection scanner. A parity test pins the two folds
together on a shared sample set.

Amounts are unit-aware: "5 lakh", "5-lakh", "5,00,000" and "500000" all become the single
token ``500000``; "1.5" and "1.50" become ``1.5``. Commas are removed only inside a valid
digit grouping (Western 1,000 or Indian 2,50,000), so "60,70" stays two numbers.

NEEDS NATIVE-SPEAKER QA: the Hindi and Marathi stop-word and unit lists below were written
by an engineer, not reviewed by a native speaker. Question words and particles only; no
content words.
"""

import re
import unicodedata
from decimal import Decimal, InvalidOperation
from typing import Dict, FrozenSet, List

MAX_TOKEN_CHARS = 64

_DEVANAGARI_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")
# Spelling variants folded for matching only: nukta dropped (ज़ -> ज), chandrabindu -> anusvara.
_FOLD = {ord("़"): None, ord("ँ"): "ं"}

# Western (1,000) and Indian (2,50,000) digit grouping; anything else is not a grouped number.
_GROUPED = re.compile(r"(?<![\d,])(?:\d{1,3}(?:,\d{3})+|\d{1,2}(?:,\d{2})+,\d{3})(?![\d,])")


def _strip_grouping(match: "re.Match[str]") -> str:
    return match.group(0).replace(",", "")


def fold(text: str) -> str:
    """Casefolded, hidden-character-free, digit- and spelling-folded view of ``text``."""
    t = unicodedata.normalize("NFKC", text or "")
    t = "".join(
        ch
        for ch in t
        if unicodedata.category(ch) != "Cf" and (unicodedata.category(ch) != "Cc" or ch in "\n\r\t")
    )
    t = t.translate(_DEVANAGARI_DIGITS).translate(_FOLD).casefold()
    return _GROUPED.sub(_strip_grouping, t)  # 2,50,000 -> 250000; 60,70 untouched


def _folded_set(words: str) -> FrozenSet[str]:
    return frozenset(fold(w) for w in words.split())


ENGLISH_STOPWORDS = _folded_set(
    "a an and are as at be but by for from has have in is it its of on or that the their this "
    "to was were what when which who will with how does do can why where i me my you your"
)
# NEEDS NATIVE-SPEAKER QA: engineer-written, unreviewed.
HINDI_STOPWORDS = _folded_set(
    "क्या है हैं का की के में से को पर और या मेरा मेरी मेरे हम आप यह वह इस उस कि ने तो भी था थी थे "
    "हो होता होती कैसे कब कहाँ कौन कितना कितने कितनी"
)
MARATHI_STOPWORDS = _folded_set(
    "आहे आहेत काय का की चा ची चे च्या मध्ये मी माझा माझी माझे आणि किंवा हे हा ही तो ते त्या या ला ना "
    "कसे केव्हा कुठे कोण किती होते होता"
)
STOPWORDS = ENGLISH_STOPWORDS | HINDI_STOPWORDS | MARATHI_STOPWORDS

_UNIT_VALUES: Dict[str, Decimal] = {
    "thousand": Decimal(1000), "हजार": Decimal(1000),
    "lakh": Decimal(100000), "lakhs": Decimal(100000), "lac": Decimal(100000), "lacs": Decimal(100000),
    "लाख": Decimal(100000),
    "crore": Decimal(10000000), "crores": Decimal(10000000), "करोड": Decimal(10000000),
    "करोड़": Decimal(10000000), "कोटी": Decimal(10000000),
}
UNITS: Dict[str, Decimal] = {fold(k): v for k, v in _UNIT_VALUES.items()}
_AMOUNT = re.compile(
    r"(?<![0-9a-z.])(\d{1,12}(?:\.\d{1,4})?)[-\s]{0,3}("
    + "|".join(sorted(map(re.escape, UNITS), key=len, reverse=True))
    + r")(?![^\W_])"
)
_DECIMAL_TOKEN = re.compile(r"\d{1,12}\.\d{1,4}")


def canonical_number(value: Decimal) -> str:
    return format(value.normalize(), "f")


def _amount(match: "re.Match[str]") -> str:
    try:
        return " " + canonical_number(Decimal(match.group(1)) * UNITS[match.group(2)]) + " "
    except (InvalidOperation, ArithmeticError):
        return match.group(0)


def _is_word_char(ch: str) -> bool:
    # Devanagari matras are combining marks (Mn/Mc), which str.isalnum() rejects; ZWJ/ZWNJ were
    # already removed by fold(), so a conjunct and its un-joined spelling tokenise identically.
    return ch.isalnum() or unicodedata.category(ch) in ("Mn", "Mc")


def tokenize(text: str, drop_stopwords: bool = False) -> List[str]:
    """Split into folded word tokens (each at most ``MAX_TOKEN_CHARS`` characters)."""
    t = _AMOUNT.sub(_amount, fold(text))
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
    out: List[str] = []
    for tok in tokens:
        if _DECIMAL_TOKEN.fullmatch(tok):
            tok = canonical_number(Decimal(tok))  # 1.50 -> 1.5, 2.0 -> 2
        out.append(tok[:MAX_TOKEN_CHARS])
    if drop_stopwords:
        out = [tok for tok in out if tok not in STOPWORDS]
    return out
