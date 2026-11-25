"""Kadi — demo kit routes (ADR-011 demo infrastructure). Mounted under /api/v1/kadi.

`GET /clinical-demo/status` needs a signed-in account (ADR-029); it says whether this server
runs in demo mode and what is simulated, so a client can show an honest DEMO MODE banner. Every mutating
route needs the governance key AND demo mode AND a non-production APP_ENV.
"""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.account_auth import require_principal
from app.clinical.auth import require_governance_admin
from app.clinical.demo import seed_demo
from app.clinical.demo_control import demo_status, load_scenario, reset_demo
from app.config import settings
from app.database import get_db
from app.services.accounts import Principal

router = APIRouter()

RESET_CONFIRMATION = "RESET DEMO"

_DISABLED = (
    "Demo operations are disabled. They need CLINICAL_DEMO_MODE=true and a non-production "
    "APP_ENV (never in a real deployment)."
)


def _require_demo() -> None:
    if not settings.demo_operations_allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=_DISABLED)


class DemoResetRequest(BaseModel):
    confirm: str = Field(..., description=f"Must be exactly '{RESET_CONFIRMATION}'.")


@router.get("/clinical-demo/status")
async def get_demo_status():
    """Whether this server is in demo mode, what is simulated, and the scenario scripts."""
    return demo_status()


@router.post("/clinical-demo/seed")
async def seed_clinical_demo(admin: str = Depends(require_governance_admin), db: AsyncSession = Depends(get_db)):
    """Creates (or re-issues credentials for) the demo reviewers, demo institution and
    playbook, and two demo safety rules. Disabled unless demo operations are allowed."""
    _require_demo()
    return await seed_demo(db)


@router.post("/clinical-demo/reset")
async def reset_clinical_demo(
    body: DemoResetRequest,
    admin: str = Depends(require_governance_admin),
    db: AsyncSession = Depends(get_db),
):
    """Removes demo cases (cases holding a committed synthetic demo document), restores
    the demo safety rules to ACTIVE and rotates the demo credentials. Non-demo cases are
    never touched. Returns the fresh one-time credentials."""
    _require_demo()
    if body.confirm != RESET_CONFIRMATION:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Type '{RESET_CONFIRMATION}' to confirm the demo reset.",
        )
    try:
        return await reset_demo(db)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))


@router.post("/clinical-demo/scenarios/{scenario_id}")
async def load_clinical_demo_scenario(
    scenario_id: Literal["A", "B", "C", "D", "E", "a", "b", "c", "d", "e"],
    admin: str = Depends(require_governance_admin),
    principal: Principal = Depends(require_principal),
    db: AsyncSession = Depends(get_db),
):
    """Starts a scenario: a fresh consented case, owned by the signed-in account, whose
    synthetic documents have been run through the real upload pipeline."""
    _require_demo()
    try:
        return await load_scenario(db, scenario_id, owner_user_id=principal.user.id)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
