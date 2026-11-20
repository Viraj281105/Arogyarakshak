"""
Hindi / Marathi terminology audit (#37) — mechanical checks over the app's copy.

This does NOT replace a native-speaker review and never decides which word is right. It
finds what a machine can find reliably and puts the evidence in front of a reviewer:

* ``spelling_variants``   one word written two ways in the same language (जाँच / जांच)
* ``glossary_conflicts``  one concept rendered with two different terms in the same language
                          (Marathi "government": सरकारी / शासकीय), across UI copy AND letters
* ``language_leakage``    Hindi-only function words in Marathi text and the reverse
* ``english_words``       Latin-script words left in Hindi/Marathi text (minus an allow-list)
* ``untranslated``        Hindi/Marathi text identical to the English source
* ``placeholder_mismatch`` ``{name}`` / ``%s`` slots that differ from the English source

The glossary (``data/terminology/glossary.json``) and the leakage/allow lists are written by
the engineering team and are UNREVIEWED; a conflict means "two terms are in use, a reviewer
should pick or accept both", not "one is wrong". Pure functions, no I/O.
"""

import re
import unicodedata
from collections import defaultdict
from typing import Any, Dict, Iterable, List, NamedTuple, Optional, Sequence, Set, Tuple

# U+0964/0965 (danda, double danda) are punctuation, not part of a word
DEVANAGARI_WORD = re.compile(r"[ऀ-ॣ०-ॿ]+")
LATIN_WORD = re.compile(r"[A-Za-z][A-Za-z0-9'’\-]*")
PLACEHOLDER = re.compile(r"\{[^{}]*\}|%[sd]|\$\{[^}]*\}")

_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")
# nasal conjunct <-> anusvara spelling pairs (approximate, deliberately small)
_NASALS = {"न्द": "ंद", "न्त": "ंत", "न्ध": "ंध", "म्ब": "ंब", "म्प": "ंप", "ङ्क": "ंक", "ङ्ग": "ंग", "ञ्च": "ंच", "ण्ड": "ंड"}


class Entry(NamedTuple):
    source: str
    key: str
    lang: str
    text: str


def fold(text: str) -> str:
    """Spelling-insensitive form: NFKC, joiners and nukta removed, chandrabindu -> anusvara,
    nasal conjuncts -> anusvara, Devanagari digits -> ASCII. For comparison only."""
    t = unicodedata.normalize("NFKC", text or "").translate(_DIGITS)
    t = t.replace("‌", "").replace("‍", "").replace("़", "").replace("ँ", "ं")
    for conj, anusvara in _NASALS.items():
        t = t.replace(conj, anusvara)
    return t


def devanagari_words(text: str) -> List[str]:
    return DEVANAGARI_WORD.findall(unicodedata.normalize("NFKC", text or ""))


def _strip_placeholders(text: str) -> str:
    return PLACEHOLDER.sub(" ", text or "")


