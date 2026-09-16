"""
BillNyay — Clinician Agent.

Synthesizes medical justification and PubMed/clinical trial evidence
to demonstrate medical necessity or challenge invalid denial reasons.
"""

import json
import logging
import re
from typing import List, Optional
from pydantic import BaseModel, Field

from .auditor import StructuredDenial

logger = logging.getLogger("BillNyay.ClinicianAgent")
logger.setLevel(logging.INFO)


class ClinicalEvidence(BaseModel):
    article_title: str
    summary_of_finding: str
    # P1-7: NEVER populated from the LLM's own claim. This system has no real PubMed/NCBI
    # lookup, so any pubmed_id an LLM asserts is an unverifiable, likely-fabricated
    # identifier — exactly the kind of specific, checkable-looking fact the no-
    # fabrication principle forbids inventing. Stays None unless a real verification step
    # is added later (see run_clinician_agent's post-processing, which forces this to
    # None regardless of what the model returns).
    pubmed_id: Optional[str] = None


class EvidenceList(BaseModel):
    root: List[ClinicalEvidence] = Field(default_factory=list)


def _clean_json(text: str) -> str:
    if not text:
        return ""
    t = text.strip()
    t = re.sub(r"```(?:json)?", "", t).replace("```", "")
    return t.strip()


def _extract_first_json(text: str) -> Optional[dict]:
    if not text:
        return None
    start = text.find("{")
    if start == -1:
        start = text.find("[")
        if start == -1:
            return None
    open_char = text[start]
    close_char = "}" if open_char == "{" else "]"
    depth = 0
    for i in range(start, len(text)):
        if text[i] == open_char:
            depth += 1
        elif text[i] == close_char:
            depth -= 1
            if depth == 0:
                block = text[start : i + 1]
                try:
                    return json.loads(block)
                except Exception:
                    cleaned = re.sub(r",\s*([}\]])", r"\1", block)
                    try:
                        return json.loads(cleaned)
                    except Exception:
                        return None
    return None


def run_clinician_agent(client, denial_details: StructuredDenial, **kwargs) -> EvidenceList:
    """Returns EvidenceList containing clinical standard-of-care rationale for an appeal.

    P1-7 (fabricated citations): the previous system prompt literally instructed the
    model to "Generate realistic, evidence-backed clinical justifications" and asked for
    a pubmed_id per item — with no real PubMed/NCBI lookup anywhere in this system, that
    is an instruction to invent plausible-looking but fake citation identifiers, which
    then flowed into real appeal letters as if they were genuine sources. This system has
    no literature-search capability; asking an LLM to "be evidence-backed" cannot make one
    exist. The prompt now asks only for general clinical reasoning, and any pubmed_id the
    model returns anyway is discarded in post-processing (see below) — never trusted
    merely for being present in valid JSON.
    """
    logger.info("[Clinician] Synthesizing clinical standard-of-care rationale...")
    sys_instr = (
        "You are the Clinician Agent in BillNyay.\n"
        "Write general clinical standard-of-care reasoning supporting medical necessity, "
        "in your own words, for an insurance appeal.\n"
        "Output STRICT JSON ONLY matching this exact format:\n"
        '{"root": [{"article_title": "...", "summary_of_finding": "...", "pubmed_id": null}]}\n'
        "Rules:\n"
        "- Provide 2 to 3 clinical reasoning points.\n"
        "- Summarize clinical rationale and standard of care in general terms.\n"
        "- IMPORTANT: you have no access to PubMed or any literature database. You MUST "
        "set pubmed_id to null on every item. Do NOT invent a PMID, DOI, article "
        "citation number, or any other identifier that looks like a verifiable source — "
        "doing so would present a fabricated citation as real evidence in a legal "
        "document, which is never acceptable.\n"
        "- Output ONLY JSON. No explanation."
    )

    prompt = (
        f"Procedure / Treatment: {denial_details.procedure_denied}\n"
        f"Denial Reason: {denial_details.insurer_reason_snippet}\n"
        f"Policy Clause: {denial_details.policy_clause_text}\n\n"
        "Output clinical evidence JSON:"
    )

    raw = client.generate(
        prompt=prompt, system=sys_instr, temperature=0.2, max_tokens=1024, json_mode=True
    )

    if raw:
        clean = _clean_json(raw)
        try:
            evidence = EvidenceList.model_validate_json(clean)
            if evidence.root:
                return _strip_unverifiable_citations(evidence)
        except Exception:
            recovered = _extract_first_json(clean)
            if recovered:
                if isinstance(recovered, list):
                    recovered = {"root": recovered}
                try:
                    evidence = EvidenceList.model_validate(recovered)
                    if evidence.root:
                        return _strip_unverifiable_citations(evidence)
                except Exception:
                    pass

    logger.warning("[Clinician] LLM output parsing failed. Returning default clinical justification.")
    return EvidenceList(
        root=[
            ClinicalEvidence(
                article_title=f"Clinical Standard of Care for {denial_details.procedure_denied or 'Requested Medical Procedure'}",
                summary_of_finding="Established clinical guidelines generally support that medically indicated "
                "procedures for the stated diagnosis are appropriate standard of care. No specific literature "
                "citation is provided — this is general clinical reasoning, not a cited source.",
                pubmed_id=None,
            )
        ]
    )


def _strip_unverifiable_citations(evidence: EvidenceList) -> EvidenceList:
    """P1-7: even though the prompt instructs the model to always set pubmed_id to
    null, an LLM does not reliably follow instructions embedded in its own prompt (the
    same fact that makes prompt injection an unsolved problem, per P0-4) — this makes
    the guarantee structural instead of just requested. Any pubmed_id the model returns
    anyway is discarded here, unconditionally, before the result ever reaches a caller."""
    cleaned_items = []
    dropped = 0
    for item in evidence.root:
        if item.pubmed_id is not None:
            dropped += 1
            item = item.model_copy(update={"pubmed_id": None})
        cleaned_items.append(item)
    if dropped:
        logger.warning(
            "[Clinician] Discarded %d LLM-provided pubmed_id value(s) despite explicit "
            "instructions not to invent them — never trusting an unverifiable citation "
            "merely because it was present in valid JSON.",
            dropped,
        )
    return EvidenceList(root=cleaned_items)
