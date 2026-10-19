"""Helpers shared by the clinical review modules (ADR-011)."""

import uuid

from fastapi import HTTPException, status

from kadi.clinical_review.lifecycle import (
    LifecycleError,
)



NOT_FOUND = "Clinical review not found."


def _lifecycle_http(e: LifecycleError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(e))


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"
