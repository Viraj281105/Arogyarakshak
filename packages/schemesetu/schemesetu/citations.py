"""
SchemeSetu — citation verification (Wave 2, stream B).

``verify_citation(sentence, hit)`` answers one narrow question: does the cited span contain
every figure and every scheme name the sentence asserts? It is a deterministic string check,
not a language-understanding one:

- figures: numbers (Devanagari digits normalised, Indian digit grouping removed, "lakh" /
  "crore" / लाख / करोड converted to absolute values) must each appear among the span's figures;
  that is how amounts, ages, dates and thresholds are checked;
- scheme names: each scheme the sentence names (PMJAY, MJPJAY, with aliases) must be named
  in the span;
- a sentence that asserts no figure and names no scheme is "uncheckable" and is never
  reported as supported.

What it does NOT do: judge whether the sentence's meaning follows from the span (negation,
"above" vs "below", who a figure applies to). A pass means "no unsupported number or scheme
name", not "the claim is true". The Devanagari scheme-name aliases are engineer-written and
NEED NATIVE-SPEAKER QA.

The ``hit`` argument is anything with a ``quote`` attribute (``kadi.retrieval.Hit`` fits).
"""

import re
import unicodedata
from decimal import Decimal
from typing import List, Protocol, Set

from pydantic import BaseModel

_DEVANAGARI_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")
_FOLD = {ord("़"): None, ord("ँ"): "ं"}
_UNIT = {
    "lakh": Decimal(100000), "lakhs": Decimal(100000), "lac": Decimal(100000), "lacs": Decimal(100000),
    "लाख": Decimal(100000),
    "crore": Decimal(10000000), "crores": Decimal(10000000),
    "करोड": Decimal(10000000), "करोड़": Decimal(10000000),
}
_FIGURE = re.compile(
    r"(?<![^\W_])(\d+(?:\.\d+)?)(?![^\W_\d])(?:\s*(lakhs?|lacs?|crores?|लाख|करोड़|करोड)(?![^\W_]))?",
)
_CITATION_KEY = re.compile(r"\[[^\]]*\]")
_GROUPED = re.compile(r"(?<=\d),(?=\d)")

# compact (letters/digits only, folded) alias -> canonical scheme label
_SCHEME_ALIASES = {
    "PMJAY": ("pmjay", "pradhanmantrijanarogyayojana", "ayushmanbharat", "आयुष्मानभारत"),
    "MJPJAY": ("mjpjay", "mahatmajyotiraophule", "महात्माज्योतिरावफुले", "महात्माजोतिरावफुले"),
}


class SpanLike(Protocol):
    quote: str


class CitedSpan(BaseModel):
    """A cited source span. Same shape as ``kadi.retrieval.Hit``."""

    source: str
    page: int
    quote: str
    score: float = 0.0


class CitationVerdict(BaseModel):
    status: str  # "supported" | "unsupported" | "uncheckable"
    checked_figures: List[str]
    missing_figures: List[str]
    checked_schemes: List[str]
    missing_schemes: List[str]
    reasons: List[str]

    @property
    def supported(self) -> bool:
        return self.status == "supported"


def _fold(text: str) -> str:
    t = unicodedata.normalize("NFKC", text or "")
    t = "".join(ch for ch in t if unicodedata.category(ch) != "Cf")
    t = t.translate(_DEVANAGARI_DIGITS).translate(_FOLD).casefold()
    return _GROUPED.sub("", t)


def _canonical(value: Decimal) -> str:
    s = format(value.normalize(), "f")
    return s


def extract_figures(text: str) -> Set[str]:
    """Canonical string values of every figure in ``text`` (citation keys like [PMJAY:S2] excluded)."""
    folded = _fold(_CITATION_KEY.sub(" ", text or ""))
    out: Set[str] = set()
    for m in _FIGURE.finditer(folded):
        value = Decimal(m.group(1))
        unit = m.group(2)
        if unit:
            value *= _UNIT[unit]
        out.add(_canonical(value))
    return out


def _compact(text: str) -> str:
    return "".join(ch for ch in _fold(text) if ch.isalnum() or ord(ch) in range(0x0900, 0x0980) and ch not in "।॥")


def _schemes_in(text: str) -> Set[str]:
    compact = _compact(_CITATION_KEY.sub(" ", text or ""))
    return {label for label, aliases in _SCHEME_ALIASES.items() if any(a in compact for a in aliases)}


def verify_citation(sentence: str, hit: SpanLike) -> CitationVerdict:
    quote = getattr(hit, "quote", "") or ""
    figures = extract_figures(sentence)
    schemes = _schemes_in(sentence)
    span_figures = extract_figures(quote)
    span_schemes = _schemes_in(quote)
    missing_figures = sorted(figures - span_figures, key=Decimal)
    missing_schemes = sorted(schemes - span_schemes)
    reasons: List[str] = []
    if not (sentence or "").strip():
        status = "unsupported"
        reasons.append("empty sentence")
    elif not quote.strip():
        status = "unsupported"
        reasons.append("cited span is empty")
    elif not figures and not schemes:
        status = "uncheckable"
        reasons.append("sentence asserts no figure and names no scheme, so nothing can be verified")
    elif missing_figures or missing_schemes:
        status = "unsupported"
        if missing_figures:
            reasons.append("figures not found in the cited span: " + ", ".join(missing_figures))
        if missing_schemes:
            reasons.append("schemes not named in the cited span: " + ", ".join(missing_schemes))
    else:
        status = "supported"
    return CitationVerdict(
        status=status,
        checked_figures=sorted(figures, key=Decimal),
        missing_figures=missing_figures,
        checked_schemes=sorted(schemes),
        missing_schemes=missing_schemes,
        reasons=reasons,
    )
