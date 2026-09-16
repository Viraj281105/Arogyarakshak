"""
Adversarial tests for per-case access authorization (ADR-009, app/case_auth.py).

These deliberately do NOT rely on AuthAwareTestClient's auto-attach convenience — each
test constructs the exact header (missing, wrong, or belonging to a different case) it
wants to prove is rejected, so a bug in the test-infrastructure shim cannot hide a bug in
the real server-side boundary.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)  # plain client: no auto-attached tokens anywhere in this file

CASE_SCOPED_GET_ROUTES = [
    "/api/v1/kadi/cases/{case_id}",
    "/api/v1/kadi/cases/{case_id}/resolutions",
    "/api/v1/kadi/cases/{case_id}/graph",
]


def _create_case(consent: bool = True) -> "tuple[str, str]":
    res = client.post("/api/v1/kadi/cases", json={"consent_opt_in": consent})
    assert res.status_code == 201
    data = res.json()
    return data["id"], data["access_token"]


# ---------------------------------------------------------------------------
# Token issuance
# ---------------------------------------------------------------------------


def test_case_creation_returns_a_real_access_token():
    res = client.post("/api/v1/kadi/cases", json={"consent_opt_in": True})
    data = res.json()
    assert "access_token" in data
    assert isinstance(data["access_token"], str)
    assert len(data["access_token"]) >= 32  # secrets.token_urlsafe(32) is well over this


def test_two_cases_get_different_tokens():
    _id1, token1 = _create_case()
    _id2, token2 = _create_case()
    assert token1 != token2


def test_access_token_is_never_echoed_back_on_a_later_read():
    """The plaintext token is shown exactly once, at creation. A later GET of the same
    case must not leak it (or any token-shaped field) back."""
    case_id, token = _create_case()
    res = client.get(f"/api/v1/kadi/cases/{case_id}", headers={"X-Case-Access-Token": token})
    assert res.status_code == 200
    body = res.json()
    assert "access_token" not in body
    assert "access_token" not in body.get("case", {})
    assert token not in res.text


# ---------------------------------------------------------------------------
# The core property: a case id alone is not authorization
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path_template", CASE_SCOPED_GET_ROUTES)
def test_no_token_is_rejected(path_template):
    case_id, _token = _create_case()
    res = client.get(path_template.format(case_id=case_id))
    assert res.status_code == 401, f"{path_template} allowed access with no token at all"


@pytest.mark.parametrize("path_template", CASE_SCOPED_GET_ROUTES)
def test_garbage_token_is_rejected(path_template):
    case_id, _token = _create_case()
    res = client.get(
        path_template.format(case_id=case_id),
        headers={"X-Case-Access-Token": "not-a-real-token-at-all"},
    )
    assert res.status_code == 403


@pytest.mark.parametrize("path_template", CASE_SCOPED_GET_ROUTES)
def test_case_a_token_cannot_be_used_to_read_case_b(path_template):
    """The exact property the audit asked for: Case A must not be reachable using
    Case B's (real, validly-issued) token."""
    case_a, _token_a = _create_case()
    _case_b, token_b = _create_case()

    res = client.get(
        path_template.format(case_id=case_a),
        headers={"X-Case-Access-Token": token_b},
    )
    assert res.status_code == 403, (
        f"{path_template}: Case A was reachable using Case B's token — "
        "authorization is not actually per-case"
    )


@pytest.mark.parametrize("path_template", CASE_SCOPED_GET_ROUTES)
def test_correct_token_is_accepted(path_template):
    case_id, token = _create_case()
    res = client.get(
        path_template.format(case_id=case_id),
        headers={"X-Case-Access-Token": token},
    )
    assert res.status_code == 200


def test_nonexistent_case_is_404_regardless_of_token():
    """Existence is checked before authorization (matches the existing 404-before-403
    convention in app.consent) — a guessed id with a garbage token must not be
    distinguishable, via status code alone, from a real id with the wrong token in a way
    that would help an attacker confirm a case id exists.

    Actually verifies the simpler, load-bearing property: a nonexistent case never
    returns 200/403 — only 404."""
    res = client.get(
        "/api/v1/kadi/cases/CASE-doesnotexist12",
        headers={"X-Case-Access-Token": "anything"},
    )
    assert res.status_code == 404


# ---------------------------------------------------------------------------
# Cross-case denial on write/action routes, not just reads
# ---------------------------------------------------------------------------


def test_upload_rejects_a_foreign_case_token():
    case_a, _token_a = _create_case()
    _case_b, token_b = _create_case()

    res = client.post(
        f"/api/v1/kadi/cases/{case_a}/upload",
        files={"file": ("bill.txt", b"Consultation: 500\nTotal Amount: 500\n")},
        headers={"X-Case-Access-Token": token_b},
    )
    assert res.status_code == 403


def test_upload_rejects_no_token():
    case_id, _token = _create_case()
    res = client.post(
        f"/api/v1/kadi/cases/{case_id}/upload",
        files={"file": ("bill.txt", b"Consultation: 500\nTotal Amount: 500\n")},
    )
    assert res.status_code == 401


def test_billnyay_audit_rejects_a_foreign_case_token():
    case_a, _token_a = _create_case()
    _case_b, token_b = _create_case()
    res = client.post(
        f"/api/v1/billnyay/cases/{case_a}/audit",
        headers={"X-Case-Access-Token": token_b},
    )
    assert res.status_code == 403


