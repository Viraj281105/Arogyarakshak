"""Shared helpers for the ADR-011 clinical-review API tests."""

from typing import Dict, Optional, Tuple

from kadi.clinical_review.lifecycle import FACT_DECISION_CONFIRMATION_TEXT, FINALIZATION_CONFIRMATION_TEXT

from app.main import app
from tests.auth_test_client import AuthAwareTestClient

client = AuthAwareTestClient(app)

K = "/api/v1/kadi"
CONFIRM = {"confirmation": True, "confirmation_text": FINALIZATION_CONFIRMATION_TEXT}
FACT_CONFIRM = {"confirmation": True, "confirmation_text": FACT_DECISION_CONFIRMATION_TEXT}
ADMIN_KEY = "test-governance-admin-key"

APPENDIX_DOC = (
    b"City Care Hospital\n"
    b"Patient Name: Asha Rao\n"
    b"Diagnosis: K35.8 Acute appendicitis\n"
    b"Chief complaint: pain abdomen. USG report shows inflamed appendix.\n"
    b"Laparoscopic Appendectomy 45000\n"
    b"Tab Dolo 650mg 30\n"
    b"Total: 45030\n"
)

MISMATCH_DOC = (
    b"City Care Hospital\n"
    b"Diagnosis: K35.8 Acute appendicitis\n"
    b"MRI Brain 12000\n"
    b"Total: 12000\n"
)


def rh(token: str) -> Dict[str, str]:
    return {"X-Reviewer-Token": token}


def admin() -> Dict[str, str]:
    return {"X-Governance-Admin-Key": ADMIN_KEY}


def make_case(doc: Optional[bytes] = APPENDIX_DOC, consent: bool = True) -> str:
    res = client.post(f"{K}/cases", json={"consent_opt_in": consent})
    assert res.status_code == 201, res.text
    case_id = res.json()["id"]
    if doc is not None:
        up = client.post(f"{K}/cases/{case_id}/upload", files={"file": ("doc.txt", doc)})
        assert up.status_code in (200, 202), up.text
    return case_id


def case_token(case_id: str) -> str:
    return client._case_tokens[case_id]


def register(category: str = "DOCTOR", name: str = "Dr. Test Reviewer", reg: Optional[str] = "MMC-12345") -> Tuple[str, str]:
    res = client.post(
        f"{K}/clinical-reviewers",
        json={"name": name, "category": category, "registration_number": reg,
              "registration_authority": "Maharashtra Medical Council", "specialty": "General Surgery"},
    )
    assert res.status_code == 201, res.text
    body = res.json()
    return body["reviewer"]["id"], body["reviewer_token"]


def request_review(case_id: str, source_module: str = "billnyay", **extra) -> str:
    res = client.post(
        f"{K}/cases/{case_id}/clinical-reviews",
        json={"source_module": source_module, "share_with_reviewer_consent": True, **extra},
    )
    assert res.status_code == 201, res.text
    return res.json()["review_id"]


def assign(case_id: str, review_id: str, reviewer_id: str):
    return client.post(f"{K}/cases/{case_id}/clinical-reviews/{review_id}/assign", json={"reviewer_id": reviewer_id})


def accept(review_id: str, token: str, coi: str = "INDEPENDENT_REVIEWER", disclosure: Optional[str] = None):
    return client.post(
        f"{K}/clinical-reviews/{review_id}/accept",
        json={"coi_category": coi, "coi_disclosure": disclosure},
        headers=rh(token),
    )


def evidence_ids(review_id: str, token: str):
    res = client.get(f"{K}/clinical-reviews/{review_id}/evidence", headers=rh(token))
    assert res.status_code == 200, res.text
    return [i["item_id"] for i in res.json()["evidence"]]


def draft(review_id: str, token: str, text: str = "In my opinion the documented procedure is consistent with the diagnosis."):
    ids = evidence_ids(review_id, token)
    res = client.post(
        f"{K}/clinical-reviews/{review_id}/statements",
        json={"evidence_reviewed": ids[:2], "reviewer_statement": text, "limitations": "I did not examine the patient."},
        headers=rh(token),
    )
    assert res.status_code == 201, res.text
    return res.json()["statement_id"]


def finalize(review_id: str, statement_id: str, token: str, body=None):
    return client.post(
        f"{K}/clinical-reviews/{review_id}/statements/{statement_id}/finalize",
        json=CONFIRM if body is None else body,
        headers=rh(token),
    )


def full_statement(case_id: str, source_module: str = "billnyay", coi: str = "HOSPITAL_AFFILIATED"):
    """Request -> assign -> accept (COI) -> draft -> finalize. Returns ids and token."""
    reviewer_id, token = register()
    review_id = request_review(case_id, source_module)
    assert assign(case_id, review_id, reviewer_id).status_code == 200
    assert accept(review_id, token, coi, "Visiting consultant at the treating hospital").status_code == 200
    statement_id = draft(review_id, token)
    res = finalize(review_id, statement_id, token)
    assert res.status_code == 200, res.text
    return {"reviewer_id": reviewer_id, "token": token, "review_id": review_id, "statement_id": statement_id}
