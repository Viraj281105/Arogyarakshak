"""Request schemas for the clinical review routes (ADR-011)."""

from typing import List, Literal, Optional

from pydantic import BaseModel, Field

from kadi.clinical_review import (
    ReviewerCategory,
    ReviewTrigger,
    SourceModule,
)




# --- Schemas ------------------------------------------------------------------

class ReviewerRegistration(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    category: ReviewerCategory
    designation: Optional[str] = Field(None, max_length=120)
    specialty: Optional[str] = Field(None, max_length=120)
    registration_number: Optional[str] = Field(None, max_length=60)
    registration_authority: Optional[str] = Field(None, max_length=160)
    affiliation: Optional[str] = Field(None, max_length=200)
    standing_disclosures: Optional[str] = Field(None, max_length=1000)
    reviewer_notes: Optional[str] = Field(None, max_length=1000)


class ReviewCreate(BaseModel):
    source_module: SourceModule
    clinical_question: Optional[str] = Field(None, max_length=1000)
    evidence_scope: Optional[List[str]] = None
    insurer_name: Optional[str] = Field(None, max_length=120)
    trigger: ReviewTrigger = ReviewTrigger.MANUAL
    trigger_ref: Optional[str] = Field(None, max_length=80)
    share_with_reviewer_consent: bool = False


class AssignRequest(BaseModel):
    reviewer_id: str = Field(..., max_length=40)


class AcceptRequest(BaseModel):
    coi_category: str
    coi_disclosure: Optional[str] = Field(None, max_length=1000)


class DeclineRequest(BaseModel):
    reason: Optional[str] = Field(None, max_length=500)


class StatementWrite(BaseModel):
    evidence_reviewed: List[str] = Field(..., max_length=60)
    reviewer_statement: str = Field(..., max_length=8000)
    limitations: str = Field(..., max_length=3000)


class ConfirmRequest(BaseModel):
    confirmation: bool = False
    confirmation_text: Optional[str] = Field(None, max_length=300)


class WithdrawRequest(BaseModel):
    reason: str = Field(..., max_length=500)


class FactDecisionRequest(ConfirmRequest):
    decision: Literal["CONFIRMED", "REJECTED", "CANNOT_DETERMINE"]
    note: Optional[str] = Field(None, max_length=1000)


class BoardSeatRequest(BaseModel):
    seated: bool


class VerificationRequest(BaseModel):
    mode: Literal["external", "demo"]
