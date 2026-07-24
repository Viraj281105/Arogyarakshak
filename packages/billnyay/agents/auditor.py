"""
BillNyay — Auditor Agent.

Extracts structured denial details, policy clauses, and evidence chunks
from hospital bills, insurance claim forms, or rejection letters.
"""

import json
import logging
import re
from typing import Any, ClassVar, Dict, List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger("BillNyay.AuditorAgent")
logger.setLevel(logging.INFO)


class StructuredDenial(BaseModel):
    """Auditor Agent → unified structured memory object."""

    _SCHEMA: ClassVar[dict] = {}
    denial_code: str
    insurer_reason_snippet: str
    policy_clause_text: str
    procedure_denied: str
    confidence_score: float
    raw_evidence_chunks: List[str] = Field(default_factory=list)


if not StructuredDenial._SCHEMA:
    StructuredDenial._SCHEMA = StructuredDenial.model_json_schema()


def find_relevant_policy_snippet(full_policy_text: str) -> str:
    """Finds policy exclusions/limitations in text."""
    keys = [
        "EXCLUSIONS",
        "LIMITATIONS",
        "EXPERIMENTAL",
        "INVESTIGATIVE",
        "UNPROVEN",
        "NOT COVERED",
        "OVERCHARGE",
        "CEILING RATE",
    ]
    for kw in keys:
        m = re.search(
            rf".{{0,1500}}{re.escape(kw)}.{{0,1500}}",
            full_policy_text,
            re.IGNORECASE | re.DOTALL,
        )
        if m:
            blk = m.group(0)
            paras = re.split(r"\n{2,}", blk)
            for p in paras:
                if any(k in p.upper() for k in keys):
                    return p.strip()
            return blk.strip()
    snippet = full_policy_text[:4000]
    return snippet.rsplit("\n", 1)[0].strip()


def extract_first_json(text: str) -> Optional[Dict[str, Any]]:
    """Extracts valid JSON object from LLM response text."""
    if not text:
        return None
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
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


def run_auditor_agent(
    client, denial_text: str, policy_text: str = "", **kwargs
) -> Optional[StructuredDenial]:
    """Runs the Auditor Agent against text extracted from bill/rejection document."""
    if not denial_text or not denial_text.strip():
        logger.error("[Auditor] Empty denial text provided.")
        return None

    policy_excerpt = find_relevant_policy_snippet(policy_text) if policy_text else "General hospital billing & insurance policy."
    denial_text_trimmed = denial_text[:8000]
    policy_excerpt_trimmed = policy_excerpt[:4000]

    sys_instr = (
        "You are the Auditor Agent for BillNyay.\n"
        "Extract only facts from the hospital bill/denial letter and policy document.\n"
        "Output STRICT JSON ONLY. No markdown. No explanation.\n"
        "Follow this exact JSON format:\n"
        "{\n"
        '  "denial_code": "string",\n'
        '  "insurer_reason_snippet": "string",\n'
        '  "policy_clause_text": "string",\n'
        '  "procedure_denied": "string",\n'
        '  "confidence_score": 0.95,\n'
        '  "raw_evidence_chunks": []\n'
        "}\n\n"
        "Rules:\n"
        "- If a field is missing in source text, use empty string or 0.0.\n"
        "- Do NOT hallucinate.\n"
        "- 'raw_evidence_chunks' MUST be an empty list [].\n"
        "- Output ONLY the JSON object. Nothing else."
    )

    prompt = (
        "--- DENIAL / BILL DOCUMENT ---\n"
        f"{denial_text_trimmed}\n\n"
        "--- RELEVANT POLICY EXCERPT ---\n"
        f"{policy_excerpt_trimmed}\n\n"
        "Now output the JSON object:"
    )

    logger.info("[Auditor] Sending prompt to LLM...")
    raw = client.generate(
        prompt=prompt, system=sys_instr, temperature=0.0, max_tokens=1024, json_mode=True
    )

    if not raw:
        logger.error("[Auditor] Empty response from LLM.")
        return None

    try:
        sd = StructuredDenial.model_validate_json(raw)
    except Exception:
        logger.warning("[Auditor] Strict JSON parse failed, attempting recovery.")
        recovered = extract_first_json(raw)
        if not recovered:
            logger.error("[Auditor] Could not recover JSON from response.")
            return None
        try:
            sd = StructuredDenial.model_validate(recovered)
        except Exception as e:
            logger.error(f"[Auditor] Recovery JSON invalid: {e}")
            return None

    sd.raw_evidence_chunks = [line.strip() for line in denial_text.splitlines() if len(line.strip()) > 30][:24]
    logger.info(f"[Auditor] SUCCESS — Code: {sd.denial_code}, Procedure: {sd.procedure_denied}")
    return sd
