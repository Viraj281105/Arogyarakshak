from billnyay.agents.consensus import (
    AgentRole,
    AgentVote,
    VoteDecision,
    compute_weighted_consensus,
    vote_from_auditor,
    vote_from_clinician,
    vote_from_regulatory,
)
from billnyay.agents.auditor import StructuredDenial
from billnyay.agents.clinician import ClinicalEvidence, EvidenceList


def _vote(role, decision, confidence):
    return AgentVote(role=role, decision=decision, confidence=confidence, rationale_digest="test")


def test_unanimous_high_confidence_approval():
    votes = [
        _vote(AgentRole.AUDITOR, VoteDecision.APPROVE, 0.9),
        _vote(AgentRole.CLINICIAN, VoteDecision.APPROVE, 0.9),
        _vote(AgentRole.REGULATORY, VoteDecision.APPROVE, 0.9),
    ]
    result = compute_weighted_consensus(votes)
    assert result.final_verdict == VoteDecision.APPROVE
    assert result.is_unanimous is True
    assert result.requires_judge_override is False
    assert result.weighted_score == 0.9


def test_single_rejection_forces_override_even_with_high_confidence_elsewhere():
    votes = [
        _vote(AgentRole.AUDITOR, VoteDecision.REJECT, 0.9),
        _vote(AgentRole.CLINICIAN, VoteDecision.APPROVE, 0.95),
        _vote(AgentRole.REGULATORY, VoteDecision.APPROVE, 0.95),
    ]
    result = compute_weighted_consensus(votes)
    assert result.final_verdict != VoteDecision.APPROVE
    assert result.requires_judge_override is True
    assert result.is_unanimous is False


def test_low_confidence_flags_for_review_not_outright_rejection():
    votes = [
        _vote(AgentRole.AUDITOR, VoteDecision.APPROVE, 0.5),
        _vote(AgentRole.CLINICIAN, VoteDecision.APPROVE, 0.5),
        _vote(AgentRole.REGULATORY, VoteDecision.APPROVE, 0.5),
    ]
    result = compute_weighted_consensus(votes)
    assert result.weighted_score == 0.5
    assert result.final_verdict == VoteDecision.FLAG_REVIEW


def test_very_low_confidence_rejects():
    votes = [
        _vote(AgentRole.AUDITOR, VoteDecision.APPROVE, 0.1),
        _vote(AgentRole.CLINICIAN, VoteDecision.APPROVE, 0.1),
        _vote(AgentRole.REGULATORY, VoteDecision.APPROVE, 0.1),
    ]
    result = compute_weighted_consensus(votes)
    assert result.final_verdict == VoteDecision.REJECT


def test_custom_role_weights_are_respected():
    votes = [
        _vote(AgentRole.AUDITOR, VoteDecision.APPROVE, 1.0),
        _vote(AgentRole.CLINICIAN, VoteDecision.APPROVE, 0.0),
        _vote(AgentRole.REGULATORY, VoteDecision.APPROVE, 0.0),
    ]
    result = compute_weighted_consensus(votes, role_weights={AgentRole.AUDITOR: 1.0, AgentRole.CLINICIAN: 0.0, AgentRole.REGULATORY: 0.0})
    assert result.weighted_score == 1.0
    assert result.final_verdict == VoteDecision.APPROVE


# ---------------------------------------------------------------------------
# Vote derivation from real upstream agent outputs
# ---------------------------------------------------------------------------


def test_vote_from_auditor_none_denial_rejects():
    vote = vote_from_auditor(None, denial_facts_extracted=False)
    assert vote.decision == VoteDecision.REJECT
    assert vote.confidence == 0.0


def test_vote_from_auditor_fallback_template_flags_review():
    denial = StructuredDenial(
        denial_code="DEN-999",
        insurer_reason_snippet="Audit deviation detected.",
        policy_clause_text="Section 4.1",
        procedure_denied="General ward treatment",
        confidence_score=0.95,
        raw_evidence_chunks=[],
    )
    vote = vote_from_auditor(denial, denial_facts_extracted=False)
    assert vote.decision == VoteDecision.FLAG_REVIEW
    assert vote.confidence <= 0.5


def test_vote_from_auditor_real_extraction_high_confidence_approves():
    denial = StructuredDenial(
        denial_code="DEN-4471",
        insurer_reason_snippet="Real reason from document.",
        policy_clause_text="Section 4.1",
        procedure_denied="Laparoscopic Appendectomy",
        confidence_score=0.9,
        raw_evidence_chunks=[],
    )
    vote = vote_from_auditor(denial, denial_facts_extracted=True)
    assert vote.decision == VoteDecision.APPROVE
    assert vote.confidence == 0.9


def test_vote_from_clinician_empty_evidence_flags_review():
    vote = vote_from_clinician(EvidenceList(root=[]))
    assert vote.decision == VoteDecision.FLAG_REVIEW


def test_vote_from_clinician_with_evidence_approves():
    evidence = EvidenceList(
        root=[ClinicalEvidence(article_title="A", summary_of_finding="B", pubmed_id="PMID:1")]
    )
    vote = vote_from_clinician(evidence)
    assert vote.decision == VoteDecision.APPROVE


def test_vote_from_regulatory_no_statutes_flags_review():
    vote = vote_from_regulatory({"statute_count": 0, "legal_points": []})
    assert vote.decision == VoteDecision.FLAG_REVIEW


def test_vote_from_regulatory_with_statutes_approves():
    vote = vote_from_regulatory({"statute_count": 2, "legal_points": [{}, {}]})
    assert vote.decision == VoteDecision.APPROVE
