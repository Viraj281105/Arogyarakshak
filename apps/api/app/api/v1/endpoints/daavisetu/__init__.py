"""
DaaviSetu API Endpoints.

Claim and pre-authorisation document generation (``claims``) and institution playbooks with
pre-authorisation readiness (``readiness``, ADR-011). This package composes their routers.
"""

from fastapi import APIRouter

from app.api.v1.endpoints.daavisetu import claims, readiness
from app.services.daavisetu_claims import (  # noqa: F401 — re-exported for existing importers
    _claim_data_from_record,
    claim_data_from_record,
)

router = APIRouter()
for _group in (claims, readiness):
    router.include_router(_group.router)
