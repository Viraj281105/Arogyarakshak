"""
BillNyay — Barrister Agent (Appeal Letter Drafter).

Generates a formal, IRDAI-compliant legal appeal letter in markdown/text format
synthesizing facts from Auditor, Clinician, and Regulatory agents.
"""

import json
import logging
from typing import Any, Dict, List, Optional

from .auditor import StructuredDenial
from .clinician import EvidenceList

logger = logging.getLogger("BillNyay.BarristerAgent")
logger.setLevel(logging.INFO)


def format_clinical_evidence(ev: Any) -> str:
    try:
        if hasattr(ev, "root"):
            items = ev.root
        elif isinstance(ev, list):
            items = ev
        else:
            return "- Clinical medical necessity established by standard of care."
        if not items:
            return "- Clinical medical necessity established by standard of care."
        lines = []
        for it in items:
            title = getattr(it, "article_title", None) or it.get("article_title", "Clinical Finding")
            summary = getattr(it, "summary_of_finding", None) or it.get("summary_of_finding", "")
            pmid = getattr(it, "pubmed_id", None) or it.get("pubmed_id", "N/A")
            lines.append(f"- {title}: {summary} ({pmid})")
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"Failed to format clinical evidence: {e}")
        return "- Medical necessity established under standard clinical guidelines."


def run_barrister_agent(
    client,
    denial_details: StructuredDenial = None,
    clinical_evidence: EvidenceList = None,
    regulatory_evidence: Dict[str, Any] = None,
    critique: str = None,
    **kwargs,
) -> Optional[str]:
    """Generates a formal IRDAI appeal letter."""
    denial = denial_details
    clinical_text = format_clinical_evidence(clinical_evidence)

    legal_points = (regulatory_evidence or {}).get("legal_points", [])
    if legal_points:
        legal_text = "\n".join(
            f"- {lp.get('statute', 'Statute')}: {lp.get('summary', '')}"
            for lp in legal_points
        )
    else:
        legal_text = "- Applicable under IRDAI Protection of Policyholders Interest Regulations."

    sys_instr = (
        "You are the Barrister Agent in BillNyay — a legal counsel specializing in Indian health insurance appeals and bill audit disputes.\n"
        "Your task is to produce a formal, legally structured, IRDAI-compliant insurance appeal letter.\n"
        "Write in formal legal prose. No placeholders. No bracketed instructions.\n"
        "Do not add introductory or concluding conversational chat text. Output ONLY the letter text."
    )

    if critique:
        sys_instr += f"\n\nJUDGE FEEDBACK: Address these points in your revision: '{critique}'"

    prompt = f"""Draft a formal insurance appeal letter:

CLAIM / DENIAL DETAILS:
- Procedure / Treatment: {denial.procedure_denied if denial else 'Medical Treatment'}
- Denial Code / Reference: {denial.denial_code if denial else 'N/A'}
- Insurer Reason: {denial.insurer_reason_snippet if denial else 'Coverage Denied / Overcharged'}
- Policy Clause: {denial.policy_clause_text if denial else 'N/A'}

CLINICAL EVIDENCE & MEDICAL NECESSITY:
{clinical_text}

STATUTORY & REGULATORY PROVISIONS:
{legal_text}

REQUIRED APPEAL LETTER STRUCTURE:
1. SUBJECT LINE: Formal Notice of Representation & Appeal for Claim / Bill Audit
2. RECITALS: Date, Policy/Claim Number reference, and formal intent to appeal rejection/overcharge.
3. SECTION I: CLINICAL JUSTIFICATION & MEDICAL NECESSITY
4. SECTION II: STATUTORY & IRDAI REGULATORY VIOLATIONS
5. SECTION III: FORMAL DEMAND & TIMELINE FOR REVERSAL (30-day IRDAI mandate)

Generate the full appeal letter text now:"""

    logger.info("[Barrister] Generating appeal letter via LLM...")
    appeal_text = client.generate(
        prompt=prompt,
        system=sys_instr,
        temperature=0.3,
        max_tokens=2048,
        json_mode=False,
    )

    if not appeal_text or len(appeal_text.strip()) < 100:
        logger.error("[Barrister] Empty response from LLM.")
        return None

    return appeal_text.strip()
