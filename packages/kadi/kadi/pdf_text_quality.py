"""
Kadi: quality gate for a PDF page's embedded text layer.

Many Indian government PDFs store Devanagari through legacy fonts (Kruti/Chanakya-style
Latin look-alike codes) or through a glyph map that does not match Unicode. PyMuPDF then returns
text that *looks* like text but is unreadable (``jftLVªh``, ``विस्तावरत`` for ``विस्तारित``). Feeding
that to extraction produces confident nonsense, so a page whose layer fails this gate must not be
trusted: it is OCR'd (or skipped and reported), never used as extracted.

``assess_text_layer`` is a pure, deterministic heuristic over one page's text. It returns ratios
and a verdict only: the result never carries any of the document text, so it is safe to log.

Verdicts:
    ``clean``           Devanagari text that passes every check; the text layer can be used.
    ``corrupted``       The layer shows a legacy-font signature, malformed Devanagari, glyph
                        substitution, or (on long prose pages) almost no recognisable words.
    ``not_devanagari``  Latin-script or empty/near-empty text; nothing for this gate to reject.

Known limits (see docs/evaluation/devanagari-ocr.md): short corrupted cover pages, a page that
mixes clean and corrupted regions, corruption that yields valid-looking words, and Latin legacy
encodings on pages dominated by English-looking codes are not reliably caught. The thresholds
were tuned on six real public PDFs and hand-written unit cases only.
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
# Known-word check: only on long prose pages (short pages and tables have too few function
# words to judge), and only for prose-like line structure.
MIN_TOKENS_FOR_WORD_CHECK = 100
MIN_KNOWN_WORD_RATIO = 0.10
MIN_PROSE_LINE_RATIO = 0.5
PROSE_LINE_MIN_TOKENS = 6
MAX_MALFORMED_TOKEN_RATIO = 0.03
MAX_MIXED_TOKEN_RATIO = 0.05
MAX_STRAY_SCRIPT_RATIO = 0.02
MAX_GARBLED_LATIN_RATIO = 0.05
MIN_GARBLED_LATIN_TOKENS = 3
# A Latin legacy encoding with no Devanagari: most Latin tokens are vowel-less codes.
MIN_LATIN_TOKENS_FOR_CODE_CHECK = 8
MIN_CODE_TOKEN_RATIO = 0.5
CODE_TOKEN_MAX_VOWEL_SHARE = 0.2
# A page whose Latin tokens are mostly common English words is English, whatever its codes.
MIN_LATIN_TOKENS_FOR_ENGLISH = 8
MIN_ENGLISH_WORD_RATIO = 0.25

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
# Common Marathi/Hindi case endings; a token is "known" if it is a known word plus one of these.
_SUFFIXES = tuple(
    sorted(
        """चा ची चे च्या ने ला ना त तील मध्ये ात ाचा ाची ाचे ाच्या ाने ाला ास ांना ांच्या ांचे ांनी
        ाकडे कडून ेत ेचा ेची ेचे ेच्या ेने ेला ामुळे ें ों""".split(),
        key=len,
        reverse=True,
    )
)

# Small common-English list (billing, prescription and general words) used only to recognise an
# English page, never to judge Devanagari.
COMMON_ENGLISH = frozenset(
    """
    the and of to in for is on at by with from as or an be are was were this that it not no nil
    total amount patient room bed day days charges charge bill bills invoice cash card pay paid
    payable discount waiver date name age sex male female doctor dr tab tablet tablets cap capsule
    mg ml daily once twice after before food take syrup rent nursing admitted discharged hospital
    insurance insurer policy claim form please attach original schedule per all any not has have
    had will shall may must can your you we our us their they he she his her uses use app email id
    road street city state pin phone mobile number no address receipt tax gst service services
    fee fees test tests report reports medicine medicines drug drugs dose dosage advice follow
    review visit ward icu ot surgery procedure consultation visits room rent diet notes note
    signature stamp authorised authorized signed official copy page of balance due advance
    deposit refund net gross subtotal sub items item qty rate price unit units one two three four
    five six seven eight nine ten if then than when which who whom what where how why also only
    other such these those there here into over under between within without
    """.split()
)

_DEV_START, _DEV_END = 0x0900, 0x097F
_PUNCT_TO_STRIP = "।॥,.;:()[]{}\"'‘’“”-–—_?!/\\|*<>=+"

# Scripts that legacy-font corruption actually lands in (the glyph map falls into unrelated
# blocks: Balinese, Sundanese, Batak, Lepcha, Ol Chiki, Cyrillic Extended-C, Georgian Extended,
# Vedic Extensions, Devanagari Extended). Legitimate Indic scripts (Tamil, Gujarati, Bengali,
# Telugu, Kannada, Malayalam, Gurmukhi, ...) and Greek (mu in ug/mL) are NOT in this set.
_STRAY_RANGES = ((0x1B00, 0x1CFF), (0xA8E0, 0xA8FF))

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

# Latin legacy-font glyph codes. Strong signature: Latin-1 glyphs that legacy Devanagari fonts
# use but English never does, directly between letters (``jftLVªh``). Accented Latin letters
# (é ï ç), the degree/micro/plus-minus signs and Greek letters are legitimate and not listed.
_LEGACY_GLYPHS = "ªº¥ÐÝÞþðýöõ¨¯¿¡¢¤¦"
_GLYPH_TOKEN = re.compile(rf"[A-Za-z][{_LEGACY_GLYPHS}]|[{_LEGACY_GLYPHS}][A-Za-z]")
_LATIN_TOKEN = re.compile(r"[A-Za-z][A-Za-z¡-ÿ/\]\[`;'.&-]{2,}")
_VOWELS = frozenset("aeiouAEIOU")
_LIGATURES = {"ﬀ": "ff", "ﬁ": "fi", "ﬂ": "fl", "ﬃ": "ffi", "ﬄ": "ffl"}


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


def _is_stray_script(ch: str) -> bool:
    code = ord(ch)
    return any(lo <= code <= hi for lo, hi in _STRAY_RANGES)


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


def _is_known(token: str) -> bool:
    if token in KNOWN_WORDS:
        return True
    for suffix in _SUFFIXES:
        if token.endswith(suffix) and len(token) - len(suffix) >= 2 and token[: -len(suffix)] in KNOWN_WORDS:
            return True
    return False


def _vowel_share(token: str) -> float:
    letters = [c for c in token if c.isalpha()]
    if not letters:
        return 1.0
    return sum(1 for c in letters if c in _VOWELS) / len(letters)


def _garbled_shape(token: str) -> bool:
    """A Latin token shaped like a legacy-font code rather than English."""
    # ``vlk/kj.k``: a slash joins segments and one of them has no vowel (and/or, bed/day pass).
    if "/" in token:
        parts = [p for p in re.split(r"[/.]", token) if len(p) >= 2 and p.isalpha()]
        if any(_vowel_share(p) == 0 for p in parts):
            return True
    # ``c`gLifrokj``: a backtick between letters.
    if re.search(r"[A-Za-z]`[A-Za-z]", token):
        return True
    # ``fnYyh]`` : a closing bracket glued to letters with no opening bracket in the token.
    if re.search(r"[A-Za-z]\]", token) and "[" not in token:
        return True
    # ``jftLVh``: a vowel-less lowercase run of 2+ letters followed by a capital.
    match = re.match(r"^([a-z]{2,})[A-Z]", token)
    if match and _vowel_share(match.group(1)) == 0:
        return True
    return False


def assess_text_layer(text: str) -> TextLayerAssessment:
    """Classify one page's extracted text as ``clean``, ``corrupted`` or ``not_devanagari``."""
    text = text or ""
    for lig, plain in _LIGATURES.items():
        text = text.replace(lig, plain)
    text = unicodedata.normalize("NFC", text)

    dev = latin = stray = 0
    for ch in text:
        if _is_dev_letter(ch):
            dev += 1
        elif _is_stray_script(ch) and (ch.isalpha() or unicodedata.category(ch).startswith("M")):
            stray += 1
        elif ch.isalpha():
            latin += 1
    letters = dev + latin + stray
    devanagari_ratio = round(dev / letters, 4) if letters else 0.0

    latin_tokens = _LATIN_TOKEN.findall(text)
    n_latin = len(latin_tokens)
    words = [t.strip(_PUNCT_TO_STRIP + "`").lower() for t in latin_tokens]
    english = sum(1 for w in words if w in COMMON_ENGLISH)
    english_page = n_latin >= MIN_LATIN_TOKENS_FOR_ENGLISH and english / n_latin >= MIN_ENGLISH_WORD_RATIO

    glyph_tokens = sum(1 for t in latin_tokens if _GLYPH_TOKEN.search(t))
    shape_tokens = sum(1 for t in latin_tokens if _garbled_shape(t))
    code_tokens = sum(1 for t in latin_tokens if len(t) >= 4 and _vowel_share(t) < CODE_TOKEN_MAX_VOWEL_SHARE)
    legacy = bool(
        (stray >= 3 and stray / letters >= MAX_STRAY_SCRIPT_RATIO)
        or (
            glyph_tokens >= MIN_GARBLED_LATIN_TOKENS
            and glyph_tokens / max(1, n_latin) >= MAX_GARBLED_LATIN_RATIO
        )
        or (
            not english_page
            and (
                (
                    shape_tokens >= MIN_GARBLED_LATIN_TOKENS
                    and shape_tokens / max(1, n_latin) >= MAX_GARBLED_LATIN_RATIO
                )
                or (
                    n_latin >= MIN_LATIN_TOKENS_FOR_CODE_CHECK
                    and code_tokens / n_latin >= MIN_CODE_TOKEN_RATIO
                )
            )
        )
    )

    dev_tokens = _tokens_of_devanagari(text)
    n_tokens = len(dev_tokens)
    malformed = sum(
        1 for t in dev_tokens if _MALFORMED_START.search(t) or _MALFORMED_INSIDE.search(t)
    )
    mixed = sum(1 for t in text.split() if _MIXED_TOKEN.search(t.strip(_PUNCT_TO_STRIP)))
    known = sum(1 for t in dev_tokens if _is_known(t))
    known_ratio = round(known / n_tokens, 4) if n_tokens else 0.0
    malformed_ratio = round(malformed / n_tokens, 4) if n_tokens else 0.0
    mixed_ratio = round(mixed / n_tokens, 4) if n_tokens else 0.0

    dev_lines = [ln for ln in text.splitlines() if _tokens_of_devanagari(ln)]
    prose_lines = sum(1 for ln in dev_lines if len(_tokens_of_devanagari(ln)) >= PROSE_LINE_MIN_TOKENS)
    prose_like = bool(dev_lines) and prose_lines / len(dev_lines) >= MIN_PROSE_LINE_RATIO

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
        or (
            n_tokens >= MIN_TOKENS_FOR_WORD_CHECK
            and known_ratio < MIN_KNOWN_WORD_RATIO
            and prose_like
        )
    ):
        return build("corrupted")
    return build("clean")
