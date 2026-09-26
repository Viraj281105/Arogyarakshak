"""
Credentials for the clinical-review layer (ADR-011).

There is still no login system (ADR-008/009). Reviewers and institutions each receive a
high-entropy bearer credential exactly once, at registration; only its SHA-256 hash is
stored — the same model the per-case access token uses. Unlike case tokens, these are
accepted ONLY as headers, never in a query string, because they authorise writes that
carry professional attribution.

Delegation, not browsing: a reviewer credential grants nothing on its own. A reviewer
reaches case data only through a review or transcription task that the case's own token
holder explicitly assigned to them, and only that task's frozen evidence.
"""

import hashlib
import hmac
import logging
import secrets
from typing import Optional

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models import DaaviSetuInstitution, KadiClinicalReviewer

logger = logging.getLogger("arogyarakshak.api.clinical.auth")

REVIEWER_TOKEN_HEADER = "X-Reviewer-Token"
INSTITUTION_TOKEN_HEADER = "X-Institution-Token"
GOVERNANCE_ADMIN_HEADER = "X-Governance-Admin-Key"


def generate_credential() -> "tuple[str, str]":
    token = secrets.token_urlsafe(32)
    return token, hash_credential(token)


def hash_credential(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def reviewer_available(reviewer: Optional[KadiClinicalReviewer]) -> bool:
    """Active, and not a demo fixture outside demo mode (demo credentials must stop
    working the moment CLINICAL_DEMO_MODE is turned off)."""
    return bool(reviewer and reviewer.is_active and (settings.clinical_demo_mode or not reviewer.is_demo))


def listed_in_directory(reviewer: KadiClinicalReviewer) -> bool:
    """Only independently verified reviewers are listed publicly. Anyone can self-register
    under any name, so a self-declared "doctor" is never shown to patients as a choice;
    they are assigned only by the reviewer ID they give the patient themselves."""
    if not reviewer_available(reviewer):
        return False
    if reviewer.verification_status == "EXTERNALLY_VERIFIED":
        return True
    return settings.clinical_demo_mode and reviewer.is_demo


async def require_reviewer(
    db: AsyncSession = Depends(get_db),
    x_reviewer_token: Optional[str] = Header(None, alias=REVIEWER_TOKEN_HEADER),
) -> KadiClinicalReviewer:
    if not x_reviewer_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"This request requires your reviewer credential in the '{REVIEWER_TOKEN_HEADER}' header.",
        )
    result = await db.execute(
        select(KadiClinicalReviewer).where(
            KadiClinicalReviewer.credential_hash == hash_credential(x_reviewer_token)
        )
    )
    reviewer = result.scalar_one_or_none()
    if not reviewer_available(reviewer):
        logger.info("Rejected a reviewer credential that matched no available reviewer.")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid reviewer credential.")
    return reviewer


async def require_board_member(
    reviewer: KadiClinicalReviewer = Depends(require_reviewer),
) -> KadiClinicalReviewer:
    if not reviewer.is_safety_board_member or reviewer.category != "DOCTOR":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only doctors seated on the clinical safety review board can manage safety rules.",
        )
    return reviewer


async def resolve_institution(
    db: AsyncSession, token: Optional[str]
) -> Optional[DaaviSetuInstitution]:
    if not token:
        return None
    result = await db.execute(
        select(DaaviSetuInstitution).where(DaaviSetuInstitution.credential_hash == hash_credential(token))
    )
    institution = result.scalar_one_or_none()
    if institution is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid institution credential.")
    return institution


async def require_institution(
    db: AsyncSession = Depends(get_db),
    x_institution_token: Optional[str] = Header(None, alias=INSTITUTION_TOKEN_HEADER),
) -> DaaviSetuInstitution:
    if not x_institution_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"This request requires the institution credential in the '{INSTITUTION_TOKEN_HEADER}' header.",
        )
    return await resolve_institution(db, x_institution_token)


def require_governance_admin(
    x_governance_admin_key: Optional[str] = Header(None, alias=GOVERNANCE_ADMIN_HEADER),
) -> str:
    configured = settings.clinical_governance_admin_key
    if not configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Clinical governance administration is disabled: CLINICAL_GOVERNANCE_ADMIN_KEY "
                "is not configured on this server."
            ),
        )
    if not x_governance_admin_key or not hmac.compare_digest(
        hash_credential(x_governance_admin_key), hash_credential(configured)
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid governance admin key.")
    return "governance-admin"
