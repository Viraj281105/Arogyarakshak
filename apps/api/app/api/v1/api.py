"""
Version 1 Router Aggregation.

Combines all sub-routers under /api/v1 prefix.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import kadi, billnyay, schemesetu, dawacheck, daavisetu

api_router = APIRouter()

api_router.include_router(kadi.router, prefix="/kadi", tags=["Kadi (Shared Layer)"])
api_router.include_router(billnyay.router, prefix="/billnyay", tags=["BillNyay (Bill Audit)"])
api_router.include_router(schemesetu.router, prefix="/schemesetu", tags=["SchemeSetu (Eligibilities)"])
api_router.include_router(dawacheck.router, prefix="/dawacheck", tags=["DawaCheck (Medicine Pricing)"])
api_router.include_router(daavisetu.router, prefix="/daavisetu", tags=["DaaviSetu (Claim Forms)"])
