"""
BillNyay — Self-Correcting Appeal Drafting Loop (#68).

Re-drafts the appeal letter when the Judge Agent flags it `needs_revision`, feeding the
Judge's own issues back to the Barrister Agent as critique (the Barrister already
accepts a `critique` parameter for exactly this), up to a bounded number of attempts so
a persistently low-scoring draft cannot loop forever.
"""

import logging
from typing import Any, List, Optional

from pydantic import BaseModel

from billnyay.agents.barrister import run_barrister_agent
from billnyay.agents.judge import run_judge_agent, JudgeScorecard

logger = logging.getLogger("BillNyay.FeedbackLoop")

DEFAULT_MAX_ATTEMPTS = 2


class RevisionAttempt(BaseModel):
    attempt: int
    prior_score: int
    critique: str


class DraftingResult(BaseModel):
    appeal_letter: str
    scorecard: JudgeScorecard
    revision_count: int
    revision_history: List[RevisionAttempt]


def _critique_from_scorecard(scorecard: JudgeScorecard) -> str:
    if not scorecard.issues:
        return (
            f"Overall score {scorecard.overall_score} is below the approval threshold; "
            "strengthen factual grounding, citation consistency, and regulatory argument."
        )
    return "; ".join(
        issue.description + (f" — fix: {issue.suggested_fix}" if issue.suggested_fix else "")
        for issue in scorecard.issues
    )


def draft_with_self_correction(
    client,
    denial_details: Any = None,
    clinical_evidence: Any = None,
    regulatory_evidence: Any = None,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
) -> Optional[DraftingResult]:
    """Drafts an appeal letter, automatically revising it while the Judge reports
    `needs_revision`, up to `max_attempts` additional drafts.

    Returns None only when the Barrister cannot produce an *initial* draft at all — a
    failed revision attempt keeps the last good draft rather than discarding it.
    """
    appeal_letter = run_barrister_agent(
        client,
        denial_details=denial_details,
        clinical_evidence=clinical_evidence,
        regulatory_evidence=regulatory_evidence,
    )
    if not appeal_letter:
        return None

    scorecard = run_judge_agent(
        appeal_letter=appeal_letter,
        denial_details=denial_details,
        clinical_evidence=clinical_evidence,
        regulatory_evidence=regulatory_evidence,
    )

    history: List[RevisionAttempt] = []
    attempts = 0
    while scorecard.status == "needs_revision" and attempts < max_attempts:
        critique = _critique_from_scorecard(scorecard)
        history.append(
            RevisionAttempt(attempt=attempts + 1, prior_score=scorecard.overall_score, critique=critique)
        )
        logger.info("[FeedbackLoop] Revision attempt %d — critique: %s", attempts + 1, critique)

        revised = run_barrister_agent(
            client,
            denial_details=denial_details,
            clinical_evidence=clinical_evidence,
            regulatory_evidence=regulatory_evidence,
            critique=critique,
        )
        attempts += 1
        if not revised:
            logger.warning(
                "[FeedbackLoop] Revision attempt %d produced no letter; keeping prior draft.", attempts
            )
            break

        appeal_letter = revised
        scorecard = run_judge_agent(
            appeal_letter=appeal_letter,
            denial_details=denial_details,
            clinical_evidence=clinical_evidence,
            regulatory_evidence=regulatory_evidence,
        )

    return DraftingResult(
        appeal_letter=appeal_letter,
        scorecard=scorecard,
        revision_count=attempts,
        revision_history=history,
    )
