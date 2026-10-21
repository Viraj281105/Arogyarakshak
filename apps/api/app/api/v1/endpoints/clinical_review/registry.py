"""Reviewer registry routes: self-registration, directory, profile, and the operator-only
board seating and verification attempts (X-Governance-Admin-Key)."""

import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from kadi.clinical_review import (
    ActorType,
    AuditEventType,
    ReviewerCategory,
    VerificationStatus,
)
from kadi.clinical_review.verification import (
    DEMO_VERIFICATION_SOURCE,
    UnavailableRegistryAdapter,
    initial_verification_status,
)

from app.clinical.audit import record_event
from app.clinical.auth import (
    generate_credential,
    listed_in_directory,
    require_governance_admin,
    require_reviewer,
    reviewer_available,
)
from app.clinical.serializers import (
    reviewer_public,
)
from app.config import settings
from app.database import get_db
from app.models import KadiClinicalReviewer

router = APIRouter()
from app.api.v1.endpoints.clinical_review.schemas import BoardSeatRequest, ReviewerRegistration, VerificationRequest


# --- Reviewer registry ------------------------------------------------------------

@router.post("/clinical-reviewers", status_code=status.HTTP_201_CREATED)
async def register_reviewer(req: ReviewerRegistration, db: AsyncSession = Depends(get_db)):
    """Self-registration. The credential is returned exactly once. Verification status can
    never exceed SELF_DECLARED here — a claimed registration number is shown as claimed."""
    token, token_hash = generate_credential()
    reviewer = KadiClinicalReviewer(
        id=f"REV-{uuid.uuid4().hex[:12]}",
        name=req.name.strip(),
        category=req.category.value,
        designation=req.designation,
        specialty=req.specialty,
        registration_number=(req.registration_number or "").strip() or None,
        registration_authority=req.registration_authority,
        verification_status=initial_verification_status(req.registration_number),
        affiliation=req.affiliation,
        standing_disclosures=req.standing_disclosures,
        reviewer_notes=req.reviewer_notes,
        credential_hash=token_hash,
    )
    db.add(reviewer)
    record_event(
        db,
        event_type=AuditEventType.REVIEWER_REGISTERED.value,
        subject_type="REVIEWER",
        subject_id=reviewer.id,
        actor_type=ActorType.REVIEWER.value,
        actor_id=reviewer.id,
        details={"category": reviewer.category, "verification_status": reviewer.verification_status},
    )
    await db.commit()
    return {
        "reviewer": reviewer_public(reviewer),
        "reviewer_token": token,
        "note": (
            "Store this reviewer credential now — it is shown only once. Send it as the "
            "X-Reviewer-Token header. Your registration details are shown to patients as "
            "self-declared until verified."
        ),
    }


@router.get("/clinical-reviewers")
async def reviewer_directory(
    category: Optional[ReviewerCategory] = None,
    specialty: Optional[str] = Query(None, max_length=120),
    db: AsyncSession = Depends(get_db),
):
    """Public directory of reviewers a patient may pick without knowing them already.

    Only independently verified reviewers are listed (plus demo fixtures in demo mode).
    Self-registration cannot be verified in this build, so self-declared reviewers are
    never listed — otherwise anyone could list themselves under a real doctor's name.
    A patient assigns their own doctor by the reviewer ID that doctor gives them."""
    query = select(KadiClinicalReviewer).where(KadiClinicalReviewer.is_active.is_(True))
    if category:
        query = query.where(KadiClinicalReviewer.category == category.value)
    rows = [r for r in (await db.execute(query.order_by(KadiClinicalReviewer.name))).scalars().all() if listed_in_directory(r)]
    if specialty:
        rows = [r for r in rows if r.specialty and specialty.lower() in r.specialty.lower()]
    return [reviewer_public(r) for r in rows[:200]]


@router.get("/clinical-reviewers/me")
async def reviewer_me(reviewer: KadiClinicalReviewer = Depends(require_reviewer)):
    return reviewer_public(reviewer)


