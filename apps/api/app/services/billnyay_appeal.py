"""
BillNyay appeal and grievance drafting — application use cases.

Moved out of ``app.api.v1.endpoints.billnyay`` (restructuring, 2026-10), where the 5-agent
orchestration lived inside the route handler. Three pieces were duplicated there and are
now shared:

- ``extract_denial``: load the case's document text, run the Auditor Agent, and fall back
  to an explicit "not specified" denial (used by the appeal and the grievance draft);
- ``render_signed_pdf``: compile → SHA-256 → HMAC sign (used when drafting and when a
  clinical statement change re-renders the annex);
- ``load_appeal``: the stored appeal record (drafting, annex refresh, download, verify).

Callers (routes) enforce case access and consent first.
"""

import logging
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.clinical.events import on_statements_changed
from app.clinical.serializers import annex_dict, statement_view
from app.clinical.service import current_statements_for_case
from app.config import settings
from app.models import BillNyayAppeal, KadiCase, KadiEntity
from app.services.billnyay_llm import llm_client
from billnyay.agents.auditor import StructuredDenial, run_auditor_agent
from billnyay.agents.clinician import run_clinician_agent
from billnyay.agents.consensus import (
    ConsensusResult,
    compute_weighted_consensus,
    vote_from_auditor,
    vote_from_clinician,
    vote_from_regulatory,
)
from billnyay.agents.feedback_loop import draft_with_self_correction
from billnyay.agents.regulatory import run_regulatory_agent
from billnyay.tools.pdf_compiler import compile_appeal_packet_bytes
from billnyay.tools.pdf_integrity import compute_sha256, sign_document
from kadi.clinical_review.annex import NO_HUMAN_STATEMENT_NOTICE, render_annex

logger = logging.getLogger("arogyarakshak.api.billnyay")

# Rendered into the appeal letter wherever a fact could not be extracted. Deliberately
# reads as unknown rather than resembling a real reference.
UNSPECIFIED_FIELD = "Not specified in the supplied documents"


class AppealResponse(BaseModel):
    case_id: str
    appeal_letter: str
    scorecard: Dict[str, Any]
    status: str
    # False when the Auditor could not extract denial facts from the uploaded document.
    # The letter is then built on placeholders and the user must fill in the real denial
    # code, insurer reason and policy clause before sending it.
    denial_facts_extracted: bool = True
    # False when GROQ_API_KEY is unset: the letter is a static statutory template rather
    # than an LLM draft grounded in this case. Callers must be able to tell the two apart.
    llm_backed: bool
    # #65 — cooperative pre-drafting vote across Auditor/Clinician/Regulatory, surfaced
    # alongside (not instead of) the Judge's own scoring of the finished letter.
    consensus: Dict[str, Any]
    # #68 — how many times the Barrister re-drafted after a needs_revision verdict.
    revision_count: int = 0
    revision_history: List[Dict[str, Any]] = []
    # #66 — integrity of the compiled, persisted PDF. See .../appeal/pdf and
    # .../appeal/verify.
    document_sha256: str
    pdf_download_url: str
    # #39 — the language the letter was actually drafted in (en/hi/mr), confirming the
    # request's ?language= was honoured rather than silently ignored.
    language: str = "en"
    # ADR-011 — attributed human clinical statements appended verbatim (never passed
    # through the LLM). When none exists the annex says so explicitly.
    human_clinical_statement_attached: bool = False
    clinical_statements: List[Dict[str, Any]] = []
    # Verbatim annex included in the PDF; empty when no statement exists.
    clinical_annex: str = ""
    # Patient-facing only (never put in the insurer-facing PDF): says plainly that no
    # clinician's opinion is attached when that is the case.
    clinical_statement_notice: str = ""


class GrievanceResponse(BaseModel):
    case_id: str
    complaint_text: str
    bima_bharosa_fields: Dict[str, str] = {}
    deep_link: str
    # False when the Auditor could not extract real denial facts from the uploaded
    # document (no GROQ_API_KEY, or the call fell back). The complaint is then built on
    # UNSPECIFIED_FIELD placeholders instead of a fabricated denial code/reason —
    # mirrors AppealResponse.denial_facts_extracted for the same reason.
    denial_facts_extracted: bool = True


class AppealDraftingFailed(Exception):
    """The Barrister Agent returned no letter."""


@dataclass
class DenialExtraction:
    denial: StructuredDenial
    # True only when a live LLM call produced the facts — a canned fallback response also
    # parses into a valid StructuredDenial, so "denial is not None" alone proves nothing.
    facts_extracted: bool
    client: Any


