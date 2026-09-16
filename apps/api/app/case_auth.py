"""
Per-Case Access Authorization (ADR-009).

Phase 4 raised case-id entropy to 64 bits and documented (ADR-008) that entropy alone is
not authorization — a case id circulating anywhere (a shared link, a browser history
entry, a referrer header, a leaked log line) was still sufficient to read and act on that
patient's data indefinitely. This module closes that gap with the smallest mechanism that
provides REAL authorization rather than more obscurity:

Every case gets a high-entropy access token at creation (`generate_case_access_token`),
returned to the caller exactly once, in the creation response. Only its SHA-256 hash is
persisted (`KadiCase.access_token_hash`). Every subsequent case-scoped request must
present that token via the `X-Case-Access-Token` header; `require_case_access` is the
FastAPI dependency every `/cases/{case_id}/...` route uses to enforce it.

This is deliberately NOT a user-account/login system — there is still no concept of a
"user" distinct from "whoever holds this case's token," so one browser tab cannot access
a case created in another tab/device without the token being carried over. That is an
intentional, disclosed scope boundary (see ADR-009), not an oversight: building real
accounts is a materially larger feature explicitly out of scope for this remediation pass.
"""

import hashlib
import hmac
import logging
import secrets
from typing import Optional

from fastapi import Depends, Header, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import KadiCase

logger = logging.getLogger("arogyarakshak.api.case_auth")

CASE_ACCESS_TOKEN_HEADER = "X-Case-Access-Token"

MISSING_TOKEN_DETAIL = (
    "This request requires the case's access token, returned once when the case was "
    f"created. Send it as the '{CASE_ACCESS_TOKEN_HEADER}' header. A case id alone is "
    "not sufficient authorization (ADR-009)."
)
INVALID_TOKEN_DETAIL = "The provided case access token is invalid for this case."


def generate_case_access_token() -> "tuple[str, str]":
    """Returns (plaintext_token, sha256_hash). Only the hash is ever persisted."""
    token = secrets.token_urlsafe(32)
    return token, hash_case_access_token(token)


def hash_case_access_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


async def require_case_access(
    case_id: str,
    db: AsyncSession = Depends(get_db),
    x_case_access_token: Optional[str] = Header(None, alias=CASE_ACCESS_TOKEN_HEADER),
    access_token_qs: Optional[str] = Query(None, alias="access_token"),
) -> KadiCase:
    """FastAPI dependency: loads the case and enforces its access token.

    Accepts the token via the ``X-Case-Access-Token`` header (every route should use
    this) or an ``?access_token=`` query parameter (fallback ONLY for
    GET /cases/{case_id}/stream — the browser's native EventSource cannot set custom
    headers, and that is the sole reason this fallback exists). A query-string token is
    weaker than a header (it can land in server access logs and browser history), which
    is why it is not the default and is documented as a trade-off in ADR-009, not hidden.

    Order matches the existing app.consent.require_case_consent convention (404 before
    401/403): existence is not itself a secret worth hiding behind a uniform error, since
    the case id is already a 64-bit random token an attacker would need to have guessed
    correctly to reach this check at all.

    Uses constant-time comparison (hmac.compare_digest) so response timing cannot be used
    to brute-force a token character-by-character.
    """
    result = await db.execute(select(KadiCase).where(KadiCase.id == case_id))
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    presented_token = x_case_access_token or access_token_qs
    if not presented_token:
        logger.info("Denied access to case %s: no access token presented.", case_id)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=MISSING_TOKEN_DETAIL)

    stored_hash = case.access_token_hash or ""
    presented_hash = hash_case_access_token(presented_token)
    if not stored_hash or not hmac.compare_digest(presented_hash, stored_hash):
        logger.info("Denied access to case %s: access token did not match.", case_id)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=INVALID_TOKEN_DETAIL)

    return case
