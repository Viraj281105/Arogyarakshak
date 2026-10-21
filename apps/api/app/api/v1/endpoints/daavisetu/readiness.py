"""DaaviSetu institution playbooks and pre-authorisation readiness (ADR-011): institution
registration (X-Institution-Token), private playbook versioning, the readiness checklist
and doctor-confirmation requests. Readiness is never an approval prediction."""

import logging
import uuid
from datetime import date
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app import daavisetu_playbooks as playbooks
from app.case_auth import require_case_access
from app.clinical import service as clinical_service
from app.clinical.auth import (
    INSTITUTION_TOKEN_HEADER,
    generate_credential,
    require_institution,
    resolve_institution,
)
from app.clinical.context import load_entity_records
from app.clinical.serializers import case_holder_review_view
from app.consent import require_case_consent
from app.database import get_db
from app.models import DaaviSetuInstitution, KadiCase
from daavisetu.readiness import BASELINE_ITEMS
from kadi.clinical_review import ReviewTrigger, ReviewType, SourceModule
# Import daavisetu packages

logger = logging.getLogger("arogyarakshak.api.daavisetu")
router = APIRouter()


# --- Institution playbooks & preauth readiness (ADR-011) ----------------------------

class InstitutionRegistration(BaseModel):
    name: str = Field(..., min_length=2, max_length=160)


class PlaybookWrite(BaseModel):
    playbook_key: Optional[str] = Field(None, max_length=61)
    title: str = Field(..., max_length=200)
    insurer: str = Field(..., max_length=160)
    policy_product: Optional[str] = Field(None, max_length=200)
    procedure_category: str = Field(..., max_length=200)
    items: List[Dict[str, Any]] = Field(default_factory=list, max_length=40)
    commonly_requested_evidence: List[str] = Field(default_factory=list, max_length=30)
    internal_notes: Optional[str] = Field(None, max_length=2000)
    source_provenance: str = Field(..., max_length=300, description="Where this guidance comes from, e.g. 'TPA query letters 2025, desk experience'.")
    owner: str = Field(..., max_length=160)
    effective_date: date
    review_due_date: date


class ReadinessRequest(BaseModel):
    playbook_id: Optional[str] = Field(None, max_length=40)


class ClinicalConfirmationRequest(BaseModel):
    item_ids: List[str] = Field(..., min_length=1, max_length=20)
    playbook_id: Optional[str] = Field(None, max_length=40)
    insurer_name: Optional[str] = Field(None, max_length=120)
    share_with_reviewer_consent: bool = False


@router.post("/institutions", status_code=status.HTTP_201_CREATED)
async def register_institution(req: InstitutionRegistration, db: AsyncSession = Depends(get_db)):
    """A hospital insurance desk registers to keep private playbooks. The credential is
    shown once; only its hash is stored."""
    token, token_hash = generate_credential()
    institution = DaaviSetuInstitution(id=f"INST-{uuid.uuid4().hex[:12]}", name=req.name.strip(), credential_hash=token_hash)
    db.add(institution)
    await db.commit()
    return {
        "institution": {"id": institution.id, "name": institution.name},
        "institution_token": token,
        "note": f"Store this credential now — it is shown only once. Send it as the {INSTITUTION_TOKEN_HEADER} header.",
    }


@router.get("/playbooks")
async def list_playbooks(institution: DaaviSetuInstitution = Depends(require_institution), db: AsyncSession = Depends(get_db)):
    return [playbooks.playbook_view(p, institution.name) for p in await playbooks.list_playbooks(db, institution)]


@router.post("/playbooks", status_code=status.HTTP_201_CREATED)
async def create_playbook(req: PlaybookWrite, institution: DaaviSetuInstitution = Depends(require_institution), db: AsyncSession = Depends(get_db)):
    pb = await playbooks.create_playbook(db, institution, req.model_dump())
    await db.commit()
    return playbooks.playbook_view(pb, institution.name)


@router.get("/playbooks/{playbook_id}")
async def get_playbook(playbook_id: str, institution: DaaviSetuInstitution = Depends(require_institution), db: AsyncSession = Depends(get_db)):
    return playbooks.playbook_view(await playbooks.own_playbook(db, institution, playbook_id), institution.name)


@router.put("/playbooks/{playbook_id}")
async def update_playbook(playbook_id: str, req: PlaybookWrite, institution: DaaviSetuInstitution = Depends(require_institution), db: AsyncSession = Depends(get_db)):
    pb = await playbooks.own_playbook(db, institution, playbook_id)
    playbooks.update_playbook(pb, req.model_dump())
    await db.commit()
    return playbooks.playbook_view(pb, institution.name)


