"""
Adversarial tests for case authorization (ADR-029, app/case_auth.py): a signed-in account
cannot act on another account's case, on any module, and nothing in a URL or a case token
authorizes anything. The generated sweep over every case route is in test_case_ownership.py.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.account_helpers import bearer_for

client = TestClient(app)  # plain client: nothing is attached automatically in this file


def _create_case(consent: bool = True) -> "tuple[str, dict]":
    headers, _ = bearer_for()
    res = client.post("/api/v1/kadi/cases", json={"consent_opt_in": consent}, headers=headers)
    assert res.status_code == 201
    return res.json()["id"], headers


ACTIONS = [
    ("POST", "/api/v1/kadi/cases/{c}/upload", {"files": {"file": ("bill.txt", b"Total Amount: 500\n")}}),
    ("POST", "/api/v1/billnyay/cases/{c}/audit", {}),
    ("POST", "/api/v1/billnyay/cases/{c}/appeal", {}),
    ("POST", "/api/v1/daavisetu/cases/{c}/claim", {"json": {
        "patient_name": "Test Patient", "policy_number": "POL-1", "hospital_name": "Test Hospital",
        "diagnosis": "Test", "treatment_plan": "Test", "estimated_cost": 1000.0}}),
    ("GET", "/api/v1/dawacheck/cases/{c}/benchmark", {}),
    ("PUT", "/api/v1/schemesetu/cases/{c}/income-profile", {"json": {"annual_income_inr": 100000, "state": "Maharashtra"}}),
    ("POST", "/api/v1/schemesetu/cases/{c}/eligibility", {"json": {
        "income": 100000, "location_state": "Maharashtra", "medical_need": "checkup"}}),
    ("POST", "/api/v1/kadi/cases/{c}/resolutions/DEC-doesnotexist/feedback", {"json": {"same_entity": True}}),
    ("POST", "/api/v1/kadi/cases/{c}/abdm/import", {"json": {"resourceType": "Bundle", "entry": []}}),
    ("GET", "/api/v1/kadi/cases/{c}", {}),
    ("GET", "/api/v1/kadi/cases/{c}/graph", {}),
    ("GET", "/api/v1/kadi/cases/{c}/resolutions", {}),
    ("DELETE", "/api/v1/kadi/cases/{c}", {}),
]


@pytest.mark.parametrize("method,path,body", ACTIONS, ids=[f"{m} {p}" for m, p, _ in ACTIONS])
def test_another_account_is_refused_and_the_case_survives(method, path, body):
    case_id, owner = _create_case()
    _, intruder = _create_case()
    res = client.request(method, path.format(c=case_id), headers=intruder, **body)
    assert res.status_code == 403, res.text
    assert client.get(f"/api/v1/kadi/cases/{case_id}", headers=owner).status_code == 200


@pytest.mark.parametrize("method,path,body", ACTIONS, ids=[f"{m} {p}" for m, p, _ in ACTIONS])
def test_a_signed_out_caller_is_refused(method, path, body):
    case_id, _owner = _create_case()
    assert client.request(method, path.format(c=case_id), **body).status_code == 401


def test_creation_issues_no_case_token():
    headers, _ = bearer_for()
    data = client.post("/api/v1/kadi/cases", json={"consent_opt_in": True}, headers=headers).json()
    assert data["access_token"] is None and data["owned"] is True


def test_nonexistent_case_is_404_for_a_signed_in_caller():
    headers, _ = bearer_for()
    assert client.get("/api/v1/kadi/cases/CASE-doesnotexist12", headers=headers).status_code == 404


def test_nothing_in_the_query_string_authorizes_a_request():
    case_id, owner = _create_case()
    token = owner["Authorization"].split()[1]
    assert client.get(f"/api/v1/kadi/cases/{case_id}?access_token={token}").status_code == 401
    assert client.delete(f"/api/v1/kadi/cases/{case_id}?access_token={token}").status_code == 401
    assert client.get(f"/api/v1/kadi/cases/{case_id}", headers=owner).status_code == 200


def test_owner_without_consent_still_gets_403_from_consent_not_404_or_401():
    """Ownership grants access to the case; whether that case's context may be used
    cross-module is a SEPARATE, consent_opt_in-gated question (app/consent.py)."""
    case_id, owner = _create_case(consent=False)
    res = client.post(f"/api/v1/billnyay/cases/{case_id}/audit", headers=owner)
    assert res.status_code == 403
    assert "consent" in res.json()["detail"].lower()
