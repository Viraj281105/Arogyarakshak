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
]
