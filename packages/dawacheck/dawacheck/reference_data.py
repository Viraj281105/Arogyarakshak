"""
DawaCheck — shared NPPA reference data and brand/generic matching.

Single source of truth for the curated NPPA Schedule-I subset and the matching logic
used to resolve a free-text brand mention (as typed by a user or extracted by Kadi's
OCR/LLM pipeline) to a reference formulation. Previously this table and its matching
logic lived inline in `checker.py`; it moved here so the same lookup can be reused by
fuzzy matching (#72), dosage normalization (#73), and the Kadi case-integration
endpoint (#27) without duplicating the data.
"""

import re
from typing import Dict, List, Optional, Tuple

from dawacheck.metaphone import phonetic_codes_match

REFERENCE_SOURCE = "NPPA Schedule-I (curated subset)"

# Ceiling prices are PER DOSAGE UNIT of `unit_form` (one tablet, one capsule, one vial) —
# DawaCheck.price_basis converts a billed strip/pack/line total to that unit or refuses
# to compare.
# Each entry is one reference formulation. `ingredient_base` is the bare active
# ingredient with no dosage/strength token, used for dosage normalization (#73) and as
# the phonetic-matching target (#72) so "Paracetamol 500mg" can be recognized as a
# dosage variant of the "paracetamol 650mg" reference entry rather than an unknown drug.
NPPA_REFERENCE_DATA: Dict[str, dict] = {
    "paracetamol 650mg": {
        "unit_form": "tablet",
        "ingredient_base": "paracetamol",
        "dosage_mg": 650.0,
        "active_ingredient": "Paracetamol 650mg",
        "ceiling_price": 2.30,
        "generic_info": "Generic Paracetamol 650mg available at PMBJP Jan Aushadhi Kendras for ₹0.80/tablet (65% savings).",
        "aliases": ["dolo 650", "dolo 650mg", "crocin 650", "crocin 650mg", "calpol 650", "pacimol 650"],
    },
    "amoxicillin 500mg": {
        "unit_form": "capsule",
        "ingredient_base": "amoxicillin",
        "dosage_mg": 500.0,
        "active_ingredient": "Amoxicillin 500mg",
        "ceiling_price": 7.50,
        "generic_info": "Generic Amoxicillin 500mg available at PMBJP Jan Aushadhi for ₹2.40/capsule (68% savings).",
        "aliases": ["mox 500", "novamox 500", "amoxil 500"],
    },
    "augmentin 625": {
        "unit_form": "tablet",
        "ingredient_base": "amoxicillin clavulanate",
        "dosage_mg": 625.0,
        "active_ingredient": "Amoxicillin (500mg) + Clavulanic Acid (125mg)",
        "ceiling_price": 20.10,
        "generic_info": "Generic Amoxyclav 625mg available at PMBJP Kendras for ₹6.50/tablet (68% savings).",
        "aliases": ["augmentin 625 duo", "augmentin 625 duo tablet", "moxikind cv 625", "clavum 625"],
    },
    "metformin 500mg": {
        "unit_form": "tablet",
        "ingredient_base": "metformin",
        "dosage_mg": 500.0,
        "active_ingredient": "Metformin Hydrochloride 500mg SR",
        "ceiling_price": 2.15,
        "generic_info": "Generic Metformin 500mg SR available at PMBJP Jan Aushadhi for ₹0.45/tablet (79% savings).",
        "aliases": ["metformin 500mg sr", "glycomet 500", "glyciphage 500", "metformin sr"],
    },
    "meropenem 1g": {
        "unit_form": "injection",
        "ingredient_base": "meropenem",
        "dosage_mg": 1000.0,
        "active_ingredient": "Meropenem 1000mg Powder for Injection",
        "ceiling_price": 850.00,
        "generic_info": "Generic Meropenem 1g Injection available at Jan Aushadhi stores for ₹245.00/vial (71% savings).",
        "aliases": ["meropenem 1g injection", "meronem 1g", "meromac 1g"],
    },
    "pantoprazole 40mg": {
        "unit_form": "tablet",
        "ingredient_base": "pantoprazole",
        "dosage_mg": 40.0,
        "active_ingredient": "Pantoprazole 40mg",
        "ceiling_price": 3.20,
        "generic_info": "Generic Pantoprazole 40mg available at PMBJP Kendras for ₹0.90/tablet (72% savings).",
        "aliases": ["pan 40", "pantocid 40", "pantodac 40"],
    },
    "azithromycin 500mg": {
        "unit_form": "tablet",
        "ingredient_base": "azithromycin",
        "dosage_mg": 500.0,
        "active_ingredient": "Azithromycin 500mg",
        "ceiling_price": 21.50,
        "generic_info": "Generic Azithromycin 500mg available at PMBJP Jan Aushadhi for ₹8.00/tablet (63% savings).",
        "aliases": ["azithral 500", "aziwok 500", "zithrox 500"],
    },
}

