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
  * the longest matching key wins; no match returns None (never a guess).
"""

import json
import os
import re
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple

SYNONYM_TABLE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "matcher_synonyms.json")
_TOKEN = re.compile(r"[a-z0-9]+")


@lru_cache(maxsize=1)
def _table() -> Dict[str, Any]:
    try:
        with open(SYNONYM_TABLE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {"synonyms": [], "modifiers": [], "modifier_phrases": [], "contrast_scan_prefixes": []}


def tokens(text: str) -> List[str]:
    return _TOKEN.findall((text or "").lower())


def _contains(haystack: List[str], needle: List[str]) -> bool:
    n = len(needle)
    return n > 0 and any(haystack[i:i + n] == needle for i in range(len(haystack) - n + 1))


def _apply_synonyms(toks: List[str]) -> List[str]:
    out: List[str] = []
    for t in toks:
        rule = next((s for s in _table().get("synonyms", []) if s["phrase"] == t), None)
        if rule and not any(u in toks for u in rule.get("unless", [])):
            out.extend(rule["canonical"].split())
        else:
            out.append(t)
    return out


def has_modifier(toks: List[str]) -> bool:
    table = _table()
    mods = set(table.get("modifiers", []))
    prefixes = set(table.get("contrast_scan_prefixes", []))
    if any(t in mods for t in toks):
        return True
    if any(_contains(toks, p.split()) for p in table.get("modifier_phrases", [])):
        return True
    for i, t in enumerate(toks):
        if t == "contrast" and (i == 0 or toks[i - 1] not in prefixes):
            return True
    return False


def match_key(norm_name: str, rates_source: Dict[str, Any]) -> Optional[str]:
    """The rate key a normalised (lower-case) item name resolves to, or None."""
    if not norm_name:
        return None
    if norm_name in rates_source:
        return norm_name

    name_toks = tokens(norm_name)
    if not name_toks or has_modifier(name_toks):
        return None
    name_toks = _apply_synonyms(name_toks)

    best: Optional[Tuple[str, int]] = None
    for key in rates_source:
        key_toks = tokens(key)
        if not key_toks:
            continue
        if _contains(name_toks, key_toks) or _contains(key_toks, name_toks):
            if best is None or len(key) > best[1]:
                best = (key, len(key))
    return best[0] if best else None
