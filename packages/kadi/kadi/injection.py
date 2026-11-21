"""
Prompt-injection hygiene for untrusted document text — English, Hindi, Marathi (#94).

Document text (OCR/PDF of a patient-uploaded file) is attacker-controlled and is never a
source of instructions. Two layers live here, shared by Kadi extraction and BillNyay's
agent prompts:

1. ``sanitise_for_prompt`` — removes characters that are invisible or reorder text and have
   no business in a bill or letter: zero-width space, BOM, soft hyphen, word joiner, bidi
   controls, Unicode "tag" characters and other format characters. The zero-width
   joiner / non-joiner are *kept* only between two Devanagari characters, where they change
   how conjuncts render (क्‍ष, र्‍य) and removing them would alter real words.
2. ``detect_injection_markers`` — best-effort phrase scan, now on a normalised *matching
   view* of the text so that hidden-character splitting ("ig​nore previous
   instructions"), full-width Latin and Devanagari spelling variants (nukta, chandrabindu,
   Devanagari digits) do not slip past, plus Hindi, Marathi and romanised-Hindi phrases.

Since v2 the matching view also folds a table of Cyrillic and Greek letters that look like
Latin ones (a Cyrillic ``о`` for the ``o`` in "ignore") back to Latin. That table is small and
hand-written, not the full Unicode confusables set: it covers the common lookalikes only.

What this is NOT: a guarantee. Prompt injection cannot be solved by pattern matching; a
reworded or translated attack will not match, a homoglyph outside the table is not folded,
and the measured detection / false-positive rates on the synthetic red-team corpus
(``data/evaluation/injection_redteam_*.jsonl``, reported by
``packages/kadi/tests/test_injection_redteam.py``) are the honest picture. The Hindi/Marathi phrase lists were written by the
engineering team and have NOT been reviewed by a native speaker (tracked in #37). Real
protection is architectural: schema-constrained output, an explicit "this is data"
boundary, and deterministic cross-checks (see ``kadi.extraction`` and
``billnyay.agents.prompt_safety``). A hit is disclosed for human review and never silently
changes extraction.
"""

import re
import unicodedata
from typing import List, Pattern

_ZWNJ = "‌"
_ZWJ = "‍"
_DEVANAGARI = range(0x0900, 0x0980)

_DEVANAGARI_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")
# Spelling variants folded in the matching view only (never in text sent to a model):
# nukta dropped (ज़ -> ज), chandrabindu -> anusvara.
_FOLD = {ord("़"): None, ord("ँ"): "ं"}

# Cyrillic and Greek letters that render like a Latin letter, folded to that letter in the
# matching view only. Applied BEFORE casefolding so capitals are handled (the table holds both
# cases). Hand-written and deliberately small; NOT the Unicode confusables table. A few are
# lookalikes only in capitals (Cyrillic н/в/т/м, Greek η/ν) and are folded for that reason, which
# can in principle turn a genuine Russian or Greek word into a Latin-looking one; the view is
# never sent to a model.
_CONFUSABLES = {
    # Cyrillic
    "а": "a", "в": "b", "с": "c", "ԁ": "d", "е": "e", "һ": "h", "н": "h", "і": "i", "ї": "i",
    "ј": "j", "к": "k", "ӏ": "l", "м": "m", "о": "o", "р": "p", "ԛ": "q", "ѕ": "s", "т": "t",
    "у": "y", "х": "x", "ԝ": "w", "ѵ": "v",
    # Greek
    "α": "a", "β": "b", "ε": "e", "ζ": "z", "η": "n", "ι": "i", "κ": "k", "μ": "m", "ν": "v",
    "ο": "o", "ρ": "p", "τ": "t", "υ": "u", "χ": "x",
    # Latin-extended lookalikes NFKC leaves alone
    "ı": "i", "ɑ": "a", "ɡ": "g", "ɩ": "i", "ɴ": "n", "ᴏ": "o",
}
# Upper-case keys are derived from the lower-case ones except where the capital looks like a
# different Latin letter than the small one (Greek capital Nu is "N", small nu is "v").
_CONFUSABLES.update({k.upper(): v for k, v in list(_CONFUSABLES.items())})
_CONFUSABLES.update({"Ν": "n", "Η": "h", "Υ": "y"})
_CONFUSABLE_TABLE = str.maketrans(_CONFUSABLES)


def _is_devanagari(ch: str) -> bool:
    return ord(ch) in _DEVANAGARI


def sanitise_for_prompt(text: str) -> str:
    """``text`` without invisible/reordering format characters (see module docstring).
    Ordinary text, Devanagari letters, matras and digits come back unchanged."""
    if not text:
        return text or ""
    out: List[str] = []
    n = len(text)
    for i, ch in enumerate(text):
        if ch in (_ZWJ, _ZWNJ):
            prev_ok = i > 0 and _is_devanagari(text[i - 1])
            next_ok = i + 1 < n and _is_devanagari(text[i + 1])
            if prev_ok and next_ok:
                out.append(ch)
            continue
        cat = unicodedata.category(ch)
        if cat == "Cf":
            continue
        if cat == "Cc" and ch not in "\n\r\t":
            continue
        out.append(ch)
    return "".join(out)


def hidden_character_count(text: str) -> int:
    """How many characters ``sanitise_for_prompt`` removes (for logging; not a verdict —
    PDFs legitimately carry soft hyphens and BOMs)."""
    return len(text or "") - len(sanitise_for_prompt(text or ""))


