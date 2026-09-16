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

from fastapi import Depends, Header, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import KadiCase

logger = logging.getLogger("arogyarakshak.api.case_auth")

CASE_ACCESS_TOKEN_HEADER = "X-Case-Access-Token"

# SEC-07: a query-string token is only safe for read-only requests (it can still land in
# server access logs / browser history, which is why it is not the default — see
# require_case_access's docstring). Accepting it for a state-changing verb as well used to
# let anyone who obtained a token via a log/history/referrer leak use it to POST/PUT/DELETE,
# not just read — the exact "weaker than a header" trade-off this was meant to be limited
# to. Only GET (and HEAD, which FastAPI treats as GET) may use it.
_QUERY_TOKEN_SAFE_METHODS = {"GET", "HEAD"}

MISSING_TOKEN_DETAIL = (
    "This request requires the case's access token, returned once when the case was "
    f"created. Send it as the '{CASE_ACCESS_TOKEN_HEADER}' header. A case id alone is "
    "not sufficient authorization (ADR-009)."
)
INVALID_TOKEN_DETAIL = "The provided case access token is invalid for this case."
QUERY_TOKEN_NOT_ALLOWED_DETAIL = (
    "A query-string access_token cannot authorize this request. Send the token via the "
    f"'{CASE_ACCESS_TOKEN_HEADER}' header instead — query-string tokens are accepted only "
    "for safe, read-only requests (e.g. GET .../stream, GET .../claim/pdf)."
)


def generate_case_access_token() -> "tuple[str, str]":
    """Returns (plaintext_token, sha256_hash). Only the hash is ever persisted."""
    token = secrets.token_urlsafe(32)
    return token, hash_case_access_token(token)


def hash_case_access_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


async def require_case_access(
    request: Request,
    case_id: str,
    db: AsyncSession = Depends(get_db),
    x_case_access_token: Optional[str] = Header(None, alias=CASE_ACCESS_TOKEN_HEADER),
    access_token_qs: Optional[str] = Query(None, alias="access_token"),
) -> KadiCase:
    """FastAPI dependency: loads the case and enforces its access token.

    Accepts the token via the ``X-Case-Access-Token`` header (every route should use
    this) or, for safe read-only requests ONLY (GET/HEAD — e.g. GET
    /cases/{case_id}/stream, whose browser-native EventSource cannot set custom headers,
    or a direct-download GET like DaaviSetu's PDF), an ``?access_token=`` query
    parameter. A query-string token is weaker than a header (it can land in server access
    logs and browser history), which is why it is not the default and — SEC-07 — why it
    is REJECTED outright on any state-changing verb (POST/PUT/PATCH/DELETE): a token that
    leaked via a log/history/referrer must not be usable to mutate or delete a case, only
    to read it. This is a trade-off documented in ADR-009, not hidden.

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

    if access_token_qs and request.method.upper() not in _QUERY_TOKEN_SAFE_METHODS:
        logger.info(
            "Denied access to case %s: query-string token rejected for %s (state-changing).",
            case_id, request.method,
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=QUERY_TOKEN_NOT_ALLOWED_DETAIL)

    presented_token = x_case_access_token or (
        access_token_qs if request.method.upper() in _QUERY_TOKEN_SAFE_METHODS else None
    )
    if not presented_token:
        logger.info("Denied access to case %s: no access token presented.", case_id)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=MISSING_TOKEN_DETAIL)

    stored_hash = case.access_token_hash or ""
    presented_hash = hash_case_access_token(presented_token)
    if not stored_hash or not hmac.compare_digest(presented_hash, stored_hash):
        logger.info("Denied access to case %s: access token did not match.", case_id)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=INVALID_TOKEN_DETAIL)

    return case
