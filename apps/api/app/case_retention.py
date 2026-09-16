"""
Server-Side Case Retention & Automatic Purge (SEC-03).

Before this module existed, the ONLY way a case (and everything derived from it) was
ever deleted was the client-initiated ``DELETE /cases/{id}`` route (P1-10) — which
requires presenting the case's access token. A client that simply lost that one-time
token (closed the tab, cleared the app's in-memory token store, uninstalled the mobile
app, or just never came back) had no way to ever trigger deletion again, so the case's
data was retained on the server indefinitely by default. That directly contradicted
ADR-003's description of case records as "transient".

This closes that gap with a TTL the server enforces on its own:

- Every case gets a `KadiCase.expires_at` deadline at creation
  (`created_at + settings.case_ttl_days`, see app/config.py) — set unconditionally,
  never dependent on any later client action.
- `sweep_expired_cases` runs on a periodic background task (started from the FastAPI
  lifespan, see app/main.py) and purges every case whose deadline has passed, using the
  exact same cascade (`purge_case`) the client-initiated DELETE route uses — so an
  expired case's entities, redacted document excerpt, generated PDFs, and any
  case-linked BimaNyay record (SEC-04) are all removed, not just the case row.
- A case with a NULL `expires_at` (a pre-existing row from before this column existed)
  is treated as already-expired and purged on the next sweep, never as "keep forever" —
  the safe default for retention is to expire, not to retain silently.

This documents and delivers the actual retention lifecycle ADR-003 always claimed:
cases are genuinely temporary, on a schedule the server itself enforces.
"""

import asyncio
import logging
from datetime import datetime
from typing import List

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import KadiCase

logger = logging.getLogger("arogyarakshak.api.case_retention")


async def find_expired_case_ids(db: AsyncSession, *, now: "datetime | None" = None) -> List[str]:
    """Case ids whose retention deadline has passed (or was never set — treated as
    already-expired, never as unlimited retention)."""
    now = now or datetime.utcnow()
    result = await db.execute(
        select(KadiCase.id).where(or_(KadiCase.expires_at.is_(None), KadiCase.expires_at <= now))
    )
    return [row[0] for row in result.all()]


async def sweep_expired_cases(db: AsyncSession) -> int:
    """Purges every expired case via the same cascade the client-initiated DELETE route
    uses. Returns the number of cases purged. Commits per case, so one bad case cannot
    abort the whole sweep."""
    from app.api.v1.endpoints.kadi import purge_case  # local import: avoids a circular import at module load

    expired_ids = await find_expired_case_ids(db)
    purged = 0
    for case_id in expired_ids:
        try:
            await purge_case(db, case_id)
            await db.commit()
            purged += 1
        except Exception:
            await db.rollback()
            logger.exception("Failed to purge expired case %s; will retry on the next sweep.", case_id)

    if purged:
        logger.info("Retention sweep purged %d expired case(s).", purged)
    return purged


async def run_retention_sweep_loop(stop_event: asyncio.Event) -> None:
    """Runs `sweep_expired_cases` on a fixed interval until `stop_event` is set — the
    long-running background task started from the FastAPI lifespan (app/main.py)."""
    from app.background import get_background_session

    while not stop_event.is_set():
        try:
            async with get_background_session() as session:
                await sweep_expired_cases(session)
        except Exception:
            logger.exception("Retention sweep iteration failed; will retry on the next interval.")

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=settings.case_purge_interval_seconds)
        except asyncio.TimeoutError:
            pass  # normal: interval elapsed, loop again
