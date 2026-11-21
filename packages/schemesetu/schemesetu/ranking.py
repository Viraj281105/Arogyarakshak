"""
SchemeSetu — ranking of already-computed eligibility results (Wave 2, stream B).

Order is decided by eligibility STATUS first (eligible, then ambiguous, then ineligible) and
by RELEVANCE second. Relevance only re-orders results that already exist; it never changes a
verdict, never adds or removes a scheme, and never uses income (the cited criteria define no
income ceiling). Every ranked row is provisional.

Relevance (0..1) is deterministic and explainable, with no embeddings:
- 0.3 when the scheme is specific to a state and the stated state is that state;
- up to 0.7 for the share of the applicant's stated medical-need words that appear in the
  scheme's cited criteria text.
"""

import re
from typing import List, Tuple

from pydantic import BaseModel, Field

from schemesetu.agent import EligibilityRequest, SchemeResult
from schemesetu.dialect_normalizer import normalize_state_name
from schemesetu.thresholds import SCHEME_CRITERIA, SchemeCriteria

STATE_WEIGHT = 0.3
NEED_WEIGHT = 0.7

_STATUS_ORDER = {"eligible": 0, "ambiguous": 1, "ineligible": 2}
_WORD = re.compile(r"[\wऀ-ॿ]+")
_STOP = frozenset("a an and are as at for from in is of on or the to with".split())


class RankedScheme(BaseModel):
    rank: int
    scheme_name: str
    estimated_eligibility: str
    relevance: float = Field(..., ge=0.0, le=1.0)
    relevance_basis: List[str]
    provisional: bool = Field(
        True, description="Always true: ranking never turns a provisional result into a decision."
    )
    result: SchemeResult


def _terms(text: str) -> set:
    out = set()
    for w in _WORD.findall((text or "").casefold()):
        if w in _STOP or len(w) < 2:
            continue
        out.add(w[:-1] if len(w) > 3 and w.endswith("s") else w)
    return out


def _criteria_for(scheme_name: str) -> "SchemeCriteria | None":
    for c in SCHEME_CRITERIA:
        if c.scheme_name == scheme_name:
            return c
    return None


def _criteria_text(c: SchemeCriteria) -> str:
    parts = [c.scheme_name, c.official_basis, *c.criteria_not_evaluated, *c.verification_steps]
    parts += [cit.supports for cit in c.citations]
    return " ".join(parts)


def _relevance(profile: EligibilityRequest, result: SchemeResult) -> Tuple[float, List[str]]:
    criteria = _criteria_for(result.scheme_name)
    if criteria is None:
        return 0.0, ["scheme not in the criteria index: no relevance signal"]
    score = 0.0
    basis: List[str] = []
    if criteria.applicable_states is not None:
        state = normalize_state_name(profile.location_state).normalized or profile.location_state
        if criteria.applies_to_state(state):
            score += STATE_WEIGHT
            basis.append("scheme is specific to the stated state of residence")
    need = _terms(profile.medical_need)
    if need:
        matched = need & _terms(_criteria_text(criteria))
        share = len(matched) / len(need)
        score += NEED_WEIGHT * share
        if matched:
            basis.append(f"{len(matched)} of {len(need)} stated medical-need words appear in the cited criteria")
    if not basis:
        basis.append("no relevance signal beyond eligibility status")
    return round(min(score, 1.0), 6), basis


def rank_schemes(profile: EligibilityRequest, results: List[SchemeResult]) -> List[RankedScheme]:
    """Eligibility status first, relevance second, name last (for a stable order)."""
    scored = []
    for r in results:
        relevance, basis = _relevance(profile, r)
        scored.append((_STATUS_ORDER.get(r.estimated_eligibility, len(_STATUS_ORDER)), -relevance, r.scheme_name, r, relevance, basis))
    scored.sort(key=lambda t: t[:3])
    return [
        RankedScheme(
            rank=i,
            scheme_name=r.scheme_name,
            estimated_eligibility=r.estimated_eligibility,
            relevance=relevance,
            relevance_basis=basis,
            provisional=True,
            result=r,
        )
        for i, (_s, _neg, _n, r, relevance, basis) in enumerate(scored, 1)
    ]