def _matching_view(text: str) -> str:
    """Lower-cased, hidden characters and joiners removed, NFKC (full-width Latin -> ASCII),
    Devanagari spelling variants and digits folded, Cyrillic/Greek Latin-lookalikes folded to
    Latin, whitespace collapsed."""
    t = unicodedata.normalize("NFKC", text or "")
    t = "".join(ch for ch in t if unicodedata.category(ch) != "Cf" and (unicodedata.category(ch) != "Cc" or ch in "\n\r\t"))
    t = t.translate(_DEVANAGARI_DIGITS).translate(_FOLD).translate(_CONFUSABLE_TABLE).casefold()
    return re.sub(r"\s+", " ", t)


_D = r"[ऀ-ॿ]"  # any Devanagari character, matras included (\w does not match matras)

ENGLISH_MARKER_PATTERNS: List[Pattern[str]] = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"ignore (all |the )?(previous|prior|above|preceding) instructions",
        # Requires "instructions/prompt/rules/directions" to follow — "disregard
        # previous medication" (a genuine, common clinical phrase) must not match on
        # "disregard previous" alone.
        r"disregard (all |the )?(previous|prior|above|preceding)\s+(instructions?|prompts?|rules?|directions?)",
        r"forget (everything|all) (you were told|above|prior)",
        r"new instructions\s*:",
        r"system prompt",
        r"you are now\b",
        r"act as (a|an)\b",
        r"\bDAN\b.{0,20}\bmode\b",
        r"output the following instead",
        r"do not (extract|follow|use) (the|your) (schema|instructions|rules)",
    ]
]

# Hindi and Marathi. Written against the folded matching view (no nukta, chandrabindu ->
# anusvara). Each ignore/forget phrase needs an instruction noun AND an ignoring verb, so
# ordinary text such as "पिछले निर्देशों के अनुसार दवा लें" ("take the medicine as per the
# earlier instructions") does not match.
DEVANAGARI_MARKER_PATTERNS: List[Pattern[str]] = [
    re.compile(p)
    for p in [
        # Hindi: "ignore (all) previous instructions"
        rf"(?:पिछले|पिछली|पहले\s+के|पूर्व|ऊपर\s+के|उपरोक्त|सभी|सारे)\s+(?:{_D}+\s+)?(?:निर्देश|आदेश|नियम){_D}*\s+(?:को\s+)?(?:अनदेखा|नजर\s*अंदाज|नजर\s*अन्दाज|भूल)",
        # Hindi: "new instructions:"
        rf"(?:नए|नये|नई|नवीन)\s+(?:निर्देश|आदेश){_D}*\s*[:：]",
        # Hindi / Marathi: "system prompt / system message"
        r"सिस्टम\s*(?:प्रॉम्प्ट|प्रोम्प्ट|प्रॉम्पट|संदेश)",
        # Hindi: "you act as ..."
        rf"(?:तुम|आप|तू)\s+(?:{_D}|\s){{0,30}}?के\s+रूप\s+में\s+(?:कार्य|काम|व्यवहार)\s*(?:करो|करें|कीजिए|कीजिये)(?!{_D})",
        # Hindi: "do not follow the instructions"
        rf"(?:निर्देश|नियम){_D}*\s+(?:का|के)\s+पालन\s+(?:न|मत)\s+{_D}+",
        # Hindi: "instead output the following"
        r"इसके\s+बजाय\s+निम्नलिखित",
        # Marathi: "ignore (all) previous instructions"
        rf"(?:मागील|मागच्या|आधीच्या|पूर्वीच्या|वरील|वरच्या|सर्व)\s+(?:{_D}+\s+)?(?:सूचना|आदेश|नियम){_D}*\s+(?:दुर्लक्ष|विसर)",
        # Marathi: "new instructions:"
        rf"(?:नवीन|नव्या)\s+(?:सूचना|आदेश){_D}*\s*[:：]",
        # Marathi: "you act as ..."
        rf"(?:तू|तुम्ही)\s+(?:आता\s+)?(?:{_D}|\s){{0,30}}?म्हणून\s+(?:वागा|वाग|काम\s+करा|काम\s+कर|कार्य\s+करा|कार्य\s+कर)(?!{_D})",
        # Marathi: "do not follow the instructions"
        rf"(?:सूचना|आदेश|नियम){_D}*\s+पालन\s+(?:करू|करु)\s+नका",
        # Marathi: "instead (output) the following"
        r"त्याऐवजी\s+(?:खालील|पुढील)",
    ]
]

# Hindi written in Latin script (common in chat-style text).
ROMANISED_HINDI_PATTERNS: List[Pattern[str]] = [
    re.compile(p)
    for p in [
        r"\b(?:pichh?le|purane|upar\s+ke|sabhi)\s+(?:sabhi\s+)?(?:nirdesh|instructions?|aadesh)\w*\s+(?:ko\s+)?(?:ignore|bhool|andekha|nazarandaz)",
    ]
]

ALL_MARKER_PATTERNS = ENGLISH_MARKER_PATTERNS + DEVANAGARI_MARKER_PATTERNS + ROMANISED_HINDI_PATTERNS


def detect_injection_markers(text: str) -> List[str]:
    """Matched phrases (from the normalised view, truncated to 80 characters) for
    disclosure. Never used to silently alter extraction behaviour."""
    view = _matching_view(text)
    found: List[str] = []
    for pattern in ALL_MARKER_PATTERNS:
        match = pattern.search(view)
        if match:
            found.append(match.group(0)[:80])
    return found
