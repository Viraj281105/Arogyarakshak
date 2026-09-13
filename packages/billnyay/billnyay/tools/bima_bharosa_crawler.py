"""
BillNyay — Bima Bharosa Portal Registration-Status Checker (#67).

The issue's own objective calls for a "mock registration status" check, and this ships
a mock-first implementation rather than a real headless-browser scraper against
IRDAI's live Bima Bharosa portal. Automating logins or form submissions against a real
government grievance portal is a materially different kind of system than anything
else in this codebase attempts — it is subject to that portal's own terms of use and
anti-automation measures, and there is no authorization on file for ArogyaRakshak to
do it. What ships here is a deterministic mock satisfying the same interface a real
checker would, so BillNyay's grievance flow can display and test a "registration
status" step without either false-claiming a live portal check happened or building
unauthorized site automation.

If a genuine integration is ever wanted, it needs an explicit decision (and IRDAI/
portal authorization) to relax this — not a change made unilaterally here.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

BIMA_BHAROSA_PORTAL_URL = "https://bimabharosa.irdai.gov.in/RegisterNewGrievance"


class RegistrationStatusResult(BaseModel):
    complaint_reference: str
    is_registered: bool
    checked_at: str
    source: str = Field("mock", description='Always "mock" — no live portal request is made.')
    note: str


def check_registration_status_mock(complaint_reference: Optional[str]) -> RegistrationStatusResult:
    """Deterministically simulates a Bima Bharosa registration-status check.

    Always reports `source="mock"` so a caller can never mistake this for a real
    portal query result.
    """
    checked_at = datetime.utcnow().isoformat()

    if not complaint_reference or not complaint_reference.strip():
        return RegistrationStatusResult(
            complaint_reference=complaint_reference or "",
            is_registered=False,
            checked_at=checked_at,
            source="mock",
            note="No complaint reference was supplied; there is nothing to simulate a check for.",
        )

    return RegistrationStatusResult(
        complaint_reference=complaint_reference.strip(),
        is_registered=True,
        checked_at=checked_at,
        source="mock",
        note=(
            "This is a MOCK result. ArogyaRakshak does not perform automated queries "
            f"against the live Bima Bharosa portal. Verify the real status directly at "
            f"{BIMA_BHAROSA_PORTAL_URL}."
        ),
    )
