"""
Case-scoped clinical records are erased with their case (ADR-010, ADR-011).

Called from app.api.v1.endpoints.kadi.purge_case, which both the client DELETE route and
the retention sweep use. Explicit deletes (not only ON DELETE CASCADE) keep behaviour
identical under SQLite in tests and Postgres in production.

Global records are untouched: reviewers, safety rules and approvals, institutions and
playbooks do not belong to any one case. A finalized statement's reviewer snapshot is
deleted with the case; the reviewer's own registry record is not.
"""

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    KadiClinicalAuditEvent,
    KadiClinicalFactConfirmation,
    KadiClinicalReview,
    KadiClinicalStatement,
    KadiTranscriptionAssignment,
    KadiTranscriptionSubmission,
    KadiTranscriptionTask,
)

CASE_SCOPED_CLINICAL_MODELS = (
    KadiTranscriptionSubmission,
    KadiTranscriptionAssignment,
    KadiTranscriptionTask,
    KadiClinicalFactConfirmation,
    KadiClinicalStatement,
    KadiClinicalReview,
    KadiClinicalAuditEvent,
)


async def purge_clinical_records_for_case(db: AsyncSession, case_id: str) -> None:
    for model in CASE_SCOPED_CLINICAL_MODELS:
        await db.execute(delete(model).where(model.case_id == case_id))
