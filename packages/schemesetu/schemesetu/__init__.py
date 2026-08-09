"""
SchemeSetu Package.

Government scheme eligibility verification.
"""

from .agent import check_eligibility, EligibilityRequest, SchemeResult

__all__ = [
    "check_eligibility",
    "EligibilityRequest",
    "SchemeResult",
]
