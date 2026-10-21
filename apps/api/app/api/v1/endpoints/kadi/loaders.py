"""Case loading shared by the Kadi route groups."""

from typing import Optional
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models import (
    KadiCase,
)
from app.services.case_ingestion import (  # noqa: F401 — re-exported for existing importers
    DUPLICATE_DOCUMENT_LOG,
    MAX_TRACKED_STATUS_CASES,
    _document_already_ingested,
    _duplicate_event,
    _evict_stale_status_entries,
    _record_case_latency,
    _wrap_session,
    create_case_record,
    ingest_document_now,
    process_document_background,
    processing_status,
)
from app.services.case_purge import (  # noqa: F401 — re-exported for existing importers
    _purge_bimanyay_records_for_case,
    purge_case,
)


logger = logging.getLogger("arogyarakshak.api.kadi")


async def _load_case_with_entities(db: AsyncSession, case_id: str) -> Optional[KadiCase]:
    result = await db.execute(
        select(KadiCase)
        .options(selectinload(KadiCase.entities))
        .where(KadiCase.id == case_id)
        .execution_options(populate_existing=True)
    )
    return result.scalar_one_or_none()
