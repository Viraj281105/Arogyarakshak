"""Persisted processing state for uploaded documents (ADR-019).

The upload route records a ``queued`` job before it returns; the background pipeline
moves it to ``processing`` and then to a terminal state. Because the document bytes are
never stored (ADR-003), nothing here can retry a job: after a crash or restart the job
is marked ``interrupted`` and the client is asked to upload the document again.

Bookkeeping must never break the pipeline it describes, so the background-side helpers
log and swallow their own failures.
"""

import logging
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.background import get_background_session
from app.models import KadiDocumentJob

logger = logging.getLogger("arogyarakshak.api.document_jobs")

# Bump when the ingestion pipeline's behaviour changes in a way that could change what a
# document produces (OCR trust gate, extraction prompt, line-item grounding, ...).
PIPELINE_VERSION = "kadi-ingest/2026-10"

QUEUED = "queued"
PROCESSING = "processing"
COMPLETED = "completed"
DUPLICATE = "duplicate"
FAILED = "failed"
INTERRUPTED = "interrupted"

IN_FLIGHT = (QUEUED, PROCESSING)
TERMINAL = (COMPLETED, DUPLICATE, FAILED, INTERRUPTED)

INTERRUPTED_LOG = (
    "Processing of the last document was interrupted because the server restarted. "
    "Nothing from that document was saved. Please upload it again."
)
FAILED_LOG = "Processing of the last document failed. Please try uploading the document again."


async def create_job(db: AsyncSession, case_id: str, sha256: str, state: str = QUEUED) -> str:
    """Adds a job row to ``db`` (the caller commits) and returns its id."""
    job_id = f"JOB-{uuid.uuid4().hex[:16]}"
    now = datetime.utcnow()
    db.add(
        KadiDocumentJob(
            id=job_id,
            case_id=case_id,
            sha256=sha256,
            state=state,
            pipeline_version=PIPELINE_VERSION,
            created_at=now,
            updated_at=now,
            finished_at=now if state in TERMINAL else None,
        )
    )
    return job_id


async def set_state(job_id: Optional[str], state: str, error_id: Optional[str] = None) -> None:
    """Moves a job to ``state`` in its own session. Never raises."""
    if not job_id:
        return
    try:
        async with get_background_session() as session:
            values = {"state": state, "updated_at": datetime.utcnow()}
            if state in TERMINAL:
                values["finished_at"] = datetime.utcnow()
            if error_id:
                values["error_id"] = error_id
            # Terminal states are final: a late write cannot resurrect or overwrite one.
            await session.execute(
                update(KadiDocumentJob)
                .where(KadiDocumentJob.id == job_id, KadiDocumentJob.state.in_(IN_FLIGHT))
                .values(**values)
            )
            await session.commit()
    except Exception:  # bookkeeping must not fail the pipeline
        logger.exception("Could not record state %s for document job %s", state, job_id)


async def mark_interrupted_jobs(db: AsyncSession) -> int:
    """Marks every in-flight job as interrupted. Call once at start-up, before any upload
    is accepted: with a single API process (ADR-019) nothing can still be running then.
    Returns the number of jobs marked."""
    now = datetime.utcnow()
    result = await db.execute(
        update(KadiDocumentJob)
        .where(KadiDocumentJob.state.in_(IN_FLIGHT))
        .values(state=INTERRUPTED, updated_at=now, finished_at=now)
    )
    await db.commit()
    return result.rowcount or 0


async def latest_job(db: AsyncSession, case_id: str) -> Optional[KadiDocumentJob]:
    result = await db.execute(
        select(KadiDocumentJob)
        .where(KadiDocumentJob.case_id == case_id)
        .order_by(KadiDocumentJob.created_at.desc(), KadiDocumentJob.id.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


def job_view(job: Optional[KadiDocumentJob]) -> Optional[dict]:
    """Client-facing summary: ids, state and times only."""
    if job is None:
        return None
    return {
        "job_id": job.id,
        "state": job.state,
        "pipeline_version": job.pipeline_version,
        "error_id": job.error_id,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "finished_at": job.finished_at.isoformat() if job.finished_at else None,
    }
