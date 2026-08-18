"""
SchemeSetu Package.

Government scheme eligibility verification.
"""

from .agent import check_eligibility, EligibilityRequest, SchemeResult
from .embeddings import OfflineEmbedder

__all__ = [
    "check_eligibility",
    "EligibilityRequest",
    "SchemeResult",
    "OfflineEmbedder",
]

