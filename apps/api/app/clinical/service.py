"""Clinical review service facade (ADR-011).

The implementation is split by actor and lifecycle (restructuring, 2026-10):
``case_reviews`` (case holder: request, assign, cancel, read), ``reviewer_reviews``
(reviewer: queue, accept/decline, evidence), ``statements`` (statement lifecycle),
``facts`` (fact confirmations), with shared helpers in ``review_common``. Existing
``from app.clinical import service`` / ``app.clinical.service.X`` callers keep working.

Authorization is object-level at every step, never inferred from an id:
- case-holder operations load the review by (case_id, review_id) after the case token
  was verified, so a review id from another case is simply "not found";
- reviewer operations require review.assigned_reviewer_id == this reviewer, the review
  in an accessible state, and the case still existing with consent;
- statement operations additionally require statement.reviewer_id == this reviewer.
"Not yours" is reported as 404 so ids cannot be probed; "yours, wrong state" is 409."""

from app.clinical.review_common import (  # noqa: F401
    NOT_FOUND,
    _lifecycle_http,
    _new_id,
)
from app.clinical.case_reviews import (  # noqa: F401
    assign_review,
    cancel_review,
    create_review,
    current_statements_for_case,
    facts_for_review,
    get_case_review,
    list_case_reviews,
    statements_for_review,
)
from app.clinical.reviewer_reviews import (  # noqa: F401
    EVIDENCE_STATES,
    REVIEWER_VISIBLE_STATES,
    _event,
    accept_review,
    decline_review,
    evidence_for_reviewer,
    reviewer_queue,
    reviewer_review,
)
from app.clinical.statements import (  # noqa: F401
    _content,
    _selected_evidence,
    _statement_for,
    create_statement,
    finalize_statement,
    return_to_draft,
    revise_statement,
    submit_statement,
    update_statement,
    withdraw_statement,
)
from app.clinical.facts import (  # noqa: F401
    decide_fact,
    latest_fact_decisions,
)