_DOSAGE_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(mcg|mg|g)\b", re.IGNORECASE)
_UNIT_TO_MG = {"mcg": 0.001, "mg": 1.0, "g": 1000.0}


def extract_dosage_mg(text: str) -> Optional[float]:
    """Extracts the first mg/mcg/g strength mentioned in `text`, normalized to mg.

    Returns None when no strength token is present — callers must not assume a
    default strength, since guessing one could silently mis-price a different dose.
    """
    match = _DOSAGE_RE.search(text)
    if not match:
        return None
    value, unit = match.groups()
    return round(float(value) * _UNIT_TO_MG[unit.lower()], 4)


def strip_dosage_token(text: str) -> str:
    """Removes the first mg/mcg/g strength token, leaving the bare brand/ingredient text."""
    return _DOSAGE_RE.sub("", text).strip()


def find_exact_or_alias(query: str) -> Optional[Tuple[str, dict]]:
    """Exact-key, then substring, then alias matching (unchanged from the original
    single-file matcher). Returns (reference_key, entry) or None."""
    norm_query = query.lower().strip()

    if norm_query in NPPA_REFERENCE_DATA:
        return norm_query, NPPA_REFERENCE_DATA[norm_query]

    for primary_key, entry in NPPA_REFERENCE_DATA.items():
        if primary_key in norm_query or norm_query in primary_key:
            return primary_key, entry
        for alias in entry.get("aliases", []):
            if alias in norm_query or norm_query in alias:
                return primary_key, entry

    return None


def find_ingredient_family(ingredient_base: str) -> List[Tuple[str, dict]]:
    """All reference entries sharing the given bare ingredient name."""
    target = ingredient_base.lower().strip()
    return [
        (key, entry)
        for key, entry in NPPA_REFERENCE_DATA.items()
        if entry["ingredient_base"] == target
    ]


def find_phonetic_match(query: str) -> Optional[Tuple[str, dict]]:
    """Matches the bare (dosage-stripped) ingredient token in `query` against each
    reference entry's ingredient name and aliases using Double Metaphone codes.

    This is a lower-confidence match than `find_exact_or_alias` — it is meant to catch
    spelling/OCR variants (e.g. "Amoxycillin" for "Amoxicillin"), not to guess at
    unrelated brand names. Callers must disclose when a result came from this path.
    """
    bare_query = strip_dosage_token(query).strip()
    if not bare_query:
        return None

    # Phonetic codes are unreliable on very short strings (high collision rate), so
    # require a minimum length before trusting a match.
    query_tokens = [t for t in re.split(r"\s+", bare_query) if len(t) >= 4]
    if not query_tokens:
        return None

    for key, entry in NPPA_REFERENCE_DATA.items():
        candidate_terms = [entry["ingredient_base"], key] + entry.get("aliases", [])
        candidate_tokens = set()
        for term in candidate_terms:
            bare_term = strip_dosage_token(term)
            candidate_tokens.update(t for t in re.split(r"\s+", bare_term) if len(t) >= 4)

        for q_tok in query_tokens:
            for c_tok in candidate_tokens:
                if phonetic_codes_match(q_tok, c_tok):
                    return key, entry

    return None
