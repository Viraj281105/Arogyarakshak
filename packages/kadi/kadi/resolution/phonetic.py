"""
Kadi entity resolution — cross-script phonetic matching for Indian names (#89).

Double Metaphone and Soundex were designed for English and fold the wrong things for
Hindi/Marathi names and Indian drug brands: Metaphone maps "bh" -> "P" and "th" -> "0",
and neither can read Devanagari at all. This module builds an Indic-aware key that works
on either script:

1. romanize Devanagari (``kadi.resolution.transliteration``; rule-based, not IndicXlit)
2. ``phonetic_normalize``: fold spelling variation common in Indian romanization —
   aspirates (bh/kh/gh/th/dh/jh -> b/k/g/t/d/j), sh/s, ph/f, w/v, q/k, x/ks, English c
   (k before a/o/u/consonants, s before e/i/y), vowel length (aa/ee/ii/oo/uu), ai/ei -> e,
   au -> o, doubled letters, silent final e, silent h, initial pn/ps/kn
3. ``indic_phonetic_key``: first letter (any initial vowel folded to "a") plus the
   consonant skeleton with vowels dropped and repeats collapsed

So "Crocin", "Crosin" and "क्रोसिन" share the key "krsn", and "Metformin" and "मेटफॉर्मिन"
share "mtfrmn", while "Metformin"/"Metoprolol" and "Amoxicillin"/"Ampicillin" do not.

Classic American Soundex is included only as an evaluation baseline.

Keys are evidence of similar pronunciation, never proof of identity: unrelated words can
collide, and the resolver never merges on a phonetic key alone when a quantity or dosage
form conflicts.
"""

import re
import unicodedata
from functools import lru_cache
from typing import FrozenSet, List, Optional

from pydantic import BaseModel

from kadi.resolution.similarity import GENERIC_STOPWORDS, core_tokens, levenshtein_ratio, tokenize
from kadi.resolution.transliteration import romanize_devanagari

# Partial credit for non-identical keys is halved: lexical and phonetic similarity are
# computed from the same strings, so full credit would double-count one piece of evidence.
PARTIAL_KEY_CREDIT = 0.5

_VOWELS = "aeiou"


def _normalize_word(w: str) -> str:
    w = re.sub(r"^ch(?=[lr])", "k", w)          # chlor-, chrom- are hard k
    w = re.sub(r"^p(?=[ns])", "", w)            # pneumonia, psoriasis
    w = re.sub(r"^k(?=n)", "", w)               # knee
    w = w.replace("chh", "\x01").replace("ch", "\x01")
    w = w.replace("ck", "k")
    w = re.sub(r"c(?=[eiy])", "s", w)
    w = w.replace("c", "k").replace("\x01", "c")
    w = re.sub(r"g(?=[eiy])", "j", w)            # soft g: "angioplasty" ~ "एंजियोप्लास्टी"
    w = w.replace("shh", "s").replace("sh", "s")
    w = w.replace("ph", "f")
    for aspirate, base in (("kh", "k"), ("gh", "g"), ("th", "t"), ("dh", "d"), ("bh", "b"), ("jh", "j"), ("rh", "r")):
        w = w.replace(aspirate, base)
    w = w.replace("q", "k").replace("x", "ks").replace("w", "v")
    w = re.sub(r"(?<=[^aeiou])y(?=[^aeiou]|$)", "i", w)
    w = re.sub(r"(?<=i)y(?=[aeiou])", "", w)     # glide: "nimoniya" ~ "pneumonia"
    w = re.sub(r"a{2,}", "a", w)
    w = re.sub(r"ee|ii", "i", w)
    w = re.sub(r"oo|uu", "u", w)
    w = re.sub(r"ai|ei|ay", "e", w)
    w = w.replace("au", "o")
    w = re.sub(r"([a-z])\1+", r"\1", w)
    if len(w) > 3 and w.endswith("e") and w[-2] not in _VOWELS:
        w = w[:-1]
    w = re.sub(r"(?<=.)h(?![aeiou])", "", w)
    return w


