"""A safety evaluation that fails must be reported as "Safety check unavailable" — never
as "no escalation" or "no rules active" (demo-hardening pass, Phase 5)."""

import pytest

from app.clinical import context as clinical_context
from tests.clinical_helpers import K, MISMATCH_DOC, client, make_case


@pytest.fixture
def broken_safety(monkeypatch):
    async def boom(*_args, **_kwargs):
        raise RuntimeError("rule store unreachable")

    monkeypatch.setattr(clinical_context, "load_active_rules", boom)


def test_escalations_endpoint_reports_unavailable_not_empty(broken_safety):
    case_id = make_case()
    res = client.get(f"{K}/cases/{case_id}/safety-escalations")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "UNAVAILABLE"
    assert body["active_rule_count"] is None, "must not claim zero active rules"
    assert "Safety check unavailable" in body["coverage_note"]
    assert "No clinical safety rules are active" not in body["coverage_note"]


def test_plausibility_survives_and_flags_unavailable_safety(broken_safety):
    case_id = make_case(MISMATCH_DOC)
    res = client.get(f"/api/v1/billnyay/cases/{case_id}/clinical-plausibility")
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["safety_check"]["status"] == "UNAVAILABLE"
    assert body["assessment"]["safety_check_status"] == "UNAVAILABLE"
    assert any("safety check unavailable" in r for r in body["assessment"]["review_reasons"])
    assert body["clinical_review"]["required"] is True


def test_working_safety_check_reports_evaluated():
    case_id = make_case()
    body = client.get(f"{K}/cases/{case_id}/safety-escalations").json()
    assert body["status"] == "EVALUATED"
    plaus = client.get(f"/api/v1/billnyay/cases/{case_id}/clinical-plausibility").json()
    assert plaus["safety_check"]["status"] == "EVALUATED"
