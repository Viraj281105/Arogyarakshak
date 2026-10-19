"""BimaNyay deadline explanation (ADR-015)."""

from datetime import date, timedelta

from bimanyay.tracker import calculate_grievance_timeline


def _events(**kw):
    res = calculate_grievance_timeline("Care Health", kw.pop("date_initiated", "2026-01-01"), **kw)
    return {e.tier: e for e in res.timeline_events}


def test_each_deadline_cites_its_period_and_source():
    ev = _events()
    gro = ev["LEVEL_1_GRO"].explanation
    assert gro.finding_type == "BIMANYAY_DEADLINE"
    rule = next(r for r in gro.rules if r.kind == "STATUTORY_PERIOD")
    assert {f.label: f.value for f in rule.facts}["Period (calendar days)"] == "15"
    assert "Policyholders' Interests" in rule.source
    omb = next(r for r in ev["LEVEL_3_OMBUDSMAN"].explanation.rules if r.kind == "STATUTORY_PERIOD")
    assert "rule 14(3)(b)" in omb.source
    assert "2026-01-16" in gro.headline


def test_clause_not_recorded_for_tiers_where_the_code_cites_none():
    gro = _events()["LEVEL_1_GRO"].explanation
    assert "Insurer GRO must resolve within 15 days: Specific clause" in gro.not_recorded


def test_assumptions_are_disclosed_not_hidden():
    ev = _events()
    codes = [u.code for u in ev["LEVEL_3_OMBUDSMAN"].explanation.undetermined]
    assert {"CLOCK_START_ASSUMED", "CALENDAR_DAYS", "REJECTION_DATE_NOT_USED"} <= set(codes)
    assert "ESCALATION_DATE_ASSUMED" in [u.code for u in ev["LEVEL_2_BIMA_BHAROSA"].explanation.undetermined]


def test_unreadable_start_date_is_flagged_instead_of_silently_replaced():
    ev = _events(date_initiated="not a date")
    exp = ev["LEVEL_1_GRO"].explanation
    assert exp.undetermined[0].code == "START_DATE_UNREADABLE"
    assert exp.evidence[0].value is None and "Dispute start date" in exp.not_recorded
    assert ev["LEVEL_1_GRO"].deadline_date == (date.today() + timedelta(days=15)).isoformat()