def test_billnyay_appeal_rejects_a_foreign_case_token():
    case_a, _token_a = _create_case()
    _case_b, token_b = _create_case()
    res = client.post(
        f"/api/v1/billnyay/cases/{case_a}/appeal",
        headers={"X-Case-Access-Token": token_b},
    )
    assert res.status_code == 403


def test_daavisetu_claim_rejects_a_foreign_case_token():
    case_a, _token_a = _create_case()
    _case_b, token_b = _create_case()
    res = client.post(
        f"/api/v1/daavisetu/cases/{case_a}/claim",
        json={
            "patient_name": "Test Patient",
            "policy_number": "POL-1",
            "hospital_name": "Test Hospital",
            "diagnosis": "Test",
            "treatment_plan": "Test",
            "estimated_cost": 1000.0,
        },
        headers={"X-Case-Access-Token": token_b},
    )
    assert res.status_code == 403


def test_dawacheck_case_benchmark_rejects_a_foreign_case_token():
    case_a, _token_a = _create_case()
    _case_b, token_b = _create_case()
    res = client.get(
        f"/api/v1/dawacheck/cases/{case_a}/benchmark",
        headers={"X-Case-Access-Token": token_b},
    )
    assert res.status_code == 403


def test_schemesetu_income_profile_rejects_a_foreign_case_token():
    case_a, _token_a = _create_case()
    _case_b, token_b = _create_case()
    res = client.put(
        f"/api/v1/schemesetu/cases/{case_a}/income-profile",
        json={"annual_income_inr": 100000, "state": "Maharashtra"},
        headers={"X-Case-Access-Token": token_b},
    )
    assert res.status_code == 403


def test_schemesetu_case_eligibility_rejects_a_foreign_case_token():
    case_a, _token_a = _create_case()
    _case_b, token_b = _create_case()
    res = client.post(
        f"/api/v1/schemesetu/cases/{case_a}/eligibility",
        json={"income": 100000, "location_state": "Maharashtra", "medical_need": "checkup"},
        headers={"X-Case-Access-Token": token_b},
    )
    assert res.status_code == 403


def test_resolution_feedback_rejects_a_foreign_case_token():
    case_a, _token_a = _create_case()
    _case_b, token_b = _create_case()
    res = client.post(
        f"/api/v1/kadi/cases/{case_a}/resolutions/DEC-doesnotexist/feedback",
        json={"same_entity": True},
        headers={"X-Case-Access-Token": token_b},
    )
    assert res.status_code == 403


def test_abdm_import_rejects_a_foreign_case_token():
    case_a, _token_a = _create_case()
    _case_b, token_b = _create_case()
    res = client.post(
        f"/api/v1/kadi/cases/{case_a}/abdm/import",
        json={"resourceType": "Bundle", "entry": []},
        headers={"X-Case-Access-Token": token_b},
    )
    assert res.status_code == 403


# ---------------------------------------------------------------------------
# Authorization and consent are layered, not conflated (see app/consent.py docstring)
# ---------------------------------------------------------------------------


def test_owner_without_consent_still_gets_403_from_consent_not_404_or_401():
    """A case's own token grants access to the case; whether that case's context may be
    used cross-module is a SEPARATE, consent_opt_in-gated question. Authorization must
    be checked (and pass) before consent is even evaluated."""
    case_id, token = _create_case(consent=False)
    res = client.post(
        f"/api/v1/billnyay/cases/{case_id}/audit",
        headers={"X-Case-Access-Token": token},
    )
    assert res.status_code == 403
    assert "consent" in res.json()["detail"].lower()


# ---------------------------------------------------------------------------
# SEC-07: a query-string token may authorize a safe GET, never a mutation
# ---------------------------------------------------------------------------


def test_query_string_token_cannot_authorize_a_delete():
    """The exact SEC-07 exploit: a token that leaked via a server log, browser history,
    or Referer header (all realistic ways a query-string token escapes) must not be
    usable to delete the case — only a header-carried token is state-changing-safe."""
    case_id, token = _create_case()
    res = client.delete(f"/api/v1/kadi/cases/{case_id}?access_token={token}")
    assert res.status_code == 401
    assert "header" in res.json()["detail"].lower()

    # Prove the case really is still there — the delete did not silently succeed.
    res2 = client.get(f"/api/v1/kadi/cases/{case_id}", headers={"X-Case-Access-Token": token})
    assert res2.status_code == 200


def test_query_string_token_cannot_authorize_an_upload():
    case_id, token = _create_case()
    res = client.post(
        f"/api/v1/kadi/cases/{case_id}/upload?access_token={token}",
        files={"file": ("bill.txt", b"Consultation: 500\nTotal Amount: 500\n")},
    )
    assert res.status_code == 401


def test_query_string_token_still_authorizes_a_safe_get():
    """The carve-out this exists for (EventSource, direct-download GET) must keep
    working — SEC-07 narrows the exposure, it does not remove the feature."""
    case_id, token = _create_case()
    res = client.get(f"/api/v1/kadi/cases/{case_id}?access_token={token}")
    assert res.status_code == 200


def test_wrong_token_is_rejected_even_before_consent_is_considered():
    """A consent-withheld case with a WRONG token must still fail on authorization
    (access-token mismatch), not be conflated with — or accidentally bypass — the
    consent check."""
    case_id, _token = _create_case(consent=False)
    res = client.post(
        f"/api/v1/billnyay/cases/{case_id}/audit",
        headers={"X-Case-Access-Token": "wrong-token"},
    )
    assert res.status_code == 403
    assert "access token" in res.json()["detail"].lower()
