"""
SchemeSetu — citation verification (Wave 2, stream B).

``verify_citation(sentence, hit)`` answers one narrow question: does the cited span contain
every figure the sentence asserts, and does the span attribute those figures to the scheme the
sentence names? It is a deterministic string check, not a language-understanding one.

Statuses:
- ``supported``    at least one figure, every figure found in the span, every named scheme
                   attributed by the span, and no figure is attached to a different scheme;
- ``scheme_only``  the sentence names a scheme (found in the span) but asserts no figure, so
                   only the attribution was checked. Never reported as ``supported``;
- ``unsupported``  a figure is missing from the span, a named scheme is not attributed by it, or
                   a figure sits next to a different scheme in a span that names several;
- ``uncheckable``  nothing can be verified: no figure and no scheme, OR the sentence writes a
                   figure as a word ("five lakh", "पाँच लाख"), with an unrecognised unit ("5L",
                   "million"), or as an over-long number, OR it is too long. Never ``supported``.

Figures: Devanagari digits normalised, valid Indian/Western digit grouping removed, and
lakh / crore / thousand / लाख / करोड / कोटी / हजार converted to absolute values, so "5 lakh",
"5-lakh" and "5,00,000" are the same figure. Numbers are limited to 12 integer digits and 4
decimals (longer is ``uncheckable``), so arithmetic can neither raise nor round.

Scheme names are matched in the span BODY only: a ``CitedSpan`` carries its page title
separately (``title``) and the title is ignored, because one source page can name both
schemes. A span may declare which scheme it belongs to (``scheme``); a body that names several
schemes additionally requires each figure to sit within ``PROXIMITY_WINDOW`` characters of a
mention of the scheme the sentence names.

What it does NOT do: judge whether the sentence's meaning follows from the span (negation,
"above" vs "below", who a figure applies to beyond the proximity rule). A pass means "no
unsupported number and no misattributed scheme name", not "the claim is true". Only PMJAY and
MJPJAY are recognised scheme names; any other scheme name is invisible to the check. The
Devanagari scheme aliases and number words are engineer-written and NEED NATIVE-SPEAKER QA.
Hit/span text is untrusted document data.

The ``hit`` argument is anything with a ``quote`` attribute (``kadi.retrieval.Hit`` fits) and
optionally a ``scheme`` attribute.
"""

import re
import unicodedata
from decimal import Decimal, InvalidOperation
from typing import Dict, FrozenSet, List, Optional, Protocol, Set, Tuple

from pydantic import BaseModel

MAX_SENTENCE_CHARS = 5000
MAX_QUOTE_CHARS = 20000
MAX_INT_DIGITS = 12
MAX_FRACTION_DIGITS = 4
PROXIMITY_WINDOW = 150

_DEVANAGARI_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")
_FOLD = {ord("़"): None, ord("ँ"): "ं"}
_GROUPED = re.compile(r"(?<![\d,])(?:\d{1,3}(?:,\d{3})+|\d{1,2}(?:,\d{2})+,\d{3})(?![\d,])")
_CITATION_KEY = re.compile(r"\[[^\]]*\]")


def _fold(text: str) -> str:
    t = unicodedata.normalize("NFKC", text or "")
    t = "".join(ch for ch in t if unicodedata.category(ch) != "Cf")
    t = t.translate(_DEVANAGARI_DIGITS).translate(_FOLD).casefold()
    return _GROUPED.sub(lambda m: m.group(0).replace(",", ""), t)


def _folded_units() -> Dict[str, Decimal]:
    raw = {
        "thousand": 1000, "हजार": 1000,
        "lakh": 100000, "lakhs": 100000, "lac": 100000, "lacs": 100000, "लाख": 100000,
        "crore": 10000000, "crores": 10000000, "करोड": 10000000, "करोड़": 10000000, "कोटी": 10000000,
    }
    return {_fold(k): Decimal(v) for k, v in raw.items()}


