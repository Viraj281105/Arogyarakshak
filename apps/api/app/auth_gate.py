"""Mandatory sign-in for the whole v1 API (ADR-029).

One router-level dependency, deny by default: a request is let through only when

1. it targets one of the few routes that must work signed out (``PUBLIC_API_PATHS``), or
2. its route is guarded by a staff credential (reviewer, institution or operator key). That
   dependency then authenticates the request itself, and refuses it without the credential, or
3. it carries a live account session.

A new route is therefore protected without anyone remembering to protect it. Ownership of a
particular case is a second, separate check (``app.case_auth``).
"""

from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.dependencies.models import Dependant

from app.account_auth import SIGN_IN_REQUIRED_DETAIL, get_optional_principal
from app.clinical.auth import require_governance_admin, require_institution, require_reviewer
from app.services.accounts import Principal

API_PREFIX = "/api/v1"

# Everything a person needs before they can have a session. Nothing here reads patient data.
PUBLIC_API_PATHS = frozenset(
    f"{API_PREFIX}/kadi/auth/{name}"
    for name in (
        "config",
        "register",
        "login",
        "verification/request",
        "verification/confirm",
        "password-reset/request",
        "password-reset/confirm",
    )
)

# Dependencies that REQUIRE a staff credential (an optional credential does not count).
STAFF_CREDENTIAL_DEPENDENCIES = (require_reviewer, require_institution, require_governance_admin)


def uses_staff_credential(dependant: Optional[Dependant]) -> bool:
    """True when the route's dependency tree contains a required staff credential."""
    if dependant is None:
        return False
    for sub in dependant.dependencies:
        if sub.call in STAFF_CREDENTIAL_DEPENDENCIES or uses_staff_credential(sub):
            return True
    return False


async def require_signed_in(
    request: Request, principal: Optional[Principal] = Depends(get_optional_principal)
) -> None:
    if principal is not None or request.url.path in PUBLIC_API_PATHS:
        return
    if uses_staff_credential(getattr(request.scope.get("route"), "dependant", None)):
        return
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=SIGN_IN_REQUIRED_DETAIL)
