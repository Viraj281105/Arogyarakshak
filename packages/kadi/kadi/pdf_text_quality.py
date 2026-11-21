"""
Kadi: quality gate for a PDF page's embedded text layer.

Many Indian government PDFs store Devanagari through legacy fonts (Kruti/Chanakya-style
Latin look-alike codes) or through a glyph map that does not match Unicode. PyMuPDF then returns
text that *looks* like text but is unreadable (``jftLVªh``, ``विस्तावरत`` for ``विस्तारित``). Feeding
that to extraction produces confident nonsense, so a page whose layer fails this gate must be
rasterised and OCR'd instead of trusted.

``assess_text_layer`` is a pure, deterministic heuristic over one page's text. It returns ratios
and a verdict only: the result never carries any of the document text, so it is safe to log.

Verdicts:
    ``clean``           Devanagari text that passes every check; the text layer can be used.
    ``corrupted``       The layer shows a legacy-font signature, malformed Devanagari, glyph
                        substitution, or almost no recognisable words; OCR it.
    ``not_devanagari``  Latin-script or empty/near-empty text; nothing for this gate to reject.

Limits (measured, not hidden): this is a heuristic. It can miss corruption that happens to produce
valid-looking Devanagari, and its word list is small. See docs/evaluation/devanagari-ocr.md.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Literal

Verdict = Literal["clean", "corrupted", "not_devanagari"]

# Fewer Devanagari tokens than this and the page is treated as not Devanagari content.
MIN_DEVANAGARI_TOKENS = 5
# Below this share of letters, a page is Latin/other content, not a Devanagari page.
MIN_DEVANAGARI_RATIO = 0.05
# The known-word check needs enough tokens to be meaningful.
MIN_TOKENS_FOR_WORD_CHECK = 40
MIN_KNOWN_WORD_RATIO = 0.12
MAX_MALFORMED_TOKEN_RATIO = 0.03
MAX_MIXED_TOKEN_RATIO = 0.05
MAX_STRAY_SCRIPT_RATIO = 0.02
MAX_GARBLED_LATIN_RATIO = 0.05
MIN_GARBLED_LATIN_TOKENS = 3

# High-frequency Hindi and Marathi function words and a few domain terms. Small on purpose:
# the ratio only has to separate prose from glyph soup. UNREVIEWED: NEEDS NATIVE-SPEAKER QA.
KNOWN_WORDS = frozenset(
    """
    के की का को में से पर और है हैं था थे थी हो होता होती होने कि जो यह इस उस वह एवं तथा या भी
    नहीं लिए साथ द्वारा अंतर्गत अनुसार किया किए गया गई गए जाएगा जाएगी सकता सकती करने करना कर करें
    करते हुए हुआ हुई तक वाले वाली वाला अधिक सभी कोई रूप राज्य सरकार योजना स्वास्थ्य बीमा दावा दावे
    कंपनी लाभ परिवार अस्पताल शिकायत आवेदन नाम तारीख दिनांक रुपये आयुष्मान भारत प्रधानमंत्री
    आरोग्य जन यदि ओर तो उसका
    आणि व ही हा हे ते ती त्या त्यांना त्यांच्या आहे आहेत होते होती नाही नये करण्यात
    करण्यासाठी येईल येत येणार शासन निर्णय क्रमांक महाराष्ट्र विभाग योजनेत योजनेच्या रुग्णालय
    रुग्णालये रुग्ण सोसायटी कामगार मंडळ रक्कम रकमेच्या नुसार संदर्भ सदर अंतर्गत यांना
    यांच्या यांचे पासून पर्यंत तसेच मात्र कडून साठी मध्ये वर खाली अशा असे असल्याने तथापि
    प्रमाणे वरील खालील सर्व एक दोन तीन
    """.split()
)

_DEV_START, _DEV_END = 0x0900, 0x097F
_PUNCT_TO_STRIP = "।॥,.;:()[]{}\"'‘’“”-–—_?!/\\|*<>=+"

# Dependent vowel signs (matras) U+093E..U+094C; U+0901..0903 are candrabindu/anusvara/visarga.
_MATRA = "ा-ौ"
_MALFORMED_INSIDE = re.compile(
    rf"[{_MATRA}][{_MATRA}]"  # two vowel signs in a row (anusvara after a matra is fine)
    rf"|्[{_MATRA}ऀ-ः]"  # virama followed by a vowel sign / nasal sign
    r"|ऄ"  # short A: absent from modern Hindi/Marathi, appears when glyphs are mis-mapped
)
_MALFORMED_START = re.compile(rf"^[{_MATRA}ऀ-ःऺऻ्]")
# A Latin letter next to Devanagari, a digit or odd punctuation sandwiched between Devanagari.
_MIXED_TOKEN = re.compile(
    r"[ऀ-ॿ][A-Za-z]|[A-Za-z][ऀ-ॿ]"
    r"|[ऀ-ॿ][0-9$'\"&;<>=@^*+|~`?#%][ऀ-ॿ]"
)
# Latin tokens that are legacy-font glyph codes: internal capitals, Latin-1 accented glyphs
# inside the word, or ``/ ] [ ` ;`` between letters (``vlk/kj.k``, ``jftLVªh``, ``c`gLifrokj``).
_GARBLED_LATIN = re.compile(
    r"[a-z][A-Z]|[A-Za-z][¡-¿À-ÿ]|[a-z][/\]\[`;][a-z]"
)
_LATIN_TOKEN = re.compile(r"[A-Za-z][A-Za-z¡-ÿ/\]\[`;'.&-]{3,}")


@dataclass(frozen=True)
class TextLayerAssessment:
    """Ratios and a verdict about one page's text layer. Never holds document text."""

    verdict: Verdict
    devanagari_ratio: float
    known_word_ratio: float
    legacy_font_signature: bool
    malformed_token_ratio: float = 0.0
    mixed_token_ratio: float = 0.0
    devanagari_tokens: int = 0


