"""
BillNyay — which CGHS rate key a bill line name refers to.

Replaces the raw substring test (``key in name``), which applied the PPE-kit rate to
"Appendectomy" (``ppe``) and the ICU rate to "Particular Care" (``icu``). Rules:

  * keys match as WHOLE WORDS (a contiguous run of word tokens), never inside a word;
  * hyphens and punctuation are word breaks ("X-Ray" == "x ray");
  * a small synonym table (data/matcher_synonyms.json, unreviewed) rewrites hospital wording
    to the key wording ("USG" -> "ultrasound");
  * a modifier that changes what is billed (catheter, report copy, follow-up drops, contrast
    agent, image-guided) REFUSES the match instead of pricing the line at the parent rate;
  * a key must appear inside the line; a bare fragment of a key ("scan", "ward") maps to nothing;
  * conservative plural folding ("X-Rays" == "x ray");
  * a line with Devanagari text is refused (the matcher cannot read it);
  * the most specific key wins; two unrelated keys with different rates ("ICU Consultation") or
    no key at all return None (never a guess).
"""

import json
import logging
import os
import re
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple

SYNONYM_TABLE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "matcher_synonyms.json")
logger = logging.getLogger("arogyarakshak.billnyay.matching")
_TOKEN = re.compile(r"[a-z0-9]+")
_DEVANAGARI = re.compile("[ऀ-ॿ]")


@lru_cache(maxsize=1)
def _table() -> Dict[str, Any]:
    try:
        with open(SYNONYM_TABLE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError) as exc:
        # Never fall back silently: an empty table would switch the modifier refusals off and
        # let "MRI Contrast Agent" be priced as an MRI again. (No document text is logged.)
        logger.error("BillNyay matcher table %s could not be loaded (%s); modifier refusals and synonyms are OFF",
                     SYNONYM_TABLE_PATH, type(exc).__name__)
        return {"synonyms": [], "modifiers": [], "modifier_phrases": [], "contrast_scan_prefixes": []}


def tokens(text: str) -> List[str]:
    return _TOKEN.findall((text or "").lower())


def _fold(tok: str) -> str:
    """Conservative plural folding: 'rays' -> 'ray', 'scans' -> 'scan' (tokens longer than 3
    letters ending in a single 's'). Applied to both the line and the keys."""
    return tok[:-1] if len(tok) > 3 and tok.endswith("s") and not tok.endswith("ss") else tok


def _contains(haystack: List[str], needle: List[str]) -> bool:
    n = len(needle)
    return n > 0 and any(haystack[i:i + n] == needle for i in range(len(haystack) - n + 1))


def _apply_synonyms(toks: List[str]) -> List[str]:
    out: List[str] = []
    for t in toks:
        rule = next((s for s in _table().get("synonyms", []) if _fold(s["phrase"]) == _fold(t)), None)
        if rule and not any(_fold(u) in {_fold(x) for x in toks} for u in rule.get("unless", [])):
            out.extend(rule["canonical"].split())
        else:
            out.append(t)
    return out


def has_modifier(toks: List[str]) -> bool:
    table = _table()
    folded = [_fold(t) for t in toks]
    mods = {_fold(m) for m in table.get("modifiers", [])}
    prefixes = set(table.get("contrast_scan_prefixes", []))
    if any(t in mods for t in folded):
        return True
    # A contrast AGENT/media/injection is a separate billed item even after "with".
    if any(_contains(folded, [_fold(w) for w in p.split()]) for p in table.get("modifier_phrases", [])):
        return True
    for i, t in enumerate(toks):
        if t == "contrast" and (i == 0 or toks[i - 1] not in prefixes):
            return True
    return False


def _entry_signature(entry: Any):
    if isinstance(entry, dict):
        return (entry.get("benchmark_rate"), entry.get("billing_unit"), bool(entry.get("bundled", False)))
    return (entry, None, False)


def match_key(norm_name: str, rates_source: Dict[str, Any]) -> Optional[str]:
    """The rate key a normalised (lower-case) item name resolves to, or None.

    None also when the line is ambiguous: several keys that are not refinements of one
    another ("ICU Consultation") with different rates or units."""
    if not norm_name:
        return None
    if norm_name in rates_source:
        return norm_name
    if _DEVANAGARI.search(norm_name):
        # Devanagari words that this English-only matcher cannot interpret ("MRI कॉन्ट्रास्ट")
        # may be exactly the modifier that changes what is billed: refuse.
        return None

    name_toks = tokens(norm_name)
    if not name_toks or has_modifier(name_toks):
        return None
    name_toks = [_fold(t) for t in _apply_synonyms(name_toks)]

    # One direction only: the key must appear in the line. A bare fragment of a key
    # ("scan", "ward", "private") is ambiguous between several rates and is refused.
    hits = [(k, [_fold(t) for t in tokens(k)]) for k in rates_source]
    hits = [(k, kt) for k, kt in hits if kt and _contains(name_toks, kt)]
    if not hits:
        return None
    # Keep the most specific keys: drop any key that is only a part of another matching key
    # ("icu" inside "icu day charges").
    maximal = [(k, kt) for k, kt in hits if not any(k2 != k and _contains(kt2, kt) for k2, kt2 in hits)]
    if len({_entry_signature(rates_source[k]) for k, _ in maximal}) > 1:
        return None
    return max(maximal, key=lambda h: len(h[0]))[0]
