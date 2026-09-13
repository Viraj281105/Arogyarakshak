"""
BillNyay — Multi-Agent Consensus Voting Protocol (#65).

Lets the Auditor, Clinician, and Regulatory agents each cast a vote on whether a draft
is ready for the Judge's final approval, weighted by role, before the Barrister drafts
the letter the Judge will score. This is a transparency/triage layer: it surfaces
*why* the upstream evidence looks thin before drafting proceeds, on top of (not instead
of) the Judge's own scoring of the finished letter.
"""

import logging
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger("BillNyay.ConsensusAgent")


class AgentRole(str, Enum):
    AUDITOR = "auditor"
    CLINICIAN = "clinician"
    REGULATORY = "regulatory"


class VoteDecision(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"
    FLAG_REVIEW = "flag_review"


class AgentVote(BaseModel):
    role: AgentRole
    decision: VoteDecision
    confidence: float = Field(..., ge=0.0, le=1.0)
    rationale_digest: str


class ConsensusResult(BaseModel):
    final_verdict: VoteDecision
    weighted_score: float
    is_unanimous: bool
    requires_judge_override: bool
    votes: List[AgentVote]


DEFAULT_ROLE_WEIGHTS: Dict[AgentRole, float] = {
    AgentRole.AUDITOR: 0.30,
    AgentRole.CLINICIAN: 0.40,
    AgentRole.REGULATORY: 0.30,
}


def compute_weighted_consensus(
    votes: List[AgentVote],
    role_weights: Optional[Dict[AgentRole, float]] = None,
    approval_threshold: float = 0.75,
) -> ConsensusResult:
    """Weighted approval score across the three upstream agents' votes.

    A single REJECT vote always forces the case out of straight approval (into
    FLAG_REVIEW or REJECT depending on the remaining score), mirroring how one agent
    flatly disputing medical necessity or denial facts should not be outvoted by the
    other two's confidence alone.
    """
    weights = role_weights or DEFAULT_ROLE_WEIGHTS

    score = sum(
        weights[vote.role] * vote.confidence
        for vote in votes
        if vote.decision == VoteDecision.APPROVE
    )
    has_rejection = any(vote.decision == VoteDecision.REJECT for vote in votes)
    is_unanimous = len(votes) > 0 and all(v.decision == VoteDecision.APPROVE for v in votes)

    if has_rejection or score < approval_threshold:
        verdict = VoteDecision.FLAG_REVIEW if score >= 0.50 else VoteDecision.REJECT
        return ConsensusResult(
            final_verdict=verdict,
            weighted_score=round(score, 4),
            is_unanimous=False,
            requires_judge_override=True,
            votes=votes,
        )

    return ConsensusResult(
        final_verdict=VoteDecision.APPROVE,
        weighted_score=round(score, 4),
        is_unanimous=is_unanimous,
        requires_judge_override=False,
        votes=votes,
    )


def vote_from_auditor(denial: Optional[object], denial_facts_extracted: bool) -> AgentVote:
    """Derives the Auditor's vote from the same StructuredDenial draft_appeal already
    computes — no separate LLM call, just an honest read of what was extracted."""
    if denial is None:
        return AgentVote(
            role=AgentRole.AUDITOR,
            decision=VoteDecision.REJECT,
            confidence=0.0,
            rationale_digest="No denial text could be extracted from the uploaded document.",
        )
    confidence = float(getattr(denial, "confidence_score", 0.0) or 0.0)
    if not denial_facts_extracted:
        # A parseable-but-fallback denial is a template, not real extraction.
        return AgentVote(
            role=AgentRole.AUDITOR,
            decision=VoteDecision.FLAG_REVIEW,
            confidence=min(confidence, 0.5),
            rationale_digest="Denial facts came from a fallback template, not real document extraction.",
        )
    decision = VoteDecision.APPROVE if confidence >= 0.7 else VoteDecision.FLAG_REVIEW
    return AgentVote(
        role=AgentRole.AUDITOR,
        decision=decision,
        confidence=confidence,
        rationale_digest=f"Denial code {getattr(denial, 'denial_code', 'unknown')} extracted with confidence {confidence:.2f}.",
    )


def vote_from_clinician(clinical_evidence: Optional[object]) -> AgentVote:
    """Derives the Clinician's vote from whether real evidence items were returned."""
    items = getattr(clinical_evidence, "root", None) if clinical_evidence is not None else None
    count = len(items) if items else 0
    if count == 0:
        return AgentVote(
            role=AgentRole.CLINICIAN,
            decision=VoteDecision.FLAG_REVIEW,
            confidence=0.3,
            rationale_digest="No clinical evidence items were returned.",
        )
    confidence = min(0.6 + 0.15 * count, 0.95)
    return AgentVote(
        role=AgentRole.CLINICIAN,
        decision=VoteDecision.APPROVE,
        confidence=confidence,
        rationale_digest=f"{count} clinical evidence item(s) support medical necessity.",
    )


def vote_from_regulatory(regulatory_evidence: Optional[dict]) -> AgentVote:
    """Derives the Regulatory agent's vote from whether statutes were retrieved."""
    statute_count = (regulatory_evidence or {}).get("statute_count", 0)
    if not statute_count:
        return AgentVote(
            role=AgentRole.REGULATORY,
            decision=VoteDecision.FLAG_REVIEW,
            confidence=0.3,
            rationale_digest="No applicable statutes were retrieved.",
        )
    confidence = min(0.6 + 0.1 * statute_count, 0.95)
    return AgentVote(
        role=AgentRole.REGULATORY,
        decision=VoteDecision.APPROVE,
        confidence=confidence,
        rationale_digest=f"{statute_count} applicable statute(s) retrieved.",
    )
