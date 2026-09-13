"""
SchemeSetu Package.

Government scheme eligibility verification.
"""

from .agent import check_eligibility, EligibilityRequest, SchemeResult
from .embeddings import OfflineEmbedder
from .reasoning_agent import reason_about_eligibility, EligibilityReasoning, ReasoningStep
from .trend_estimator import project_future_eligibility, EligibilityTrendResult, IncomeDataPoint
from .transition_adviser import advise_transition, TransitionAdvice

__all__ = [
    "check_eligibility",
    "EligibilityRequest",
    "SchemeResult",
    "OfflineEmbedder",
    "reason_about_eligibility",
    "EligibilityReasoning",
    "ReasoningStep",
    "project_future_eligibility",
    "EligibilityTrendResult",
    "IncomeDataPoint",
    "advise_transition",
    "TransitionAdvice",
]

