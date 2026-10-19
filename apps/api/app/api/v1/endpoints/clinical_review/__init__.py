"""
Kadi — Clinical Review endpoints (ADR-011). Mounted under /api/v1/kadi.

Three audiences, three credentials, one module each:
- operator / registry (``registry``): X-Governance-Admin-Key for board seating and
  verification attempts; reviewer self-registration and directory;
- case holder (``case_holder``): X-Case-Access-Token, routes under /cases/{case_id}/...;
- reviewer (``reviewer``): X-Reviewer-Token, routes under /clinical-reviews/... and
  /clinical-reviewers/me.

AI never holds a reviewer credential, so no model output can create, finalize or sign a
statement: every write that carries professional attribution requires one.
"""

from fastapi import APIRouter

from app.api.v1.endpoints.clinical_review import case_holder, registry, reviewer

router = APIRouter()
for _group in (registry, case_holder, reviewer):
    router.include_router(_group.router)
