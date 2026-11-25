"""Account session credentials over HTTP (ADR-026 section 5).

Web: an httpOnly, Secure, SameSite=Strict cookie. Mobile: ``Authorization: Bearer``.
A session is bound to the transport it was issued for, so a cookie token cannot be
replayed as a bearer token (which would skip the Origin check) and vice versa.

CSRF: a state-changing request authenticated by the cookie must carry an ``Origin`` that
is this API's own origin or a trusted one (``AUTH_TRUSTED_ORIGINS``, default the explicit
``CORS_ORIGINS``). SameSite=Strict already blocks cross-site cookies; this is the second,
independent layer.

An unknown, expired or revoked credential is treated as no credential, so a stale cookie
never breaks the public account routes. Every other route then answers 401 (ADR-029,
app.auth_gate).
"""

from dataclasses import dataclass
from typing import Optional, Set

from fastapi import Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.services import accounts
from app.services.accounts import Principal

UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

SIGN_IN_REQUIRED_DETAIL = "Sign in to continue."
UNTRUSTED_ORIGIN_DETAIL = (
    "This request did not come from a trusted origin. Signed-in requests that change data "
    "must be sent by the ArogyaRakshak web app (ADR-026)."
)


def session_cookie_name() -> str:
    # The __Host- prefix makes the browser refuse the cookie unless it is Secure, has
    # Path=/ and no Domain, so a sibling subdomain cannot plant or overwrite it.
    return "__Host-arogya_session" if settings.session_cookie_secure else "arogya_session"


def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=session_cookie_name(),
        value=token,
        max_age=settings.session_lifetime_hours * 3600,
        path="/",
        secure=settings.session_cookie_secure,
        httponly=True,
        samesite="strict",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(
        key=session_cookie_name(),
        path="/",
        secure=settings.session_cookie_secure,
        httponly=True,
        samesite="strict",
    )


def _trusted_origins(request: Request) -> Set[str]:
    """AUTH_TRUSTED_ORIGINS, else the explicit CORS_ORIGINS. Outside production the API's
    own origin is added for convenience; under APP_ENV=production it is NOT, because it is
    derived from the request's Host header (review L8). Production already refuses a
    wildcard CORS_ORIGINS, so this set is always an operator-written list there."""
    configured = settings.auth_trusted_origins or settings.cors_origins
    origins = {o.strip().rstrip("/") for o in configured.split(",") if o.strip() and o.strip() != "*"}
    if not settings.is_production:
        origins.add(f"{request.url.scheme}://{request.url.netloc}")
    return origins


def origin_is_trusted(request: Request) -> bool:
    origin = request.headers.get("origin")
    return bool(origin) and origin.rstrip("/") in _trusted_origins(request)


def reject_untrusted_origin(request: Request) -> None:
    """For login and registration: a browser request (it carries Origin) must come from a
    trusted origin (login CSRF). Non-browser clients send no Origin and are unaffected."""
    if request.headers.get("origin") and not origin_is_trusted(request):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=UNTRUSTED_ORIGIN_DETAIL)


@dataclass(frozen=True)
class PresentedCredential:
    token: str
    transport: str


def presented_credential(request: Request) -> Optional[PresentedCredential]:
    header = request.headers.get("authorization") or ""
    scheme, _, value = header.partition(" ")
    if scheme.lower() == "bearer" and value.strip():
        return PresentedCredential(value.strip(), accounts.TRANSPORT_BEARER)
    cookie = request.cookies.get(session_cookie_name())
    if cookie:
        return PresentedCredential(cookie, accounts.TRANSPORT_COOKIE)
    return None


async def get_optional_principal(request: Request, db: AsyncSession = Depends(get_db)) -> Optional[Principal]:
    """The live session behind the presented credential, or None. The Origin check runs
    only when a cookie maps to a live cookie session (review L7): a garbage, expired or
    planted cookie is simply ignored, so it can never break a guest write."""
    credential = presented_credential(request)
    if credential is None:
        return None
    principal = await accounts.resolve_session_token(db, credential.token)
    if principal is None or principal.session.transport != credential.transport:
        return None
    if (
        credential.transport == accounts.TRANSPORT_COOKIE
        and request.method.upper() in UNSAFE_METHODS
        and not origin_is_trusted(request)
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=UNTRUSTED_ORIGIN_DETAIL)
    return principal


async def require_principal(principal: Optional[Principal] = Depends(get_optional_principal)) -> Principal:
    if principal is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=SIGN_IN_REQUIRED_DETAIL)
    return principal
