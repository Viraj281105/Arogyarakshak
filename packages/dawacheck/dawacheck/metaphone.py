"""
Double Metaphone — pure-Python phonetic encoder.

Standard implementation of Lawrence Philips' Double Metaphone algorithm (as popularized
by the public-domain reference ports). No third-party dependency: DawaCheck is installed
into a CPU-only CI/Docker image (see apps/api/constraints-cpu.txt), so a new pip package
for one algorithm is not worth the extra resolution surface.

Used to match brand-name spelling/OCR variants (e.g. "Amoxycillin" vs "Amoxicillin") to
the same reference ingredient without asserting the words are identical — callers must
still treat a phonetic match as lower-confidence than an exact/alias match.
"""

from typing import Tuple

VOWELS = set("AEIOU")


def _is_vowel(s: str, pos: int) -> bool:
    return 0 <= pos < len(s) and s[pos] in VOWELS


def _at(s: str, pos: int, length: int = 1) -> str:
    if pos < 0 or pos >= len(s):
        return ""
    return s[pos : pos + length]


def double_metaphone(word: str) -> Tuple[str, str]:
    """Returns (primary, secondary) phonetic codes for `word`.

    Secondary equals primary when the algorithm finds no plausible alternate
    pronunciation. Non-alphabetic characters are stripped before encoding.
    """
    original = "".join(ch for ch in word.upper() if ch.isalpha())
    if not original:
        return "", ""

    s = original
    length = len(s)
    first = 0
    last = length - 1

    primary: list = []
    secondary: list = []
    pos = 0

    # Skip these silent letter combinations at the start of the word.
    if _at(s, 0, 2) in ("GN", "KN", "PN", "WR", "PS"):
        pos += 1
    if _at(s, 0, 1) == "X":
        primary.append("S")
        secondary.append("S")
        pos += 1

    max_len = 32
    while pos < length and len(primary) < max_len:
        ch = s[pos]

        if ch in VOWELS:
            if pos == first:
                primary.append("A")
                secondary.append("A")
            pos += 1
            continue

        if ch == "B":
            primary.append("P")
            secondary.append("P")
            pos += 2 if _at(s, pos + 1) == "B" else 1
        elif ch == "C":
            if _at(s, pos, 4) == "CACH" and pos == 0:
                # e.g. "cache"-like sequence — falls through to normal CH handling below.
                pass
            if _at(s, pos + 1, 1) == "H":
                if pos > 0 and _at(s, pos - 1, 3) == "SCH":
                    primary.append("K")
                    secondary.append("K")
                else:
                    primary.append("X")
                    secondary.append("X")
                pos += 2
            elif _at(s, pos + 1, 1) in ("I", "E", "Y") and _at(s, pos, 3) != "CIA":
                primary.append("S")
                secondary.append("S")
                pos += 2
            else:
                primary.append("K")
                secondary.append("K")
                pos += 2 if _at(s, pos + 1, 1) == "C" else 1
        elif ch == "D":
            if _at(s, pos, 2) == "DG" and _at(s, pos + 2, 1) in ("I", "E", "Y"):
                primary.append("J")
                secondary.append("J")
                pos += 3
            else:
                primary.append("T")
                secondary.append("T")
                pos += 2 if _at(s, pos + 1, 1) == "D" else 1
        elif ch == "F":
            primary.append("F")
            secondary.append("F")
            pos += 2 if _at(s, pos + 1, 1) == "F" else 1
        elif ch == "G":
            if _at(s, pos + 1, 1) == "H":
                if pos > 0 and not _is_vowel(s, pos - 1):
                    pos += 2
                elif pos == 0:
                    if _at(s, pos + 2, 1) == "I":
                        primary.append("J")
                        secondary.append("J")
                    else:
                        primary.append("K")
                        secondary.append("K")
                    pos += 2
                else:
                    pos += 2
            elif _at(s, pos + 1, 1) == "N":
                pos += 2
            elif _at(s, pos + 1, 1) in ("I", "E", "Y"):
                primary.append("J")
                secondary.append("K")
                pos += 2
            else:
                primary.append("K")
                secondary.append("K")
                pos += 2 if _at(s, pos + 1, 1) == "G" else 1
        elif ch == "H":
            if _is_vowel(s, pos - 1) and _is_vowel(s, pos + 1):
                primary.append("H")
                secondary.append("H")
            pos += 1
        elif ch == "J":
            primary.append("J")
            secondary.append("H")
            pos += 2 if _at(s, pos + 1, 1) == "J" else 1
        elif ch == "K":
            primary.append("K")
            secondary.append("K")
            pos += 2 if _at(s, pos + 1, 1) == "K" else 1
        elif ch == "L":
            primary.append("L")
            secondary.append("L")
            pos += 2 if _at(s, pos + 1, 1) == "L" else 1
        elif ch == "M":
            primary.append("M")
            secondary.append("M")
            pos += 2 if _at(s, pos + 1, 1) == "M" else 1
        elif ch == "N":
            primary.append("N")
            secondary.append("N")
            pos += 2 if _at(s, pos + 1, 1) == "N" else 1
        elif ch == "P":
            if _at(s, pos + 1, 1) == "H":
                primary.append("F")
                secondary.append("F")
                pos += 2
            else:
                primary.append("P")
                secondary.append("P")
                pos += 2 if _at(s, pos + 1, 1) in ("P", "B") else 1
        elif ch == "Q":
            primary.append("K")
            secondary.append("K")
            pos += 2 if _at(s, pos + 1, 1) == "Q" else 1
        elif ch == "R":
            primary.append("R")
            secondary.append("R")
            pos += 2 if _at(s, pos + 1, 1) == "R" else 1
        elif ch == "S":
            if _at(s, pos + 1, 1) == "H":
                primary.append("X")
                secondary.append("X")
                pos += 2
            elif _at(s, pos, 3) in ("SIO", "SIA"):
                primary.append("S")
                secondary.append("X")
                pos += 3
            else:
                primary.append("S")
                secondary.append("S")
                pos += 2 if _at(s, pos + 1, 1) == "S" else 1
        elif ch == "T":
            if _at(s, pos, 3) in ("TIO", "TIA"):
                primary.append("S")
                secondary.append("X")
                pos += 3
            elif _at(s, pos + 1, 1) == "H":
                primary.append("0")
                secondary.append("T")
                pos += 2
            else:
                primary.append("T")
                secondary.append("T")
                pos += 2 if _at(s, pos + 1, 1) == "T" else 1
        elif ch == "V":
            primary.append("F")
            secondary.append("F")
            pos += 2 if _at(s, pos + 1, 1) == "V" else 1
        elif ch == "W":
            if _is_vowel(s, pos + 1):
                primary.append("F")
                secondary.append("F")
            pos += 1
        elif ch == "X":
            primary.append("KS")
            secondary.append("KS")
            pos += 1
        elif ch == "Y":
            if _is_vowel(s, pos + 1):
                primary.append("Y")
                secondary.append("Y")
            pos += 1
        elif ch == "Z":
            primary.append("S")
            secondary.append("S")
            pos += 2 if _at(s, pos + 1, 1) == "Z" else 1
        else:
            pos += 1

    p = "".join(primary)[:max_len]
    sec = "".join(secondary)[:max_len]
    return p, sec or p


def phonetic_codes_match(a: str, b: str) -> bool:
    """True when either code of `a` matches either code of `b` (both non-empty)."""
    pa, sa = double_metaphone(a)
    pb, sb = double_metaphone(b)
    candidates_a = {c for c in (pa, sa) if c}
    candidates_b = {c for c in (pb, sb) if c}
    return bool(candidates_a & candidates_b)
