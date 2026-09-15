"""
SchemeSetu — Regional Marathi State-Name Normalization (#95).

`EligibilityRequest.location_state` decides MJPJAY eligibility outright
(`SchemeCriteria.applies_to_state` in thresholds.py does an exact-match lookup against
`{"maharashtra", "mh"}`). Before this module, a Marathi-speaking user who typed their
state in Devanagari (`महाराष्ट्र`), a common English misspelling (`Maharastra`), or their
city instead of the state (`Mumbai`) got **no explanation at all** — MJPJAY simply did
not appear in the results, indistinguishable from genuinely not qualifying.

Scope, stated honestly: this is a small, curated table of Devanagari spellings, common
English misspellings, and major Maharashtra city names for the *one* state string that
currently decides an eligibility outcome (MJPJAY). It is **not** a linguistically
validated corpus of Varhadi, Ahirani, or any other Marathi regional dialect — building
that would need a linguistics partnership and real dialectal survey data, which does not
exist in this repository. Calling this "dialect normalization" without that caveat would
be exactly the kind of unverifiable-capability claim the project's no-fabrication
principle exists to prevent. What is here is verifiable: standard Devanagari transliteration,
well-documented common misspellings, and well-known city-to-state facts.
"""

import re
from typing import Optional

from pydantic import BaseModel, Field

# Devanagari and common-misspelling variants of "Maharashtra" that a free-text state
# field will plausibly contain. Standard transliteration / well-known typos only —
# nothing dialect-specific is claimed.
_STATE_NAME_VARIANTS = {
    "महाराष्ट्र": "Maharashtra",
    "महाराष्ट्रात": "Maharashtra",  # locative case ("in Maharashtra"), common in free text
    "महाराष्ट्रचा": "Maharashtra",
    "maharastra": "Maharashtra",  # common typo: drops the 'h' before 't'
    "maharashta": "Maharashtra",  # common typo: drops the trailing 'r'
    "state of maharashtra": "Maharashtra",
    "maharashtra state": "Maharashtra",
}

# Major Maharashtra cities a user might type in place of the state name. Verifiable
# geography, not a dialect claim: each of these is unambiguously in Maharashtra.
_MAHARASHTRA_CITIES = {
    "mumbai",
    "bombay",
    "pune",
    "nagpur",
    "nashik",
    "thane",
    "kolhapur",
    "aurangabad",
    "chhatrapati sambhajinagar",
    "solapur",
    "amravati",
    "akola",
    "yavatmal",
    "wardha",
}


class NormalizedState(BaseModel):
    original_input: str
    normalized: str = Field(..., description="The canonical state name used for eligibility matching.")
    was_normalized: bool = Field(
        ..., description="True when the input did not already match the canonical name exactly."
    )
    normalization_basis: Optional[str] = Field(
        None,
        description="Why the normalization was applied: 'devanagari_or_spelling_variant' or "
        "'inferred_from_city_name'. None when no normalization was needed.",
    )


def normalize_state_name(raw_state: Optional[str]) -> NormalizedState:
    """Resolves common Devanagari/misspelling/city-name variants of a state name to its
    canonical English form, so a Marathi-speaking or informally-typed input does not
    silently fail the exact-match state check that decides MJPJAY eligibility.

    Returns the original input unchanged (was_normalized=False) when nothing in the
    curated variant table matches — this function never guesses at a mapping it is not
    confident about.
    """
    text = (raw_state or "").strip()
    if not text:
        return NormalizedState(original_input=raw_state or "", normalized="", was_normalized=False)

    normalized_key = re.sub(r"\s+", " ", text.strip().lower())

    variant_match = _STATE_NAME_VARIANTS.get(normalized_key) or _STATE_NAME_VARIANTS.get(text.strip())
    if variant_match:
        return NormalizedState(
            original_input=text,
            normalized=variant_match,
            was_normalized=True,
            normalization_basis="devanagari_or_spelling_variant",
        )

    if normalized_key in _MAHARASHTRA_CITIES:
        return NormalizedState(
            original_input=text,
            normalized="Maharashtra",
            was_normalized=True,
            normalization_basis="inferred_from_city_name",
        )

    return NormalizedState(original_input=text, normalized=text, was_normalized=False)