# --- spelling variants ----------------------------------------------------------------------
def spelling_variants(entries: Iterable[Entry]) -> List[Dict[str, Any]]:
    """Per language, words that differ only in spelling (same ``fold``) and appear in more
    than one surface form. Returns ``[{lang, forms: {form: count}, examples: [(source, key)]}]``."""
    groups: Dict[Tuple[str, str], Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    where: Dict[Tuple[str, str, str], Tuple[str, str]] = {}
    for e in entries:
        if e.lang not in ("hi", "mr"):
            continue
        for w in devanagari_words(_strip_placeholders(e.text)):
            k = (e.lang, fold(w))
            groups[k][w] += 1
            where.setdefault((e.lang, k[1], w), (e.source, e.key))
    out = []
    for (lang, _folded), forms in sorted(groups.items()):
        if len(forms) > 1:
            out.append({
                "lang": lang,
                "forms": dict(sorted(forms.items(), key=lambda kv: -kv[1])),
                "examples": [where[(lang, _folded, f)] for f in forms],
            })
    return out


# --- glossary conflicts ---------------------------------------------------------------------
_DEV = "ऀ-ॿ"


def _variant_pattern(variant: str) -> "re.Pattern[str]":
    """The variant as a whole word, optionally inflected: a vowel sign or anusvara and up to
    three more characters may follow (दरें, दस्तऐवजांचे), but a consonant or a virama may not,
    so ``दर`` does not match inside ``दरवाजा`` or ``दर्ज``. Matched on the folded form."""
    return re.compile(rf"(?<![{_DEV}]){re.escape(fold(variant))}(?:[ा-ौंः][{_DEV}]{{0,3}})?(?![{_DEV}])")


def glossary_conflicts(entries: Sequence[Entry], glossary: Dict[str, Any]) -> List[Dict[str, Any]]:
    """For each concept and language, the variants actually in use. ``conflict`` is True
    when more than one variant is used in the same language."""
    results: List[Dict[str, Any]] = []
    folded = [(e, fold(e.text)) for e in entries if e.lang in ("hi", "mr")]
    for concept, spec in glossary["concepts"].items():
        for lang in ("hi", "mr"):
            used: Dict[str, Dict[str, Any]] = {}
            for variant in spec.get(lang, []):
                needle = _variant_pattern(variant)
                hits = [(e.source, e.key) for e, text in folded if e.lang == lang and needle.search(text)]
                if hits:
                    used[variant] = {"count": len(hits), "examples": hits[:3]}
            # a variant that contains another variant is the same use, not a second term
            roots = [v for v in used if not any(o != v and fold(o) in fold(v) for o in used)]
            results.append({"concept": concept, "english": spec.get("en"), "lang": lang,
                            "variants_in_use": {v: used[v] for v in used},
                            "conflict": len(roots) > 1, "distinct_terms": sorted(roots)})
    return results


# --- language leakage -----------------------------------------------------------------------
def language_leakage(entries: Iterable[Entry], markers: Dict[str, Sequence[str]]) -> List[Dict[str, Any]]:
    """``markers``: {"hindi_only": [...], "marathi_only": [...]} whole words. Reports Hindi-only
    words in Marathi text and Marathi-only words in Hindi text."""
    hindi_only, marathi_only = set(markers["hindi_only"]), set(markers["marathi_only"])
    out = []
    for e in entries:
        if e.lang not in ("hi", "mr"):
            continue
        words = {w.strip("।.,;:!?") for w in devanagari_words(_strip_placeholders(e.text))}
        bad = sorted(words & (hindi_only if e.lang == "mr" else marathi_only))
        if bad:
            out.append({"lang": e.lang, "source": e.source, "key": e.key, "words": bad,
                        "kind": "hindi_in_marathi" if e.lang == "mr" else "marathi_in_hindi"})
    return out


# --- english words / untranslated / placeholders --------------------------------------------
def english_words(entries: Iterable[Entry], allow: Iterable[str]) -> Dict[str, Dict[str, Any]]:
    """Latin-script words in hi/mr text (placeholders excluded), minus the allow-list."""
    allowed = {a.lower() for a in allow}
    found: Dict[str, Dict[str, Any]] = {}
    for e in entries:
        if e.lang not in ("hi", "mr"):
            continue
        for w in LATIN_WORD.findall(_strip_placeholders(e.text)):
            if w.lower() in allowed or len(w) < 2:
                continue
            slot = found.setdefault(w, {"count": 0, "examples": []})
            slot["count"] += 1
            if len(slot["examples"]) < 3:
                slot["examples"].append((e.source, e.key, e.lang))
    return dict(sorted(found.items(), key=lambda kv: -kv[1]["count"]))


def untranslated(copy: Dict[str, Dict[str, Dict[str, str]]], allow_identical: Iterable[str] = ()) -> List[Dict[str, str]]:
    """hi/mr strings identical to their English source (ignoring strings with no letters)."""
    skip = set(allow_identical)
    out = []
    for source, langs in copy.items():
        for lang in ("hi", "mr"):
            for key, text in langs.get(lang, {}).items():
                en = langs.get("en", {}).get(key)
                if en is not None and text.strip() == en.strip() and re.search(r"[A-Za-zऀ-ॿ]", _strip_placeholders(text)) \
                        and text.strip() not in skip:
                    out.append({"lang": lang, "source": source, "key": key, "text": text})
    return out


def placeholder_mismatch(copy: Dict[str, Dict[str, Dict[str, str]]]) -> List[Dict[str, Any]]:
    out = []
    for source, langs in copy.items():
        for lang in ("hi", "mr"):
            for key, text in langs.get(lang, {}).items():
                en = langs.get("en", {}).get(key)
                if en is None:
                    continue
                a, b = sorted(PLACEHOLDER.findall(en)), sorted(PLACEHOLDER.findall(text))
                if a != b:
                    out.append({"lang": lang, "source": source, "key": key, "english": a, lang: b})
    return out


def entries_from_copy(copy: Dict[str, Dict[str, Dict[str, str]]]) -> List[Entry]:
    return [Entry(source, key, lang, text)
            for source, langs in copy.items() for lang, items in langs.items() for key, text in items.items()]


def audit(copy: Dict[str, Dict[str, Dict[str, str]]], glossary: Dict[str, Any],
          letters: Optional[Sequence[Entry]] = None) -> Dict[str, Any]:
    """Runs every check. ``letters`` are extra hi/mr entries (the generated appeal letters)."""
    entries = entries_from_copy(copy) + list(letters or [])
    conflicts = glossary_conflicts(entries, glossary)
    return {
        "strings": {lang: sum(1 for e in entries if e.lang == lang) for lang in ("en", "hi", "mr")},
        "spelling_variants": spelling_variants(entries),
        "glossary": conflicts,
        "glossary_conflicts": [c for c in conflicts if c["conflict"]],
        "language_leakage": language_leakage(entries, glossary["leakage_markers"]),
        "english_words": english_words(entries, glossary["english_allowlist"]),
        "untranslated": untranslated(copy, glossary.get("identical_allowlist", [])),
        "placeholder_mismatch": placeholder_mismatch(copy),
    }