_UNITS = _folded_units()
_UNIT_ALT = "|".join(sorted(map(re.escape, _UNITS), key=len, reverse=True))
_UNIT_AFTER = re.compile(r"[-\s]{0,3}(" + _UNIT_ALT + r")(?![^\W_])")
_ORDINAL_AFTER = re.compile(r"(?:st|nd|rd|th)(?![^\W_])")
_ABBREVIATED_AFTER = re.compile(r"[-\s]{0,3}(?:l|lk|lc|k|cr|m|mn|bn|million|billion|hundred)(?![^\W_])")
_LETTER_AFTER = re.compile(r"[^\W\d_]")
_DIGIT_RUN = re.compile(r"\d+(?:\.\d+)?")
_WORD = re.compile(r"[\wऀ-ॣ०-ॿ]+")

# NEEDS NATIVE-SPEAKER QA (Hindi and Marathi): engineer-written. A whole word from this list
# means the sentence states a number in words, which this check cannot verify.
_NUMBER_WORDS: FrozenSet[str] = frozenset(
    _fold(w)
    for w in (
        "one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen "
        "seventeen eighteen nineteen twenty thirty forty fifty sixty seventy eighty ninety hundred thousand "
        "lakh lakhs lac lacs crore crores million billion "
        "एक दो तीन चार पांच पाँच छह छः सात आठ नौ दस ग्यारह बारह तेरह चौदह पंद्रह सोलह सत्रह अठारह उन्नीस बीस तीस चालीस "
        "पचास साठ सत्तर अस्सी नब्बे सौ हजार हज़ार लाख करोड करोड़ अरब "
        "दोन पाच सहा नऊ दहा अकरा बारा तेरा चौदा पंधरा सोळा सतरा अठरा एकोणीस चाळीस पन्नास ऐंशी नव्वद शंभर कोटी"
    ).split()
)

# compact (letters/digits only, folded) alias -> canonical scheme label
_SCHEME_ALIASES = {
    "PMJAY": ("pmjay", "pradhanmantrijanarogyayojana", "ayushmanbharat", "आयुष्मानभारत"),
    "MJPJAY": ("mjpjay", "mahatmajyotiraophule", "महात्माज्योतिरावफुले", "महात्माजोतिरावफुले"),
}


class SpanLike(Protocol):
    quote: str


class CitedSpan(BaseModel):
    """A cited source span. ``quote`` is the BODY text; ``title`` is ignored by the verifier;
    ``scheme`` says which scheme the source is filed under. Same shape as ``kadi.retrieval.Hit``
    for the fields they share."""

    source: str
    page: int
    quote: str
    score: float = 0.0
    scheme: Optional[str] = None
    title: Optional[str] = None


class CitationVerdict(BaseModel):
    status: str  # "supported" | "scheme_only" | "unsupported" | "uncheckable"
    checked_figures: List[str]
    missing_figures: List[str]
    misattributed_figures: List[str] = []
    checked_schemes: List[str]
    missing_schemes: List[str]
    unverifiable: List[str] = []
    reasons: List[str]

    @property
    def supported(self) -> bool:
        return self.status == "supported"


def _canonical(value: Decimal) -> str:
    return format(value.normalize(), "f")


class _Scan:
    def __init__(self, text: str) -> None:
        self.folded = _fold(_CITATION_KEY.sub(" ", text or ""))
        self.positions: Dict[str, List[int]] = {}
        self.unverifiable: List[str] = []
        folded = self.folded
        keep: List[str] = []
        last = 0
        for m in _DIGIT_RUN.finditer(folded):
            keep.append(folded[last : m.start()])
            end = m.end()
            last = end
            whole, _, frac = m.group(0).partition(".")
            if len(whole) > MAX_INT_DIGITS or len(frac) > MAX_FRACTION_DIGITS:
                self.unverifiable.append("number with too many digits")
                continue
            try:
                value = Decimal(m.group(0))
                unit = _UNIT_AFTER.match(folded, end)
                if unit:
                    value *= _UNITS[unit.group(1)]
                    end = last = unit.end()
                elif _ORDINAL_AFTER.match(folded, end):
                    pass
                elif _ABBREVIATED_AFTER.match(folded, end) or _LETTER_AFTER.match(folded, end):
                    self.unverifiable.append(f"figure with an unrecognised unit: {m.group(0)}{folded[end:end + 6].strip()}")
                    continue
                self.positions.setdefault(_canonical(value), []).append(m.start())
            except (InvalidOperation, ArithmeticError):
                self.unverifiable.append("number that cannot be parsed")
        keep.append(folded[last:])
        rest = " ".join(keep)
        words = [w for w in _WORD.findall(rest) if w in _NUMBER_WORDS]
        if words:
            self.unverifiable.append("figure written in words: " + ", ".join(sorted(set(words))))

    @property
    def figures(self) -> Set[str]:
        return set(self.positions)


