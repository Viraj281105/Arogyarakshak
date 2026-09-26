"""Kadi — clinical-review demo fixtures (ADR-011). Mounted under /api/v1/kadi."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.clinical.auth import require_governance_admin
from app.clinical.demo import seed_demo
from app.config import settings
from app.database import get_db

router = APIRouter()


@router.post("/clinical-demo/seed")
async def seed_clinical_demo(admin: str = Depends(require_governance_admin), db: AsyncSession = Depends(get_db)):
    """Creates (or re-issues credentials for) the demo reviewers, demo institution and
    playbook, and two demo safety rules. Disabled unless CLINICAL_DEMO_MODE is on."""
    if not settings.clinical_demo_mode:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Demo seeding is disabled. Set CLINICAL_DEMO_MODE=true (never in a real deployment).",
        )
    return await seed_demo(db)