@router.post("/clinical-reviewers/me/deactivate")
async def deactivate_me(reviewer: KadiClinicalReviewer = Depends(require_reviewer), db: AsyncSession = Depends(get_db)):
    reviewer.is_active = False
    record_event(db, event_type=AuditEventType.REVIEWER_DEACTIVATED.value, subject_type="REVIEWER",
                 subject_id=reviewer.id, actor_type=ActorType.REVIEWER.value, actor_id=reviewer.id)
    await db.commit()
    return {"reviewer_id": reviewer.id, "is_active": False}


@router.get("/clinical-reviewers/{reviewer_id}")
async def reviewer_profile(reviewer_id: str, db: AsyncSession = Depends(get_db)):
    """Look up a reviewer by the ID they shared, to confirm who it is before assigning."""
    reviewer = await db.get(KadiClinicalReviewer, reviewer_id)
    if not reviewer_available(reviewer):
        raise HTTPException(status_code=404, detail="Reviewer not found.")
    return reviewer_public(reviewer)


@router.post("/clinical-reviewers/{reviewer_id}/safety-board")
async def set_board_seat(
    reviewer_id: str,
    req: BoardSeatRequest,
    admin: str = Depends(require_governance_admin),
    db: AsyncSession = Depends(get_db),
):
    reviewer = await db.get(KadiClinicalReviewer, reviewer_id)
    if reviewer is None:
        raise HTTPException(status_code=404, detail="Reviewer not found.")
    if req.seated and reviewer.category != ReviewerCategory.DOCTOR.value:
        raise HTTPException(status_code=422, detail="Only reviewers registered as doctors can sit on the safety board.")
    if req.seated and reviewer.verification_status == VerificationStatus.UNVERIFIED.value:
        raise HTTPException(status_code=422, detail="A board member must at least declare a registration number.")
    reviewer.is_safety_board_member = req.seated
    record_event(db, event_type=AuditEventType.REVIEWER_BOARD_SEAT_CHANGED.value, subject_type="REVIEWER",
                 subject_id=reviewer.id, actor_type=ActorType.GOVERNANCE_ADMIN.value, details={"seated": req.seated})
    await db.commit()
    return reviewer_public(reviewer)


@router.post("/clinical-reviewers/{reviewer_id}/verification")
async def attempt_verification(
    reviewer_id: str,
    req: VerificationRequest,
    admin: str = Depends(require_governance_admin),
    db: AsyncSession = Depends(get_db),
):
    """'external' calls the registry adapter — which, in this build, honestly reports that no
    registry integration exists and changes nothing. 'demo' is allowed only in demo mode."""
    reviewer = await db.get(KadiClinicalReviewer, reviewer_id)
    if reviewer is None:
        raise HTTPException(status_code=404, detail="Reviewer not found.")
    if req.mode == "demo":
        if not settings.clinical_demo_mode:
            raise HTTPException(status_code=403, detail="Demo verification is only available when CLINICAL_DEMO_MODE is on.")
        reviewer.verification_status = VerificationStatus.DEMO_VERIFIED.value
        reviewer.verification_source = DEMO_VERIFICATION_SOURCE
        reviewer.verification_timestamp = datetime.utcnow()
        outcome = {"outcome": VerificationStatus.DEMO_VERIFIED.value, "detail": DEMO_VERIFICATION_SOURCE}
    else:
        if not reviewer.registration_number:
            raise HTTPException(status_code=422, detail="The reviewer has not declared a registration number.")
        result = UnavailableRegistryAdapter().verify(
            registration_number=reviewer.registration_number,
            registration_authority=reviewer.registration_authority,
            name=reviewer.name,
        )
        if result.changes_status:  # unreachable with the shipped adapter; kept for a real one
            reviewer.verification_status = result.outcome
            reviewer.verification_source = result.source
            reviewer.verification_timestamp = result.checked_at
        outcome = {"outcome": result.outcome, "detail": result.detail}
    record_event(db, event_type=AuditEventType.REVIEWER_VERIFICATION_ATTEMPTED.value, subject_type="REVIEWER",
                 subject_id=reviewer.id, actor_type=ActorType.GOVERNANCE_ADMIN.value,
                 details={"mode": req.mode, "outcome": outcome["outcome"]})
    await db.commit()
    return {**outcome, "reviewer": reviewer_public(reviewer)}
