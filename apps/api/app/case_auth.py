"""
Case authorization (ADR-029, building on ADR-009 and ADR-026).

Every case-scoped route needs an account session, and only the account that owns the case may
use it. ``authorize_case`` holds the whole rule so every route that loads a case (including
BimaNyay's optional case link) applies it.

Guest cases are no longer reachable. A case created before sign-in became mandatory still
carries the hash of its one-time token; the only thing that token can still do is move the
case into the caller's account (``require_claimable_case``, used by the claim route).
"""

import hashlib
import hmac
import logging
import secrets
from typing import Optional

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.account_auth import get_optional_principal
from app.database import get_db
from app.models import KadiCase
from app.services.accounts import Principal

logger = logging.getLogger("arogyarakshak.api.case_auth")

CASE_ACCESS_TOKEN_HEADER = "X-Case-Access-Token"

SIGN_IN_FOR_CASE_DETAIL = "Sign in to open this case."
MISSING_TOKEN_DETAIL = (
    "Moving a case into your account needs that case's access token, sent as the "
    f"'{CASE_ACCESS_TOKEN_HEADER}' header (ADR-009)."
)
INVALID_TOKEN_DETAIL = "The provided case access token is invalid for this case."
UNCLAIMED_CASE_DETAIL = (
    "This case was started without an account. Move it into your account to open it (ADR-029)."
)
OTHER_ACCOUNT_DETAIL = "This case is not available to the signed-in account."


def generate_case_access_token() -> "tuple[str, str]":
    """Returns (plaintext_token, sha256_hash). Only the hash is ever persisted."""
    token = secrets.token_urlsafe(32)
    return token, hash_case_access_token(token)


def hash_case_access_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


async def _load_case(db: AsyncSession, case_id: str) -> KadiCase:
    case = (await db.execute(select(KadiCase).where(KadiCase.id == case_id))).scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    return case


async def require_case_access(
    case_id: str,
    db: AsyncSession = Depends(get_db),
    principal: Optional[Principal] = Depends(get_optional_principal),
) -> KadiCase:
    """FastAPI dependency: loads the case and authorises the caller (``authorize_case``).

    Order matches app.consent.require_case_consent (404 before 403): the case id is a 64-bit
    random value, so its existence is not worth hiding from a signed-in caller. A signed-out
    caller is refused before the lookup and learns nothing."""
    if principal is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=SIGN_IN_FOR_CASE_DETAIL)
    return authorize_case(await _load_case(db, case_id), principal=principal)


def authorize_case(case: KadiCase, *, principal: Optional[Principal]) -> KadiCase:
    """The single access rule for a loaded case: the owner's session, nothing else."""
    if principal is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=SIGN_IN_FOR_CASE_DETAIL)
    if not case.owner_user_id:
        logger.info("Denied access to case %s: it is not owned by any account.", case.id)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=UNCLAIMED_CASE_DETAIL)
    if not hmac.compare_digest(principal.user.id, case.owner_user_id):
        logger.info("Denied access to case %s: signed-in account is not its owner.", case.id)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=OTHER_ACCOUNT_DETAIL)
    return case


async def require_claimable_case(
    case_id: str,
    db: AsyncSession = Depends(get_db),
    x_case_access_token: Optional[str] = Header(None, alias=CASE_ACCESS_TOKEN_HEADER),
    principal: Optional[Principal] = Depends(get_optional_principal),
) -> KadiCase:
    """For the claim route only: a case the caller already owns, or an unowned case whose
    access token the caller holds. Constant-time comparison of the token hash."""
    if principal is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=SIGN_IN_FOR_CASE_DETAIL)
    case = await _load_case(db, case_id)
    if case.owner_user_id:
        return authorize_case(case, principal=principal)
    if not x_case_access_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=MISSING_TOKEN_DETAIL)
    stored_hash = case.access_token_hash or ""
    if not stored_hash or not hmac.compare_digest(hash_case_access_token(x_case_access_token), stored_hash):
        logger.info("Denied claim of case %s: access token did not match.", case.id)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=INVALID_TOKEN_DETAIL)
    return case