def unspecified_denial() -> StructuredDenial:
    """A neutral placeholder that reads as "unknown", never as a plausible denial code. A
    letter quoting "DEN-DEFAULT" as the insurer's reference would be sent to a real
    insurer as though it were genuine."""
    return StructuredDenial(
        denial_code=UNSPECIFIED_FIELD,
        insurer_reason_snippet=UNSPECIFIED_FIELD,
        policy_clause_text=UNSPECIFIED_FIELD,
        procedure_denied=UNSPECIFIED_FIELD,
        confidence_score=0.0,
        raw_evidence_chunks=[],
    )


async def case_document_text(db: AsyncSession, case_id: str) -> str:
    result = await db.execute(
        select(KadiEntity).join(KadiCase.entities)
        .where(KadiCase.id == case_id)
        .where(KadiEntity.type == "document_text")
    )
    return "\n".join(e.value for e in result.scalars().all() if e.value)


async def extract_denial(db: AsyncSession, case_id: str, *, empty_text_default: Optional[str]) -> DenialExtraction:
    """Agent 1 (Auditor) over the case's stored document text.

    ``empty_text_default``: what to send the Auditor when the case has no text (the appeal
    sends a generic prompt); ``None`` skips the Auditor entirely (the grievance).

    SEC-01: every agent calls ``client.generate()``, a synchronous urllib call to Groq (or
    an instant canned return offline) — run off the event loop so one in-flight draft
    cannot stall /health or any other request.
    """
    client = llm_client()
    text = await case_document_text(db, case_id) or empty_text_default
    denial = await run_in_threadpool(run_auditor_agent, client=client, denial_text=text) if text else None
    facts_extracted = denial is not None and not client.used_fallback
    return DenialExtraction(denial=denial or unspecified_denial(), facts_extracted=facts_extracted, client=client)


async def clinical_annex_for(db: AsyncSession, case_id: str):
    """(current statements, annex text). The annex is empty when no statement exists:
    the insurer-facing PDF then simply carries no annex, while the patient is told
    separately (``clinical_statement_notice``) that no clinician opinion is attached."""
    statements = await current_statements_for_case(db, case_id, ["billnyay"])
    annex = render_annex([annex_dict(s) for s in statements]) if statements else ""
    return statements, annex


async def render_signed_pdf(letter: str, case_id: str, annex: str) -> Tuple[bytes, str, str]:
    """(pdf bytes, SHA-256, HMAC signature) — the exact bytes served by .../appeal/pdf and
    checked by .../appeal/verify (#66)."""
    pdf_bytes = await run_in_threadpool(
        compile_appeal_packet_bytes, letter, case_meta={"case_id": case_id}, clinical_annex=annex or None
    )
    return pdf_bytes, compute_sha256(pdf_bytes), sign_document(pdf_bytes, settings.document_signing_secret)


async def load_appeal(db: AsyncSession, case_id: str) -> Optional[BillNyayAppeal]:
    result = await db.execute(select(BillNyayAppeal).where(BillNyayAppeal.case_id == case_id))
    return result.scalar_one_or_none()