@router.post("/playbooks/{playbook_id}/activate")
async def activate_playbook(playbook_id: str, institution: DaaviSetuInstitution = Depends(require_institution), db: AsyncSession = Depends(get_db)):
    pb = await playbooks.own_playbook(db, institution, playbook_id)
    await playbooks.activate_playbook(db, pb)
    await db.commit()
    return playbooks.playbook_view(pb, institution.name)


@router.post("/playbooks/{playbook_id}/new-version", status_code=status.HTTP_201_CREATED)
async def new_playbook_version(playbook_id: str, institution: DaaviSetuInstitution = Depends(require_institution), db: AsyncSession = Depends(get_db)):
    pb = await playbooks.own_playbook(db, institution, playbook_id)
    draft = await playbooks.new_playbook_version(db, pb)
    await db.commit()
    return playbooks.playbook_view(draft, institution.name)


@router.post("/playbooks/{playbook_id}/retire")
async def retire_playbook(playbook_id: str, institution: DaaviSetuInstitution = Depends(require_institution), db: AsyncSession = Depends(get_db)):
    pb = await playbooks.own_playbook(db, institution, playbook_id)
    playbooks.retire_playbook(pb)
    await db.commit()
    return playbooks.playbook_view(pb, institution.name)


async def _playbook_for_case_request(
    db: AsyncSession, playbook_id: Optional[str], institution_token: Optional[str]
):
    if not playbook_id:
        return None, None
    institution = await resolve_institution(db, institution_token)
    if institution is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Applying an institution playbook requires that institution's {INSTITUTION_TOKEN_HEADER}.",
        )
    pb = await playbooks.own_playbook(db, institution, playbook_id)
    playbooks.ensure_applicable(pb)
    return pb, institution


@router.post("/cases/{case_id}/readiness")
async def preauth_readiness(
    case_id: str,
    req: ReadinessRequest,
    case: KadiCase = Depends(require_case_access),
    db: AsyncSession = Depends(get_db),
    x_institution_token: Optional[str] = Header(None, alias=INSTITUTION_TOKEN_HEADER),
):
    """Documentation completeness for a cashless pre-authorization. Presence comes only
    from this case's evidence; clinical facts stay unconfirmed until a named reviewer
    decides them. Never an approval prediction."""
    require_case_consent(case)
    pb, institution = await _playbook_for_case_request(db, req.playbook_id, x_institution_token)
    report = playbooks.build_report(
        await load_entity_records(db, case_id),
        case.total_charged,
        await clinical_service.latest_fact_decisions(db, case_id),
        pb,
    )
    return {
        "case_id": case_id,
        "guidance": playbooks.playbook_view(pb, institution.name) if pb else None,
        "guidance_label": (
            f"{pb.title} (v{pb.version}, {institution.name})" if pb else "DaaviSetu generic baseline only"
        ),
        **report.model_dump(),
    }


@router.post("/cases/{case_id}/readiness/clinical-confirmations", status_code=status.HTTP_201_CREATED)
async def request_clinical_confirmation(
    case_id: str,
    req: ClinicalConfirmationRequest,
    case: KadiCase = Depends(require_case_access),
    db: AsyncSession = Depends(get_db),
    x_institution_token: Optional[str] = Header(None, alias=INSTITUTION_TOKEN_HEADER),
):
    """Routes the checklist's clinical facts to a named doctor for confirmation. The fact
    wording comes from the server-side checklist, never from the request, so a request
    cannot smuggle an assertion in as a 'fact'."""
    pb, _ = await _playbook_for_case_request(db, req.playbook_id, x_institution_token)
    items = {i.item_id: i for i in BASELINE_ITEMS}
    if pb:
        items.update({i.item_id: i for i in playbooks.playbook_items(pb)})
    facts = []
    for item_id in dict.fromkeys(req.item_ids):
        item = items.get(item_id)
        if item is None or not item.clinical_fact:
            raise HTTPException(status_code=422, detail=f"'{item_id}' is not a clinical-fact checklist item.")
        facts.append({
            "fact_key": item.item_id,
            "question": item.clinical_fact_question,
            "source": "daavisetu_readiness",
            "playbook_ref": f"{pb.id}@v{pb.version}" if pb else None,
        })
    review = await clinical_service.create_review(
        db,
        case,
        source_module=SourceModule.DAAVISETU.value,
        review_type=ReviewType.FACT_CONFIRMATION.value,
        clinical_question="Please confirm or reject each clinical fact below using only the records shared with you.",
        entities=await load_entity_records(db, case_id),
        evidence_scope=None,
        insurer_name=req.insurer_name,
        trigger=ReviewTrigger.READINESS_CLINICAL_FACT.value,
        trigger_ref=f"{pb.id}@v{pb.version}" if pb else "baseline",
        share_with_reviewer_consent=req.share_with_reviewer_consent,
        facts=facts,
    )
    await db.commit()
    return case_holder_review_view(review, None, [], await clinical_service.facts_for_review(db, review.id))
