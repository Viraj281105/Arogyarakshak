"""
Reviewer registration verification (ADR-011).

There is no integration with the National Medical Commission (NMC) Indian Medical
Register, any State Medical Council, or the Pharmacy Council of India in this build:
none of them publishes an API this project is authorised to call. So the only adapter
shipped here reports that plainly. A real adapter can be dropped in behind
`RegistryVerificationAdapter` later without touching callers; until then no code path
can produce EXTERNALLY_VERIFIED.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Protocol

from .types import VerificationStatus

EXTERNAL_VERIFICATION_UNAVAILABLE = "EXTERNAL_VERIFICATION_UNAVAILABLE"
DEMO_VERIFICATION_SOURCE = "ArogyaRakshak demo fixture — not a real registry check"


@dataclass(frozen=True)
class VerificationOutcome:
    # A VerificationStatus value when the adapter reached a verdict; otherwise
    # EXTERNAL_VERIFICATION_UNAVAILABLE and the reviewer's status must not change.
    outcome: str
    source: Optional[str]
    checked_at: datetime
    detail: str

    @property
    def changes_status(self) -> bool:
        return self.outcome == VerificationStatus.EXTERNALLY_VERIFIED.value


class RegistryVerificationAdapter(Protocol):
    def verify(
        self, *, registration_number: str, registration_authority: Optional[str], name: str
    ) -> VerificationOutcome: ...


class UnavailableRegistryAdapter:
    """The honest default: no registry integration exists."""

    def verify(
        self, *, registration_number: str, registration_authority: Optional[str], name: str
    ) -> VerificationOutcome:
        return VerificationOutcome(
            outcome=EXTERNAL_VERIFICATION_UNAVAILABLE,
            source=None,
            checked_at=datetime.utcnow(),
            detail=(
                "External verification unavailable: this deployment has no integration with "
                "the NMC Indian Medical Register, a State Medical Council or the Pharmacy "
                "Council of India. The reviewer's status was not changed."
            ),
        )


def initial_verification_status(registration_number: Optional[str]) -> str:
    """Self-registration can never produce more than SELF_DECLARED."""
    return (
        VerificationStatus.SELF_DECLARED.value
        if registration_number and registration_number.strip()
        else VerificationStatus.UNVERIFIED.value
    )