def _is_devanagari(ch: str) -> bool:
    return _DEV_START <= ord(ch) <= _DEV_END


def _is_dev_letter(ch: str) -> bool:
    # Letters, vowel signs and nasal signs; not digits or the danda punctuation.
    return _is_devanagari(ch) and ch not in "।॥" and not ("०" <= ch <= "९")


def _is_stray_script_letter(ch: str) -> bool:
    """A letter that is neither Devanagari nor Latin: the output of a font whose glyph map
    lands in unrelated Unicode blocks (Sundanese, Ol Chiki, Vedic extensions, ...)."""
    return (
        ord(ch) > 0x24F
        and not _is_devanagari(ch)
        and (ch.isalpha() or unicodedata.category(ch).startswith("M"))
    )


def _tokens_of_devanagari(text: str) -> list[str]:
    tokens = []
    for raw in text.split():
        word = raw.strip(_PUNCT_TO_STRIP)
        if not word:
            continue
        dev = sum(1 for c in word if _is_dev_letter(c))
        if dev and dev >= len(word) / 2:
            tokens.append(word)
    return tokens


def assess_text_layer(text: str) -> TextLayerAssessment:
    """Classify one page's extracted text as ``clean``, ``corrupted`` or ``not_devanagari``."""
    text = text or ""
    dev = latin = stray = 0
    for ch in text:
        if _is_dev_letter(ch):
            dev += 1
        elif ch.isascii():
            if ch.isalpha():
                latin += 1
        elif _is_stray_script_letter(ch):
            stray += 1
        elif ch.isalpha():  # Latin-1 / Latin Extended letters
            latin += 1
    letters = dev + latin + stray
    devanagari_ratio = round(dev / letters, 4) if letters else 0.0

    latin_tokens = _LATIN_TOKEN.findall(text)
    garbled = sum(1 for t in latin_tokens if _GARBLED_LATIN.search(t))
    legacy = bool(
        (stray >= 3 and stray / letters >= MAX_STRAY_SCRIPT_RATIO)
        or (
            garbled >= MIN_GARBLED_LATIN_TOKENS
            and garbled / max(1, len(latin_tokens)) >= MAX_GARBLED_LATIN_RATIO
        )
    )

    dev_tokens = _tokens_of_devanagari(text)
    n_tokens = len(dev_tokens)
    malformed = sum(
        1 for t in dev_tokens if _MALFORMED_START.search(t) or _MALFORMED_INSIDE.search(t)
    )
    mixed = sum(1 for t in text.split() if _MIXED_TOKEN.search(t.strip(_PUNCT_TO_STRIP)))
    known = sum(1 for t in dev_tokens if t in KNOWN_WORDS)
    known_ratio = round(known / n_tokens, 4) if n_tokens else 0.0
    malformed_ratio = round(malformed / n_tokens, 4) if n_tokens else 0.0
    mixed_ratio = round(mixed / n_tokens, 4) if n_tokens else 0.0

    def build(verdict: Verdict) -> TextLayerAssessment:
        return TextLayerAssessment(
            verdict=verdict,
            devanagari_ratio=devanagari_ratio,
            known_word_ratio=known_ratio,
            legacy_font_signature=legacy,
            malformed_token_ratio=malformed_ratio,
            mixed_token_ratio=mixed_ratio,
            devanagari_tokens=n_tokens,
        )

    if legacy:
        return build("corrupted")
    if n_tokens < MIN_DEVANAGARI_TOKENS or devanagari_ratio < MIN_DEVANAGARI_RATIO:
        return build("not_devanagari")
    if (
        (malformed >= 2 and malformed_ratio >= MAX_MALFORMED_TOKEN_RATIO)
        or (mixed >= 2 and mixed_ratio >= MAX_MIXED_TOKEN_RATIO)
        or (n_tokens >= MIN_TOKENS_FOR_WORD_CHECK and known_ratio < MIN_KNOWN_WORD_RATIO)
    ):
        return build("corrupted")
    return build("clean")
