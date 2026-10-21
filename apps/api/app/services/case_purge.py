"""
Case erasure — application use case (ADR-010).

Moved out of ``app.api.v1.endpoints.kadi`` (ADR-018). Shared by the client-initiated
``DELETE /kadi/cases/{id}`` route, the server-side retention sweep
(``app.case_retention``) and the demo reset. Previously the latter two imported the
route module lazily to dodge a circular import.
"""

import logging

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.clinical.purge import purge_clinical_records_for_case
from app.models import (
    BillNyayAppeal,
    BimaNyayCase,
    BimaNyayGrievance,
    BimaNyayTimelineEvent,
    DaaviSetuClaim,
    KadiCase,
    KadiCaseDocument,
    KadiDocumentJob,
    KadiEntity,
    KadiModuleInsight,
    KadiResolutionDecision,
    SchemeSetuCaseProfile,
    kadi_case_entities,
)

logger = logging.getLogger("arogyarakshak.api.kadi")


async def purge_case(db: AsyncSession, case_id: str) -> None:
    """Deletes a case and everything derived from it. Shared by the DELETE route above
    (client-initiated) and app.case_retention's periodic sweep (SEC-03,
    server-initiated on expiry — does NOT depend on the client ever coming back with
    its token). Does not commit; the caller controls the transaction boundary."""
    entity_ids_result = await db.execute(
        select(kadi_case_entities.c.entity_id).where(kadi_case_entities.c.case_id == case_id)
    )
    entity_ids = [row[0] for row in entity_ids_result.all()]

    await db.execute(delete(kadi_case_entities).where(kadi_case_entities.c.case_id == case_id))

    if entity_ids:
        still_linked_result = await db.execute(
            select(kadi_case_entities.c.entity_id.distinct()).where(
                kadi_case_entities.c.entity_id.in_(entity_ids)
            )
        )
        still_linked = {row[0] for row in still_linked_result.all()}
        now_orphaned = [eid for eid in entity_ids if eid not in still_linked]
        if now_orphaned:
            await db.execute(delete(KadiEntity).where(KadiEntity.id.in_(now_orphaned)))

    await db.execute(delete(KadiCaseDocument).where(KadiCaseDocument.case_id == case_id))
    await db.execute(delete(KadiDocumentJob).where(KadiDocumentJob.case_id == case_id))
    await db.execute(delete(KadiResolutionDecision).where(KadiResolutionDecision.case_id == case_id))
    await db.execute(delete(KadiModuleInsight).where(KadiModuleInsight.case_id == case_id))
    await db.execute(delete(SchemeSetuCaseProfile).where(SchemeSetuCaseProfile.case_id == case_id))
    await db.execute(delete(BillNyayAppeal).where(BillNyayAppeal.case_id == case_id))
    await db.execute(delete(DaaviSetuClaim).where(DaaviSetuClaim.case_id == case_id))
    await _purge_bimanyay_records_for_case(db, case_id)
    # ADR-011: reviews, statements, fact decisions, transcription tasks/readings and
    # their audit trail. Global reviewer/rule/playbook records are kept.
    await purge_clinical_records_for_case(db, case_id)
    await db.execute(delete(KadiCase).where(KadiCase.id == case_id))


async def _purge_bimanyay_records_for_case(db: AsyncSession, case_id: str) -> None:
    """SEC-04: deletes every BimaNyay dispute/grievance record explicitly linked to
    this case (case_id set), plus each grievance's timeline events. Explicit Python
    deletes rather than relying solely on ON DELETE CASCADE, same rationale as the rest
    of this route: identical behaviour under SQLite (no FK enforcement by default, used
    in tests) and Postgres (production)."""
    grievance_ids_result = await db.execute(
        select(BimaNyayGrievance.id).where(BimaNyayGrievance.case_id == case_id)
    )
    grievance_ids = [row[0] for row in grievance_ids_result.all()]
    if grievance_ids:
        await db.execute(
            delete(BimaNyayTimelineEvent).where(BimaNyayTimelineEvent.grievance_id.in_(grievance_ids))
        )
    await db.execute(delete(BimaNyayGrievance).where(BimaNyayGrievance.case_id == case_id))
    await db.execute(delete(BimaNyayCase).where(BimaNyayCase.case_id == case_id))
