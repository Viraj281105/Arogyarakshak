"""
SchemeSetu case eligibility — application use case.

Moved out of ``app.api.v1.endpoints.schemesetu`` (ADR-018): shared by the case route
and Kadi's auto-triggers. The route module re-exports these names. Callers must enforce
case access and consent first.
"""

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import KadiCase, KadiEntity
from schemesetu.agent import EligibilityRequest, SchemeResult, check_eligibility


class CaseMedicalNeedMissing(Exception):
    """No medical need was supplied and the case has no diagnosis/procedure entities."""


async def case_medical_need(case_id: str, db: AsyncSession) -> Optional[str]:
    entities_result = await db.execute(
        select(KadiEntity)
        .join(KadiCase.entities)
        .where(KadiCase.id == case_id, KadiEntity.type.in_(["diagnosis", "procedure"]))
    )
    # De-duplicated, order-preserving: a case can carry the same procedure name from more
    # than one source document.
    names = list(dict.fromkeys(e.name for e in entities_result.scalars().all() if e.name))
    return "; ".join(names) if names else None


async def build_case_eligibility(
    case_id: str,
    *,
    income: float,
    location_state: str,
    category: str,
    medical_need: Optional[str],
    db: AsyncSession,
) -> List[SchemeResult]:
    """Shared by the route above and Kadi's auto-triggers (#32, #92). Callers enforce
    consent first."""
    medical_need = medical_need or await case_medical_need(case_id, db)
    if not medical_need:
        raise CaseMedicalNeedMissing()
    return check_eligibility(
        EligibilityRequest(
            income=income, location_state=location_state, category=category, medical_need=medical_need
        )
    )
