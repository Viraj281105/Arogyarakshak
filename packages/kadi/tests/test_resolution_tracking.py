"""ADR-031: only records that could be true are accepted."""

from datetime import date, timedelta

import pytest

from kadi.resolution_tracking import (
    ALLOWED_TRANSITIONS,
    ActionStatus as S,
    ImpossibleTransition,
    TrackingError,
    validate_event,
)

TODAY = date(2026, 11, 25)


def test_every_status_has_a_rule_and_no_status_claims_a_third_party_decision():
    assert set(ALLOWED_TRANSITIONS) == set(S)
    values = {s.value for s in S}
    assert not values & {"submitted", "accepted", "approved", "rejected"}


@pytest.mark.parametrize(
    "current,new",
    [
        (S.PLANNED, S.RESPONSE_RECEIVED),
        (S.PLANNED, S.RESOLVED),
        (S.DRAFT_PREPARED, S.RESOLVED),
        (S.DRAFT_PREPARED, S.AWAITING_RESPONSE),
        (S.WITHDRAWN, S.RESOLVED),
    ],
)
def test_nothing_is_resolved_or_answered_before_it_was_sent(current, new):
    with pytest.raises(ImpossibleTransition):
        validate_event(current, new, TODAY, TODAY)


@pytest.mark.parametrize("new", [S.SENT, S.RESPONSE_RECEIVED])
def test_real_world_events_need_a_date(new):
    current = S.PLANNED if new == S.SENT else S.SENT
    with pytest.raises(TrackingError, match="which day"):
        validate_event(current, new, None, TODAY)


def test_a_future_date_is_refused_but_a_time_zone_day_is_allowed():
    validate_event(S.PLANNED, S.SENT, TODAY + timedelta(days=1), TODAY)
    with pytest.raises(TrackingError, match="future"):
        validate_event(S.PLANNED, S.SENT, TODAY + timedelta(days=2), TODAY)


def test_a_response_cannot_predate_the_sending():
    history = [(S.SENT, TODAY - timedelta(days=3))]
    with pytest.raises(TrackingError, match="before"):
        validate_event(S.SENT, S.RESPONSE_RECEIVED, TODAY - timedelta(days=4), TODAY, history)
    validate_event(S.SENT, S.RESPONSE_RECEIVED, TODAY - timedelta(days=3), TODAY, history)


def test_an_outcome_can_be_reopened():
    for outcome in (S.RESOLVED, S.PARTIALLY_RESOLVED, S.UNRESOLVED, S.CLOSED):
        validate_event(outcome, S.FURTHER_ACTION_NEEDED, None, TODAY)
