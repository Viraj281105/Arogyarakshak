"""
Version 1 Router Aggregation.

Combines all sub-routers under /api/v1 prefix.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    billnyay,
    bimanyay,
    clinical_demo,
    clinical_review,
    clinical_safety,
    clinical_transcription,
    daavisetu,
    dawacheck,
    kadi,
    schemesetu,
)

api_router = APIRouter()

api_router.include_router(kadi.router, prefix="/kadi", tags=["Kadi (Shared Layer)"])
# ADR-011: human clinical review, safety governance and OCR resolution are Kadi
# capabilities (cross-module case context), so they share the /kadi prefix.
api_router.include_router(clinical_review.router, prefix="/kadi", tags=["Kadi — Clinical Review"])
api_router.include_router(clinical_safety.router, prefix="/kadi", tags=["Kadi — Clinical Safety Governance"])
api_router.include_router(clinical_transcription.router, prefix="/kadi", tags=["Kadi — Human OCR Resolution"])
api_router.include_router(clinical_demo.router, prefix="/kadi", tags=["Kadi — Clinical Demo Fixtures"])
api_router.include_router(billnyay.router, prefix="/billnyay", tags=["BillNyay (Bill Audit)"])
api_router.include_router(schemesetu.router, prefix="/schemesetu", tags=["SchemeSetu (Eligibilities)"])
api_router.include_router(dawacheck.router, prefix="/dawacheck", tags=["DawaCheck (Medicine Pricing)"])
api_router.include_router(daavisetu.router, prefix="/daavisetu", tags=["DaaviSetu (Claim Forms)"])
api_router.include_router(bimanyay.router, prefix="/bimanyay", tags=["BimaNyay (Insurance Denials)"])

