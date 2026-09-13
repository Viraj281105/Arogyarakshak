"""
Cross-Module Consent Enforcement.

ADR-003 and the README state that cross-module data sharing through Kadi requires an
explicit per-case patient opt-in. That promise was previously decorative:
``KadiCase.consent_opt_in`` was written at case creation and never read by anything.

Enforcement reads the **persisted** case row, never a per-request field, so a client
cannot grant itself access by sending ``consent_opt_in: true`` on the module call. The
only way to set it is at case creation, which is the patient's own action.

Modules that consume Kadi case context (BillNyay, DaaviSetu, and DawaCheck's
``GET /cases/{case_id}/benchmark``) must call ``require_case_consent``. A module route
that takes all its input from the request body and reads no case context (SchemeSetu;
DawaCheck's ``POST /benchmark``) is out of scope by design — consent enforcement is a
per-route decision based on whether that route reads case entities, not a per-module one.
"""

import logging

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import KadiCase

logger = logging.getLogger("arogyarakshak.api.consent")

CONSENT_REQUIRED_DETAIL = (
    "Cross-module analysis requires patient consent for this case. "
    "The case was created without consent_opt_in, so its extracted context cannot be "
    "shared with other modules. Create a new case with consent_opt_in=true to proceed."
)


async def require_case_consent(case_id: str, db: AsyncSession) -> KadiCase:
    """Loads a case and enforces its cross-module sharing consent.

    Raises 404 when the case does not exist, and 403 when consent was not granted.
    Returns the case so callers do not need a second query.
    """
    result = await db.execute(select(KadiCase).where(KadiCase.id == case_id))
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    if not case.consent_opt_in:
        logger.info("Blocked cross-module access to case %s: consent not granted.", case_id)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=CONSENT_REQUIRED_DETAIL
        )

    return case
