"""Shared types for Kadi entity resolution."""

from typing import Literal, Optional

from pydantic import BaseModel, Field

SignalName = Literal["lexical", "phonetic", "semantic"]

# AVAILABLE      — the signal was computed and `score` holds its value.
# UNAVAILABLE    — the signal could apply but could not be computed (e.g. semantic matching
#                  disabled, or the model failed to load). It must not count as evidence
#                  either way.
# NOT_APPLICABLE — the signal does not apply to this pair (e.g. no phonetic key can be
#                  built from a purely numeric name).
SignalStatus = Literal["AVAILABLE", "UNAVAILABLE", "NOT_APPLICABLE"]


class SignalScore(BaseModel):
    """One similarity signal for a mention/candidate pair."""

    signal: SignalName
    status: SignalStatus
    score: Optional[float] = Field(None, ge=0.0, le=1.0)
    detail: str = ""
