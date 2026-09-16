"""
Cross-Module Consent Enforcement.

ADR-003 and the README state that cross-module data sharing through Kadi requires an
explicit per-case patient opt-in. That promise was previously decorative:
``KadiCase.consent_opt_in`` was written at case creation and never read by anything.

Enforcement reads the **persisted** case row, never a per-request field, so a client
cannot grant itself access by sending ``consent_opt_in: true`` on the module call. The
only way to set it is at case creation, which is the patient's own action.

Consent is a DIFFERENT concern from authorization (app.case_auth, ADR-009): consent gates
whether a case's context may be shared *across modules*; authorization gates whether the
caller may reach the case's data *at all*. A route's dependency order is always
``case: KadiCase = Depends(require_case_access)`` first, then ``require_case_consent(case)``
— a caller must hold the case's access token before the code ever checks what that case
consented to share. ``require_case_consent`` therefore takes an already-loaded
``KadiCase`` rather than re-querying by id; the existence check happened in
``require_case_access``.

Modules that consume Kadi case context (BillNyay, DaaviSetu; DawaCheck's
``GET /cases/{case_id}/benchmark``; SchemeSetu's ``POST /cases/{case_id}/eligibility``)
must call ``require_case_consent``. A module route that takes all its input from the
request body and reads no case context (SchemeSetu's ``POST /eligibility``; DawaCheck's
``POST /benchmark`` and ``POST /translate-instructions``; BillNyay's
``POST /outcome-estimate``) is out of scope by design — consent enforcement is a
per-route decision based on whether that route reads case entities, not a per-module one.

Phase 3 routes:

- Consent-gated: Kadi's ``GET /cases/{case_id}/insights`` (other modules' analyses of the
  case) and ``POST /cases/{case_id}/abdm/import`` (pulled medical history enters the shared
  context only for an opted-in case); SchemeSetu's ``PUT/GET/DELETE
  /cases/{case_id}/income-profile`` (nothing is stored without consent).
- Not gated, like ``GET /kadi/cases/{case_id}``: Kadi's own view of its case —
  ``/cases/{case_id}/resolutions`` (+ feedback) and ``/cases/{case_id}/graph``.
- Auto-triggers (app.auto_triggers) re-read the stored consent at run time and run nothing
  for a case without it.
"""

import logging

from fastapi import HTTPException, status

from app.models import KadiCase

logger = logging.getLogger("arogyarakshak.api.consent")

CONSENT_REQUIRED_DETAIL = (
    "Cross-module analysis requires patient consent for this case. "
    "The case was created without consent_opt_in, so its extracted context cannot be "
    "shared with other modules. Create a new case with consent_opt_in=true to proceed."
)


def require_case_consent(case: KadiCase) -> KadiCase:
    """Enforces cross-module sharing consent on an already-loaded, already-authorized case.

    Raises 403 when consent was not granted. Returns the case unchanged so call sites can
    chain it inline: ``case = require_case_consent(case)``.
    """
    if not case.consent_opt_in:
        logger.info("Blocked cross-module access to case %s: consent not granted.", case.id)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=CONSENT_REQUIRED_DETAIL
        )

    return case
