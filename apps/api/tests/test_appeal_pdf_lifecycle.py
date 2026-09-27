"""Appeal + PDF lifecycle (demo-hardening pass, Phase 3).

The stored, signed appeal PDF must always reflect the CURRENT valid clinician statement:
finalize -> revise/supersede -> withdraw -> cancel -> regenerate. A failed re-render must
roll the statement change back atomically, and the PDF is never served on a wrong token.
"""

import hashlib

import pytest

from app.api.v1.endpoints import billnyay as billnyay_endpoint
from tests.clinical_helpers import K, client, evidence_ids, finalize, full_statement, make_case, rh

B = "/api/v1/billnyay"
V1_TEXT = "In my opinion the documented procedure is consistent with the diagnosis."
V2_TEXT = "Revised: on the additional records, the procedure remains consistent with the diagnosis."


def _pdf_text(pdf_bytes: bytes) -> str:
    import fitz

    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        return " ".join(" ".join(page.get_text().split()) for page in doc)


def _pdf(case_id: str) -> bytes:
    res = client.get(f"{B}/cases/{case_id}/appeal/pdf")
    assert res.status_code == 200, res.text
    return res.content


def _revise_and_finalize(case_id: str, ids) -> str:
    rev = client.post(
        f"{K}/clinical-reviews/{ids['review_id']}/statements/{ids['statement_id']}/revise", headers=rh(ids["token"])
    )
    assert rev.status_code == 201, rev.text
    new_id = rev.json()["statement_id"]
    evidence = evidence_ids(ids["review_id"], ids["token"])
    client.put(
        f"{K}/clinical-reviews/{ids['review_id']}/statements/{new_id}",
        json={"evidence_reviewed": evidence[:1], "reviewer_statement": V2_TEXT, "limitations": "Records only."},
        headers=rh(ids["token"]),
    )
    assert finalize(ids["review_id"], new_id, ids["token"]).status_code == 200
    return new_id


def test_superseded_version_leaves_the_pdf_and_the_new_one_enters_it():
    case_id = make_case()
    ids = full_statement(case_id)
    client.post(f"{B}/cases/{case_id}/appeal")
    assert V1_TEXT in _pdf_text(_pdf(case_id))

    _revise_and_finalize(case_id, ids)
    text = _pdf_text(_pdf(case_id))
    assert V2_TEXT in text
    assert V1_TEXT not in text, "a superseded statement must not remain in the current PDF"
    assert "Statement version: 2" in text
    verify = client.get(f"{B}/cases/{case_id}/appeal/verify").json()
    assert verify["signature_valid"] and verify["hash_matches_stored_bytes"]


def test_full_lifecycle_finalize_revise_withdraw_regenerate():
    case_id = make_case()
    ids = full_statement(case_id)
    client.post(f"{B}/cases/{case_id}/appeal")
    new_id = _revise_and_finalize(case_id, ids)
    client.post(
        f"{K}/clinical-reviews/{ids['review_id']}/statements/{new_id}/withdraw",
        json={"reason": "Further records changed my view."},
        headers=rh(ids["token"]),
    )
    after_withdraw = _pdf_text(_pdf(case_id))
    assert V1_TEXT not in after_withdraw and V2_TEXT not in after_withdraw
    assert "ANNEXURE" not in after_withdraw

    # Regenerating the appeal after the withdrawal still carries no opinion.
    body = client.post(f"{B}/cases/{case_id}/appeal").json()
    assert body["human_clinical_statement_attached"] is False
    assert "ANNEXURE" not in _pdf_text(_pdf(case_id))
    view = client.get(f"{K}/cases/{case_id}/clinical-reviews/{ids['review_id']}").json()
    assert view["current_statement"] is None, "a withdrawn statement is never shown as current"
    assert {s["status"] for s in view["statement_history"]} == {"SUPERSEDED", "WITHDRAWN"}


def test_failed_pdf_rerender_rolls_the_withdrawal_back(monkeypatch):
    case_id = make_case()
    ids = full_statement(case_id)
    client.post(f"{B}/cases/{case_id}/appeal")
    before = _pdf(case_id)

    def broken(*_a, **_k):
        raise RuntimeError("renderer unavailable")

    monkeypatch.setattr(billnyay_endpoint, "compile_appeal_packet_bytes", broken)
    with pytest.raises(RuntimeError):
        client.post(
            f"{K}/clinical-reviews/{ids['review_id']}/statements/{ids['statement_id']}/withdraw",
            json={"reason": "Changed my mind."},
            headers=rh(ids["token"]),
        )
    monkeypatch.undo()

    view = client.get(f"{K}/cases/{case_id}/clinical-reviews/{ids['review_id']}").json()
    assert view["current_statement"]["status"] == "FINALIZED", "the status change must not commit without the PDF"
    assert _pdf(case_id) == before, "stored PDF unchanged and still consistent with the current statement"
    verify = client.get(f"{B}/cases/{case_id}/appeal/verify").json()
    assert verify["signature_valid"] and verify["sha256_hash"] == hashlib.sha256(before).hexdigest()


def test_pdf_is_not_served_on_a_wrong_or_missing_case_token():
    case_a = make_case()
    full_statement(case_a)
    client.post(f"{B}/cases/{case_a}/appeal")
    case_b = make_case()
    token_b = client._case_tokens[case_b]
    wrong = client.get(f"{B}/cases/{case_a}/appeal/pdf", headers={"X-Case-Access-Token": token_b})
    assert wrong.status_code in (401, 403, 404)
    missing = client.get(f"{B}/cases/{case_a}/appeal/pdf", headers={"X-Case-Access-Token": ""})
    assert missing.status_code in (401, 403, 404)
    assert not wrong.content.startswith(b"%PDF") and not missing.content.startswith(b"%PDF")


def test_no_statement_pdf_never_implies_an_insurer_rejection_of_a_clinical_view():
    case_id = make_case()
    body = client.post(f"{B}/cases/{case_id}/appeal").json()
    assert body["human_clinical_statement_attached"] is False
    text = _pdf_text(_pdf(case_id))
    for phrase in ("No statement from a named clinician", "not the opinion of a named doctor", "CLINICAL STATEMENT STATUS"):
        assert phrase not in text, "the absence of a clinician statement is patient-facing only"
    assert "No statement from a named clinician" in body["clinical_statement_notice"]
