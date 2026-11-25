"""ADR-029: no application functionality is reachable without signing in.

The first test walks every operation in the OpenAPI document, so a route added later is
covered without anyone listing it here.
"""

import re

import pytest
from fastapi.testclient import TestClient

from app.account_auth import SIGN_IN_REQUIRED_DETAIL
from app.auth_gate import PUBLIC_API_PATHS
from app.main import app
from app.services.case_ingestion import create_case_record
from tests.account_helpers import bearer_for, run_db

anonymous = TestClient(app)

_METHODS = ("get", "post", "put", "delete", "patch")
# Operations that authenticate with a staff credential instead of an account session.
_STAFF_REFUSALS = (401, 403, 503)


def _operations():
    for path, item in app.openapi()["paths"].items():
        if path.startswith("/api/v1"):
            for method in _METHODS:
                if method in item:
                    yield method.upper(), path


def _concrete(path: str) -> str:
    return re.sub(r"\{scenario_id\}", "A", re.sub(r"\{(?!scenario_id)[^}]+\}", "x", path))


OPERATIONS = sorted(_operations())


def test_the_sweep_sees_the_whole_api():
    assert len(OPERATIONS) > 60
    assert PUBLIC_API_PATHS <= {path for _, path in OPERATIONS}


@pytest.mark.parametrize("method,path", [op for op in OPERATIONS if op[1] not in PUBLIC_API_PATHS])
def test_every_operation_refuses_a_signed_out_caller(method, path):
    res = anonymous.request(method, _concrete(path))
    assert res.status_code in _STAFF_REFUSALS, f"{method} {path} answered {res.status_code}: {res.text[:200]}"
    # A session-protected operation says why; only staff operations may answer differently.
    if res.status_code == 401 and "credential" not in res.text:
        assert res.json()["detail"] == SIGN_IN_REQUIRED_DETAIL


def test_a_made_up_staff_header_does_not_open_a_patient_route():
    res = anonymous.post(
        "/api/v1/kadi/cases",
        json={"consent_opt_in": True},
        headers={"X-Reviewer-Token": "x", "X-Institution-Token": "x", "X-Governance-Admin-Key": "x"},
    )
    assert res.status_code == 401


def test_creating_a_case_needs_a_session_and_the_case_is_owned():
    headers, _ = bearer_for()
    res = anonymous.post("/api/v1/kadi/cases", json={"consent_opt_in": True}, headers=headers)
    assert res.status_code == 201, res.text
    assert res.json()["owned"] is True
    assert res.json()["access_token"] is None


def _legacy_guest_case():
    """A case created before sign-in became mandatory: unowned, with a token."""

    async def create(db):
        case, token = await create_case_record(db, consent_opt_in=True)
        return case.id, token

    return run_db(create)


def test_a_valid_old_case_token_no_longer_opens_a_case():
    case_id, token = _legacy_guest_case()
    token_header = {"X-Case-Access-Token": token}
    assert anonymous.get(f"/api/v1/kadi/cases/{case_id}", headers=token_header).status_code == 401
    assert anonymous.get(f"/api/v1/kadi/cases/{case_id}?access_token={token}").status_code == 401

    headers, _ = bearer_for()
    res = anonymous.get(f"/api/v1/kadi/cases/{case_id}", headers={**headers, **token_header})
    assert res.status_code == 403
    assert "account" in res.json()["detail"]


def test_an_old_case_can_still_be_claimed_with_its_token_then_opened():
    case_id, token = _legacy_guest_case()
    headers, _ = bearer_for()
    claim = f"/api/v1/kadi/cases/{case_id}/claim"

    assert anonymous.post(claim, headers={"X-Case-Access-Token": token}).status_code == 401
    assert anonymous.post(claim, headers=headers).status_code == 401
    assert anonymous.post(claim, headers={**headers, "X-Case-Access-Token": "wrong"}).status_code == 403

    assert anonymous.post(claim, headers={**headers, "X-Case-Access-Token": token}).status_code == 200
    assert anonymous.get(f"/api/v1/kadi/cases/{case_id}", headers=headers).status_code == 200


def test_another_account_cannot_open_or_delete_an_owned_case():
    owner, _ = bearer_for()
    case_id = anonymous.post("/api/v1/kadi/cases", json={"consent_opt_in": True}, headers=owner).json()["id"]
    intruder, _ = bearer_for()
    assert anonymous.get(f"/api/v1/kadi/cases/{case_id}", headers=intruder).status_code == 403
    assert anonymous.delete(f"/api/v1/kadi/cases/{case_id}", headers=intruder).status_code == 403
    assert anonymous.get(f"/api/v1/kadi/cases/{case_id}", headers=owner).status_code == 200


def test_a_signed_out_session_loses_access_at_once():
    headers, _ = bearer_for()
    assert anonymous.get("/api/v1/kadi/cases", headers=headers).status_code == 200
    assert anonymous.post("/api/v1/kadi/auth/logout", headers=headers).status_code == 204
    assert anonymous.get("/api/v1/kadi/cases", headers=headers).status_code == 401
    assert anonymous.post("/api/v1/dawacheck/benchmark", json={}, headers=headers).status_code == 401


def test_a_reviewer_credential_authenticates_without_a_patient_session():
    headers, _ = bearer_for()
    created = anonymous.post(
        "/api/v1/kadi/clinical-reviewers",
        json={"name": "Dr. Gate", "category": "DOCTOR", "registration_number": "MMC-1",
              "registration_authority": "Maharashtra Medical Council", "specialty": "Surgery"},
        headers=headers,
    )
    assert created.status_code == 201, created.text
    reviewer = {"X-Reviewer-Token": created.json()["reviewer_token"]}
    assert anonymous.get("/api/v1/kadi/clinical-reviewers/me", headers=reviewer).status_code == 200
    assert anonymous.get("/api/v1/kadi/clinical-reviews/assigned", headers=reviewer).status_code == 200
    # The same credential opens nothing that belongs to patients.
    assert anonymous.get("/api/v1/kadi/cases", headers=reviewer).status_code == 401