def extract_figures(text: str) -> Set[str]:
    """Canonical string values of every checkable figure in ``text`` (citation keys excluded)."""
    return _Scan((text or "")[:MAX_QUOTE_CHARS]).figures


def _compact_with_map(folded: str) -> Tuple[str, List[int]]:
    chars: List[str] = []
    index: List[int] = []
    for i, ch in enumerate(folded):
        if ch.isalnum() or unicodedata.category(ch) in ("Mn", "Mc"):
            chars.append(ch)
            index.append(i)
    return "".join(chars), index


def _mentions(folded: str) -> Dict[str, List[int]]:
    """scheme label -> positions (in ``folded``) where an alias of it occurs."""
    compact, index = _compact_with_map(folded)
    out: Dict[str, List[int]] = {}
    for label, aliases in _SCHEME_ALIASES.items():
        for alias in aliases:
            start = compact.find(alias)
            while start != -1:
                out.setdefault(label, []).append(index[start])
                start = compact.find(alias, start + 1)
    return out


def verify_citation(sentence: str, hit: SpanLike) -> CitationVerdict:
    """Check ``sentence`` against the cited span ``hit`` (see the module docstring). Never raises."""
    raw_quote = getattr(hit, "quote", None)
    quote = raw_quote if isinstance(raw_quote, str) else ""
    meta = getattr(hit, "scheme", None)
    sentence = sentence if isinstance(sentence, str) else ""

    def verdict(status: str, **kw) -> CitationVerdict:
        base = dict(checked_figures=[], missing_figures=[], checked_schemes=[], missing_schemes=[], reasons=[])
        base.update(kw)
        return CitationVerdict(status=status, **base)

    if not sentence.strip():
        return verdict("unsupported", reasons=["empty sentence"])
    if not quote.strip():
        return verdict("unsupported", reasons=["cited span is empty or has no text"])
    if len(sentence) > MAX_SENTENCE_CHARS:
        return verdict("uncheckable", unverifiable=["sentence too long to verify"], reasons=["sentence too long to verify"])

    s = _Scan(sentence)
    q = _Scan(quote[:MAX_QUOTE_CHARS])
    schemes = set(_mentions(s.folded))
    mentions = _mentions(q.folded)
    span_schemes = set(mentions) | ({meta} if meta in _SCHEME_ALIASES else set())

    figures = sorted(s.figures, key=Decimal)
    missing_figures = [f for f in figures if f not in q.positions]
    missing_schemes = sorted(schemes - span_schemes)
    misattributed: List[str] = []
    if not missing_figures and not missing_schemes and schemes and figures and len(span_schemes) > 1:
        near = [pos for label in schemes for pos in mentions.get(label, [])]
        for f in figures:
            if not any(abs(p - m) <= PROXIMITY_WINDOW for p in q.positions[f] for m in near):
                misattributed.append(f)

    reasons: List[str] = []
    if missing_figures:
        reasons.append("figures not found in the cited span: " + ", ".join(missing_figures))
    if missing_schemes:
        reasons.append("schemes not attributed by the cited span: " + ", ".join(missing_schemes))
    if misattributed:
        reasons.append("figures sit next to a different scheme in the cited span: " + ", ".join(misattributed))
    if missing_figures or missing_schemes or misattributed:
        status = "unsupported"
    elif s.unverifiable:
        status = "uncheckable"
        reasons.extend(s.unverifiable)
    elif figures:
        status = "supported"
    elif schemes:
        status = "scheme_only"
        reasons.append("sentence asserts no figure; only the scheme attribution was checked")
    else:
        status = "uncheckable"
        reasons.append("sentence asserts no figure and names no scheme, so nothing can be verified")
    return CitationVerdict(
        status=status,
        checked_figures=figures,
        missing_figures=missing_figures,
        misattributed_figures=misattributed,
        checked_schemes=sorted(schemes),
        missing_schemes=missing_schemes,
        unverifiable=list(s.unverifiable),
        reasons=reasons,
    )