async def draft_case_appeal(db: AsyncSession, case_id: str, language: str) -> AppealResponse:
    """The 5-agent pipeline: Auditor → Clinician → Regulatory → consensus vote →
    Barrister drafts / Judge scores with self-correction → signed PDF persisted."""
    extraction = await extract_denial(db, case_id, empty_text_default="Hospital Bill dispute.")
    client, denial = extraction.client, extraction.denial

    # Agent 2 — Clinician: synthesise medical-necessity evidence.
    clinical_evidence = await run_in_threadpool(run_clinician_agent, client=client, denial_details=denial)
    # Agent 3 — Regulatory: applicable statutory provisions (deterministic; kept on the
    # threadpool so it never becomes a blocking call unnoticed if that changes).
    regulatory_evidence = await run_in_threadpool(
        run_regulatory_agent, denial_data=denial.model_dump(), client=client
    )
    # #65: a transparency/triage vote across the three upstream agents, surfaced alongside
    # — not instead of — the Judge's scoring of the finished letter.
    consensus: ConsensusResult = compute_weighted_consensus([
        vote_from_auditor(denial, extraction.facts_extracted),
        vote_from_clinician(clinical_evidence),
        vote_from_regulatory(regulatory_evidence),
    ])
    # Agents 4 & 5 — Barrister drafts, Judge scores, with self-correcting revision (#68).
    # Several sequential LLM calls: the most important one to keep off the event loop.
    drafting = await run_in_threadpool(
        draft_with_self_correction,
        client,
        denial_details=denial,
        clinical_evidence=clinical_evidence,
        regulatory_evidence=regulatory_evidence,
        language=language,
    )
    if drafting is None:
        logger.error("[BillNyay] Barrister Agent returned no appeal letter for case %s", case_id)
        raise AppealDraftingFailed()

    # ADR-011: finalized human statements, rendered verbatim by deterministic code. The
    # LLM-drafted letter never contains them.
    statements, annex = await clinical_annex_for(db, case_id)
    pdf_bytes, sha256, signature = await render_signed_pdf(drafting.appeal_letter, case_id, annex)

    record = await load_appeal(db, case_id)
    if record is None:
        record = BillNyayAppeal(id=f"APPEAL-{uuid.uuid4().hex[:10]}", case_id=case_id)
        db.add(record)
    record.appeal_letter = drafting.appeal_letter
    record.pdf_bytes = pdf_bytes
    record.sha256_hash = sha256
    record.hmac_signature = signature
    await db.commit()

    scorecard = drafting.scorecard
    return AppealResponse(
        case_id=case_id,
        appeal_letter=drafting.appeal_letter,
        scorecard=scorecard.model_dump(),
        status=scorecard.status,
        llm_backed=bool(settings.groq_api_key),
        denial_facts_extracted=extraction.facts_extracted,
        consensus=consensus.model_dump(mode="json"),
        revision_count=drafting.revision_count,
        revision_history=[r.model_dump() for r in drafting.revision_history],
        document_sha256=sha256,
        pdf_download_url=f"/api/v1/billnyay/cases/{case_id}/appeal/pdf",
        language=language,
        human_clinical_statement_attached=bool(statements),
        clinical_statements=[statement_view(s) for s in statements],
        clinical_annex=annex,
        clinical_statement_notice="" if statements else NO_HUMAN_STATEMENT_NOTICE,
    )


@on_statements_changed
async def refresh_appeal_annex(db: AsyncSession, case_id: str, source_module: str) -> None:
    """ADR-011: when a BillNyay statement is finalized, superseded, withdrawn or its review
    cancelled, re-render the stored appeal PDF with the current annex and re-sign it.
    The letter text is unchanged (no LLM call). A copy downloaded earlier will now fail
    GET .../appeal/verify, which is the intended signal that it is out of date."""
    if source_module != "billnyay":
        return
    record = await load_appeal(db, case_id)
    if record is None:
        return
    _, annex = await clinical_annex_for(db, case_id)
    record.pdf_bytes, record.sha256_hash, record.hmac_signature = await render_signed_pdf(
        record.appeal_letter, case_id, annex
    )
    logger.info("[BillNyay] Re-rendered appeal PDF annex for case %s after a statement change.", case_id)


async def draft_case_grievance(db: AsyncSession, case: KadiCase) -> GrievanceResponse:
    """IRDAI Bima Bharosa complaint package (#51), built from the same Auditor extraction
    as the appeal — this case's denial facts, or honest placeholders."""
    extraction = await extract_denial(db, case.id, empty_text_default=None)
    denial = extraction.denial
    complaint_text = (
        "Grievance Complaint filed under IRDAI Bima Bharosa Portal.\n"
        f"Case Reference: {case.id}\n"
        f"Denial/Reference Code: {denial.denial_code}\n"
        f"Procedure/Service Disputed: {denial.procedure_denied}\n"
        f"Insurer's Stated Reason: {denial.insurer_reason_snippet}\n"
        f"Disputed Amount: Rs. {case.total_charged:.2f}\n"
        "The policyholder disputes the above rejection/deduction and seeks reversal "
        "under the IRDAI (Protection of Policyholders' Interests) Regulations."
    )
    # Required fields structure for manual copying
    fields = {
        "Complaint Type": "Claim Rejection / Unfair Deduction",
        "Insurer Category": "Health Insurance Company",
        "Disputed Amount": f"{case.total_charged:.2f}",
        "Policyholder Consent": "Yes",
    }
    return GrievanceResponse(
        case_id=case.id,
        complaint_text=complaint_text,
        denial_facts_extracted=extraction.facts_extracted,
        bima_bharosa_fields=fields,
        deep_link="https://bimabharosa.irdai.gov.in/RegisterNewGrievance",
    )