def phonetic_normalize(text: str) -> str:
    """Script-agnostic, vowel-preserving normalized form ("क्रोसिन" -> "krosin")."""
    roman = romanize_devanagari(text)
    decomposed = unicodedata.normalize("NFKD", roman)
    ascii_text = "".join(ch for ch in decomposed if not unicodedata.combining(ch)).casefold()
    words = re.findall(r"[a-z]+|\d+(?:\.\d+)?", ascii_text)
    normalized = [w if w[0].isdigit() else _normalize_word(w) for w in words]
    return " ".join(w for w in normalized if w)


def indic_phonetic_key(text: str) -> str:
    """Consonant-skeleton key, one segment per word ("Type 2 diabetes" -> "tp 2 dbts")."""
    segments = []
    for word in phonetic_normalize(text).split():
        if word[0].isdigit():
            segments.append(word)
            continue
        head = "a" if word[0] in _VOWELS else word[0]
        skeleton = head + re.sub(f"[{_VOWELS}]", "", word[1:])
        segments.append(re.sub(r"([a-z])\1+", r"\1", skeleton))
    return " ".join(segments)


_SOUNDEX_CODES = {
    **dict.fromkeys("bfpv", "1"),
    **dict.fromkeys("cgjkqsxz", "2"),
    **dict.fromkeys("dt", "3"),
    "l": "4",
    **dict.fromkeys("mn", "5"),
    "r": "6",
}


def soundex(text: str) -> str:
    """Classic American Soundex of the first word (after romanization). Baseline only."""
    letters = re.findall(r"[a-z]+", romanize_devanagari(text))
    if not letters:
        return ""
    word = letters[0]
    first = word[0].upper()
    code = []
    previous = _SOUNDEX_CODES.get(word[0], "")
    for ch in word[1:]:
        digit = _SOUNDEX_CODES.get(ch, "")
        if digit and digit != previous:
            code.append(digit)
        if ch not in "hw":
            previous = digit
    return (first + "".join(code) + "000")[:4]


@lru_cache(maxsize=32)
def normalized_stopwords(stopwords: FrozenSet[str]) -> FrozenSet[str]:
    return frozenset(phonetic_normalize(s) for s in stopwords) | stopwords


def core_phonetic_keys(
    text: str, stopwords: FrozenSet[str] = GENERIC_STOPWORDS, fuzzy_stopwords: bool = False
) -> List[str]:
    """Sorted phonetic keys of the identifying tokens only: numbers, units, dosage forms
    and stopwords (in either script) are excluded, so "Tab Paracetamol 650mg" and
    "पॅरासिटामॉल" both reduce to ["prstml"]."""
    normalized_stops = normalized_stopwords(stopwords)
    keys = []
    for token in core_tokens(tokenize(romanize_devanagari(text)), stopwords):
        if core_tokens([phonetic_normalize(token)], normalized_stops, fuzzy_stopwords) == []:
            continue
        key = indic_phonetic_key(token)
        if re.search(r"[a-z]", key):
            keys.append(key)
    return sorted(keys)


class PhoneticSimilarity(BaseModel):
    key_a: str
    key_b: str
    score: Optional[float]
    keys_equal: bool


def phonetic_similarity(
    a: str, b: str, stopwords: FrozenSet[str] = GENERIC_STOPWORDS, fuzzy_stopwords: bool = False
) -> PhoneticSimilarity:
    """Word-order-insensitive comparison of core phonetic keys.

    1.0 when both sides have the same multiset of keys; otherwise
    PARTIAL_KEY_CREDIT * max(Levenshtein ratio of the joined keys, key-set Jaccard).
    `score` is None when either side has no identifying token (e.g. "650 mg").
    """
    keys_a = core_phonetic_keys(a, stopwords, fuzzy_stopwords)
    keys_b = core_phonetic_keys(b, stopwords, fuzzy_stopwords)
    key_a, key_b = " ".join(keys_a), " ".join(keys_b)
    if not keys_a or not keys_b:
        return PhoneticSimilarity(key_a=key_a, key_b=key_b, score=None, keys_equal=False)
    if keys_a == keys_b:
        return PhoneticSimilarity(key_a=key_a, key_b=key_b, score=1.0, keys_equal=True)
    set_a, set_b = set(keys_a), set(keys_b)
    jaccard = len(set_a & set_b) / len(set_a | set_b)
    score = PARTIAL_KEY_CREDIT * max(levenshtein_ratio(key_a, key_b), jaccard)
    return PhoneticSimilarity(key_a=key_a, key_b=key_b, score=round(score, 4), keys_equal=False)
