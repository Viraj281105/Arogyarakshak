"""
Kadi entity resolution — rule-based Devanagari romanization (#89).

This is **not IndicXlit**. AI4Bharat's IndicXlit (`ai4bharat-transliteration`) depends
on fairseq, whose latest release ships wheels only for Python 3.6–3.8, so it cannot be
installed on this project's Python 3.11 stack (issue #29 stays open on that blocker).

What this module does instead is deterministic, table-driven romanization of Hindi and
Marathi text into a plain Latin form suitable for *matching* (not for display):

- consonants carry an inherent "a" unless followed by a virama or a vowel sign
- vowel signs (matras), independent vowels, anusvara/chandrabindu (nasal), visarga
- nukta consonants (ज़ -> z, फ़ -> f, क़ -> q, ड़ -> r)
- the Marathi/loanword vowel signs ॅ and ॉ (पॅरासिटामॉल -> "peraasitaamol")
- word-final schwa deletion (नमन -> "naman", not "namana")
- a simple medial schwa deletion heuristic (V C[a] C V: कमला -> "kamlaa")

Known lossy cases, by design: retroflex and dental consonants both map to t/d/n; the
nasal quality of anusvara is approximated as n (m before p/b/m); schwa deletion is a
heuristic and misses some words. Downstream phonetic keys (``kadi.resolution.phonetic``)
fold most of these differences away.
"""

from dataclasses import dataclass
from typing import List, Literal, Optional
import re
import unicodedata

ScriptName = Literal["latin", "devanagari", "mixed", "other", "none"]

_VIRAMA = "्"
_NUKTA = "़"
_ANUSVARA = "ं"
_CHANDRABINDU = "ँ"
_VISARGA = "ः"
_DANDAS = ("।", "॥")

INDEPENDENT_VOWELS = {
    "अ": "a", "आ": "aa", "इ": "i", "ई": "ii", "उ": "u", "ऊ": "uu", "ऋ": "ri", "ॠ": "rii",
    "ऌ": "li", "ए": "e", "ऐ": "ai", "ओ": "o", "औ": "au", "ऑ": "o", "ॲ": "e", "ऎ": "e",
    "ऒ": "o",
}

VOWEL_SIGNS = {
    "ा": "aa", "ि": "i", "ी": "ii", "ु": "u", "ू": "uu", "ृ": "ri", "ॄ": "rii", "े": "e",
    "ै": "ai", "ो": "o", "ौ": "au", "ॅ": "e", "ॉ": "o", "ॆ": "e", "ॊ": "o", "ॢ": "li",
}

CONSONANTS = {
    "क": "k", "ख": "kh", "ग": "g", "घ": "gh", "ङ": "ng",
    "च": "ch", "छ": "chh", "ज": "j", "झ": "jh", "ञ": "ny",
    "ट": "t", "ठ": "th", "ड": "d", "ढ": "dh", "ण": "n",
    "त": "t", "थ": "th", "द": "d", "ध": "dh", "न": "n", "ऩ": "n",
    "प": "p", "फ": "ph", "ब": "b", "भ": "bh", "म": "m",
    "य": "y", "र": "r", "ऱ": "r", "ल": "l", "ळ": "l", "ऴ": "l", "व": "v",
    "श": "sh", "ष": "sh", "स": "s", "ह": "h",
}

# Consonant + nukta. NFC/NFKC decompose the precomposed forms (U+0958–U+095F), so only the
# decomposed sequence needs handling.
NUKTA_CONSONANTS = {"क": "q", "ख": "kh", "ग": "g", "ज": "z", "ड": "r", "ढ": "rh", "फ": "f", "य": "y"}

_DEVANAGARI_DIGITS = "०१२३४५६७८९"
_DEVANAGARI_RUN = re.compile(r"[ऀ-ॿ‌‍]+")


@dataclass
class _Unit:
    consonant: Optional[str]
    vowel: Optional[str]
    explicit_vowel: bool
    nasal: bool = False
    visarga: bool = False


def _is_devanagari_letter(ch: str) -> bool:
    return "ऀ" <= ch <= "ॿ" and unicodedata.category(ch)[0] in ("L", "M")


def _is_latin_letter(ch: str) -> bool:
    return unicodedata.category(ch)[0] == "L" and "LATIN" in unicodedata.name(ch, "")


