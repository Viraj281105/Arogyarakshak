"""
BillNyay Agents Package.

Contains the 5-agent pipeline for hospital bill auditing and IRDAI-compliant appeal drafting:
1. AuditorAgent: Extracts denial facts & evidence chunks.
2. ClinicianAgent: Synthesizes PubMed clinical literature / evidence.
3. RegulatoryAgent: Retrieves IRDAI, Consumer Protection, and CGHS regulations.
4. BarristerAgent: Generates formal legal appeal letter.
5. JudgeAgent: Performs QA evaluation & scorecard validation.
"""

from .auditor import run_auditor_agent, StructuredDenial
from .clinician import run_clinician_agent, EvidenceList, ClinicalEvidence
from .regulatory import run_regulatory_agent
from .barrister import run_barrister_agent
from .judge import run_judge_agent, JudgeScorecard
from .consensus import (
    AgentRole,
    AgentVote,
    ConsensusResult,
    VoteDecision,
    compute_weighted_consensus,
    vote_from_auditor,
    vote_from_clinician,
    vote_from_regulatory,
)
from .feedback_loop import draft_with_self_correction, DraftingResult, RevisionAttempt
from .icd_audit import audit_icd_procedure_consistency, ICDProcedureAuditItem

__all__ = [
    "run_auditor_agent",
    "StructuredDenial",
    "run_clinician_agent",
    "EvidenceList",
    "ClinicalEvidence",
    "run_regulatory_agent",
    "run_barrister_agent",
    "run_judge_agent",
    "JudgeScorecard",
    "AgentRole",
    "AgentVote",
    "ConsensusResult",
    "VoteDecision",
    "compute_weighted_consensus",
    "vote_from_auditor",
    "vote_from_clinician",
    "vote_from_regulatory",
    "draft_with_self_correction",
    "DraftingResult",
    "RevisionAttempt",
    "audit_icd_procedure_consistency",
    "ICDProcedureAuditItem",
]