def detect_script(text: str) -> ScriptName:
    has_dev = has_lat = has_other = False
    for ch in text or "":
        if _is_devanagari_letter(ch):
            has_dev = True
        elif _is_latin_letter(ch):
            has_lat = True
        elif unicodedata.category(ch)[0] == "L":
            has_other = True
    if has_dev and has_lat:
        return "mixed"
    if has_dev:
        return "devanagari"
    if has_lat:
        return "latin"
    return "other" if has_other else "none"


def _delete_schwas(units: List[_Unit]) -> None:
    n = len(units)
    last = units[-1] if units else None
    if (
        n > 1
        and last.consonant
        and last.vowel == "a"
        and not last.explicit_vowel
        and not last.nasal
        and not last.visarga
    ):
        last.vowel = None

    for idx in range(1, n - 1):
        unit = units[idx]
        if not (unit.consonant and unit.vowel == "a" and not unit.explicit_vowel):
            continue
        if unit.nasal or unit.visarga:
            continue
        prev, nxt = units[idx - 1], units[idx + 1]
        if prev.vowel is None or not nxt.consonant or nxt.vowel is None:
            continue
        unit.vowel = None


def _render(units: List[_Unit]) -> str:
    out: List[str] = []
    for idx, unit in enumerate(units):
        out.append((unit.consonant or "") + (unit.vowel or ""))
        if unit.nasal:
            nxt = units[idx + 1] if idx + 1 < len(units) else None
            labial = nxt is not None and (nxt.consonant or "")[:1] in ("p", "b", "m")
            out.append("m" if labial else "n")
        if unit.visarga:
            out.append("h")
    return "".join(out)


def _romanize_run(run: str) -> str:
    words: List[str] = []
    units: List[_Unit] = []
    digits: List[str] = []

    def flush() -> None:
        if units:
            _delete_schwas(units)
            words.append(_render(units))
            units.clear()

    def flush_digits() -> None:
        if digits:
            words.append("".join(digits))
            digits.clear()

    i, n = 0, len(run)
    while i < n:
        ch = run[i]
        if ch in _DEVANAGARI_DIGITS:
            flush()
            digits.append(str(_DEVANAGARI_DIGITS.index(ch)))
            i += 1
            continue
        flush_digits()
        if ch in CONSONANTS:
            roman = CONSONANTS[ch]
            if i + 1 < n and run[i + 1] == _NUKTA:
                roman = NUKTA_CONSONANTS.get(ch, roman)
                i += 1
            unit = _Unit(consonant=roman, vowel="a", explicit_vowel=False)
            units.append(unit)
            i += 1
            if i < n and run[i] == _VIRAMA:
                unit.vowel = None
                i += 1
            elif i < n and run[i] in VOWEL_SIGNS:
                unit.vowel = VOWEL_SIGNS[run[i]]
                unit.explicit_vowel = True
                i += 1
            continue
        if ch in INDEPENDENT_VOWELS:
            units.append(_Unit(consonant=None, vowel=INDEPENDENT_VOWELS[ch], explicit_vowel=True))
        elif ch in VOWEL_SIGNS:
            # A vowel sign with no consonant before it (OCR noise); keep its sound.
            units.append(_Unit(consonant=None, vowel=VOWEL_SIGNS[ch], explicit_vowel=True))
        elif ch in (_ANUSVARA, _CHANDRABINDU):
            if units:
                units[-1].nasal = True
            else:
                units.append(_Unit(consonant="n", vowel=None, explicit_vowel=True))
        elif ch == _VISARGA:
            if units:
                units[-1].visarga = True
        elif ch in _DANDAS:
            flush()
        elif ch == "ॐ":
            units.append(_Unit(consonant=None, vowel="om", explicit_vowel=True))
        # Stray nukta/virama, avagraha and zero-width joiners carry no sound here.
        i += 1
    flush()
    flush_digits()
    return " ".join(w for w in words if w)


def romanize_devanagari(text: str) -> str:
    """Romanizes every Devanagari run in `text`; everything else passes through unchanged
    (casefolded). Digits in Devanagari are converted to ASCII digits."""
    s = unicodedata.normalize("NFKC", text or "")
    parts: List[str] = []
    last_end = 0
    for match in _DEVANAGARI_RUN.finditer(s):
        parts.append(s[last_end:match.start()])
        parts.append(_romanize_run(match.group(0)))
        last_end = match.end()
    parts.append(s[last_end:])
    return re.sub(r"\s+", " ", "".join(parts)).strip().casefold()
