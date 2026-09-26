"""ADR-011 clinical review: reviewers, COI, statement lifecycle, packages, plausibility."""

import json

import pytest

from app.config import settings
from tests.clinical_helpers import (
    ADMIN_KEY,
    CONFIRM,
    K,
    MISMATCH_DOC,
    accept,
    admin,
    assign,
    client,
    draft,
    evidence_ids,
    finalize,
    full_statement,
    make_case,
    register,
    request_review,
    rh,
)


@pytest.fixture
def governance(monkeypatch):
    monkeypatch.setattr(settings, "clinical_governance_admin_key", ADMIN_KEY)
    monkeypatch.setattr(settings, "clinical_demo_mode", False)


# --- Reviewer registry & verification ---------------------------------------------

def test_registration_returns_token_once_and_is_self_declared():
    res = client.post(f"{K}/clinical-reviewers", json={"name": "Dr. A", "category": "DOCTOR", "registration_number": "MMC-9"})
    body = res.json()
    assert res.status_code == 201
    assert body["reviewer_token"]
    assert body["reviewer"]["verification_status"] == "SELF_DECLARED"
    assert "not verified" in body["reviewer"]["verification_label"].lower()
    profile = client.get(f"{K}/clinical-reviewers/{body['reviewer']['id']}").json()
    assert "reviewer_token" not in profile and "credential_hash" not in profile


def test_registration_cannot_claim_verified_status():
    res = client.post(
        f"{K}/clinical-reviewers",
        json={"name": "Dr. Fake", "category": "DOCTOR", "registration_number": "X", "verification_status": "EXTERNALLY_VERIFIED"},
    )
    assert res.json()["reviewer"]["verification_status"] == "SELF_DECLARED"


def test_no_registration_number_means_unverified():
    rid, _ = register(reg=None)
    assert client.get(f"{K}/clinical-reviewers/{rid}").json()["verification_status"] == "UNVERIFIED"


def test_external_verification_is_honestly_unavailable(governance):
    rid, _ = register()
    res = client.post(f"{K}/clinical-reviewers/{rid}/verification", json={"mode": "external"}, headers=admin())
    assert res.status_code == 200
    assert res.json()["outcome"] == "EXTERNAL_VERIFICATION_UNAVAILABLE"
    assert res.json()["reviewer"]["verification_status"] == "SELF_DECLARED"


def test_demo_verification_refused_outside_demo_mode(governance):
    rid, _ = register()
    res = client.post(f"{K}/clinical-reviewers/{rid}/verification", json={"mode": "demo"}, headers=admin())
    assert res.status_code == 403


def test_governance_disabled_without_configured_key(monkeypatch):
    monkeypatch.setattr(settings, "clinical_governance_admin_key", "")
    rid, _ = register()
    res = client.post(f"{K}/clinical-reviewers/{rid}/safety-board", json={"seated": True}, headers=admin())
    assert res.status_code == 503


def test_wrong_governance_key_rejected(governance):
    rid, _ = register()
    res = client.post(
        f"{K}/clinical-reviewers/{rid}/safety-board", json={"seated": True}, headers={"X-Governance-Admin-Key": "nope"}
    )
    assert res.status_code == 403


# --- Requesting a review: consent -----------------------------------------------

def test_review_requires_explicit_share_consent():
    case_id = make_case()
    res = client.post(f"{K}/cases/{case_id}/clinical-reviews", json={"source_module": "billnyay"})
    assert res.status_code == 422


def test_review_requires_case_consent():
    case_id = make_case(consent=False)
    res = client.post(
        f"{K}/cases/{case_id}/clinical-reviews",
        json={"source_module": "billnyay", "share_with_reviewer_consent": True},
    )
    assert res.status_code == 403


def test_evidence_packet_is_scoped_and_recorded():
    case_id = make_case()
    res = client.post(
        f"{K}/cases/{case_id}/clinical-reviews",
        json={"source_module": "billnyay", "share_with_reviewer_consent": True, "evidence_scope": ["diagnosis"]},
    )
    shared = res.json()["evidence_shared"]
    kinds = {i["kind"] for i in shared}
    assert "diagnosis" in kinds
    assert "billing_item" not in kinds and "document_text" not in kinds
    assert any(i["kind"] == "machine_finding" and i["provenance"] == "AI_DERIVED" for i in shared)


def test_non_doctor_cannot_be_assigned_a_clinical_statement():
    case_id = make_case()
    rid, _ = register(category="PHARMACIST", name="Pharm")
    review_id = request_review(case_id)
    assert assign(case_id, review_id, rid).status_code == 422


# --- COI and evidence gating ------------------------------------------------------

def test_evidence_locked_until_coi_declared():
    case_id = make_case()
    rid, tok = register()
    review_id = request_review(case_id)
    assign(case_id, review_id, rid)
    detail = client.get(f"{K}/clinical-reviews/{review_id}", headers=rh(tok)).json()
    assert detail["coi_context"]["hospital_names"] == ["City Care Hospital"]
    assert client.get(f"{K}/clinical-reviews/{review_id}/evidence", headers=rh(tok)).status_code == 409
    assert accept(review_id, tok, "INDEPENDENT_REVIEWER").status_code == 200
    assert client.get(f"{K}/clinical-reviews/{review_id}/evidence", headers=rh(tok)).status_code == 200


def test_coi_category_is_mandatory_and_validated():
    case_id = make_case()
    rid, tok = register()
    review_id = request_review(case_id)
    assign(case_id, review_id, rid)
    assert accept(review_id, tok, "NOT_A_CATEGORY").status_code == 422
    assert accept(review_id, tok, "OTHER", None).status_code == 422


def test_evidence_items_are_redacted():
    case_id = make_case()
    rid, tok = register()
    review_id = request_review(case_id, evidence_scope=["document_text", "diagnosis"])
    assign(case_id, review_id, rid)
    accept(review_id, tok)
    evidence = client.get(f"{K}/clinical-reviews/{review_id}/evidence", headers=rh(tok)).json()
    assert "Asha Rao" not in json.dumps(evidence)


# --- Statement lifecycle -----------------------------------------------------------

def test_full_lifecycle_finalizes_with_attribution_and_coi():
    case_id = make_case()
    ids = full_statement(case_id, coi="HOSPITAL_AFFILIATED")
    review = client.get(f"{K}/cases/{case_id}/clinical-reviews/{ids['review_id']}").json()
    stmt = review["current_statement"]
    assert review["status"] == "COMPLETED"
    assert stmt["status"] == "FINALIZED"
    assert stmt["provenance"] == "HUMAN_AUTHORED"
    assert stmt["coi_category"] == "HOSPITAL_AFFILIATED"
    assert stmt["coi_label"] == "Affiliated with the treating hospital"
    assert stmt["reviewer_snapshot"]["verification_status"] == "SELF_DECLARED"
    assert stmt["reviewer_confirmation"] is True
    assert len(stmt["content_sha256"]) == 64
    assert stmt["limitations"] == "I did not examine the patient."


def test_cannot_finalize_without_explicit_confirmation():
    case_id = make_case()
    rid, tok = register()
    review_id = request_review(case_id)
    assign(case_id, review_id, rid)
    accept(review_id, tok)
    sid = draft(review_id, tok)
    assert finalize(review_id, sid, tok, {}).status_code == 422
    assert finalize(review_id, sid, tok, {"confirmation": True}).status_code == 422
    assert finalize(review_id, sid, tok, {"confirmation": True, "confirmation_text": "ok"}).status_code == 422
    assert finalize(review_id, sid, tok, {"confirmation": False, "confirmation_text": CONFIRM["confirmation_text"]}).status_code == 422
    assert finalize(review_id, sid, tok).status_code == 200


def test_case_holder_never_sees_drafts():
    case_id = make_case()
    rid, tok = register()
    review_id = request_review(case_id)
    assign(case_id, review_id, rid)
    accept(review_id, tok)
    draft(review_id, tok, "Secret working draft")
    view = client.get(f"{K}/cases/{case_id}/clinical-reviews/{review_id}").json()
    assert view["draft_in_progress"] is True
    assert view["current_statement"] is None
    assert "Secret working draft" not in json.dumps(view)


def test_finalized_statement_is_immutable():
    case_id = make_case()
    ids = full_statement(case_id)
    res = client.put(
        f"{K}/clinical-reviews/{ids['review_id']}/statements/{ids['statement_id']}",
        json={"evidence_reviewed": [], "reviewer_statement": "changed", "limitations": "x"},
        headers=rh(ids["token"]),
    )
    assert res.status_code in (409, 422)
    again = finalize(ids["review_id"], ids["statement_id"], ids["token"])
    assert again.status_code == 409


def test_revision_creates_new_version_and_supersedes():
    case_id = make_case()
    ids = full_statement(case_id)
    rev = client.post(
        f"{K}/clinical-reviews/{ids['review_id']}/statements/{ids['statement_id']}/revise", headers=rh(ids["token"])
    )
    assert rev.status_code == 201
    new_id = rev.json()["statement_id"]
    assert rev.json()["statement_version"] == 2
    assert rev.json()["supersedes_statement_id"] == ids["statement_id"]
    evidence = evidence_ids(ids["review_id"], ids["token"])
    client.put(
        f"{K}/clinical-reviews/{ids['review_id']}/statements/{new_id}",
        json={"evidence_reviewed": evidence[:1], "reviewer_statement": "Revised opinion.", "limitations": "Limited records."},
        headers=rh(ids["token"]),
    )
    assert finalize(ids["review_id"], new_id, ids["token"]).status_code == 200
    view = client.get(f"{K}/cases/{case_id}/clinical-reviews/{ids['review_id']}").json()
    assert view["current_statement"]["statement_version"] == 2
    statuses = {s["statement_version"]: s["status"] for s in view["statement_history"]}
    assert statuses == {1: "SUPERSEDED", 2: "FINALIZED"}


def test_withdrawal_removes_current_statement():
    case_id = make_case()
    ids = full_statement(case_id)
    res = client.post(
        f"{K}/clinical-reviews/{ids['review_id']}/statements/{ids['statement_id']}/withdraw",
        json={"reason": "New records received."},
        headers=rh(ids["token"]),
    )
    assert res.status_code == 200 and res.json()["status"] == "WITHDRAWN"
    view = client.get(f"{K}/cases/{case_id}/clinical-reviews/{ids['review_id']}").json()
    assert view["human_statement_exists"] is False


def test_evidence_reviewed_must_come_from_packet():
    case_id = make_case()
    rid, tok = register()
    review_id = request_review(case_id)
    assign(case_id, review_id, rid)
    accept(review_id, tok)
    evidence_ids(review_id, tok)
    res = client.post(
        f"{K}/clinical-reviews/{review_id}/statements",
        json={"evidence_reviewed": ["ENTITY-FROM-ANOTHER-CASE"], "reviewer_statement": "x", "limitations": "y"},
        headers=rh(tok),
    )
    assert res.status_code == 422


# --- Audit -------------------------------------------------------------------------

def test_audit_trail_records_lifecycle_without_sensitive_text():
    case_id = make_case()
    ids = full_statement(case_id)
    events = client.get(f"{K}/cases/{case_id}/clinical-reviews/{ids['review_id']}/audit").json()
    types = [e["event_type"] for e in events]
    for expected in ("REVIEW_REQUESTED", "REVIEWER_ASSIGNED", "COI_DECLARED", "EVIDENCE_ACCESSED",
                     "STATEMENT_CREATED", "STATEMENT_FINALIZED"):
        assert expected in types
    dump = json.dumps(events)
    assert "In my opinion" not in dump
    assert "appendicitis" not in dump.lower()
    assert "Asha" not in dump


# --- Module integration -----------------------------------------------------------

def _pdf_text(pdf_bytes: bytes) -> str:
    import fitz

    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        return "\n".join(page.get_text() for page in doc)


def test_appeal_without_statement_tells_the_patient_not_the_insurer():
    case_id = make_case()
    res = client.post(f"{K.replace('kadi', 'billnyay')}/cases/{case_id}/appeal")
    body = res.json()
    assert res.status_code == 200
    assert body["human_clinical_statement_attached"] is False
    assert body["clinical_statements"] == []
    assert body["clinical_annex"] == ""
    assert "No statement from a named clinician" in body["clinical_statement_notice"]
    pdf = client.get(f"/api/v1/billnyay/cases/{case_id}/appeal/pdf").content
    text = _pdf_text(pdf)
    assert "named clinician" not in text and "ANNEXURE" not in text, "the insurer-facing PDF must not carry the notice"


def test_withdrawn_statement_is_removed_from_the_stored_signed_pdf():
    case_id = make_case()
    ids = full_statement(case_id)
    client.post(f"/api/v1/billnyay/cases/{case_id}/appeal")
    before = client.get(f"/api/v1/billnyay/cases/{case_id}/appeal/pdf").content
    assert "ATTRIBUTED CLINICAL STATEMENT" in _pdf_text(before)

    client.post(
        f"{K}/clinical-reviews/{ids['review_id']}/statements/{ids['statement_id']}/withdraw",
        json={"reason": "New records."},
        headers=rh(ids["token"]),
    )
    after = client.get(f"/api/v1/billnyay/cases/{case_id}/appeal/pdf").content
    assert "ATTRIBUTED CLINICAL STATEMENT" not in _pdf_text(after)
    verify = client.get(f"/api/v1/billnyay/cases/{case_id}/appeal/verify").json()
    assert verify["signature_valid"] is True and verify["hash_matches_stored_bytes"] is True
    assert verify["sha256_hash"] != __import__("hashlib").sha256(before).hexdigest(), (
        "a copy downloaded before the withdrawal must no longer verify"
    )


def test_statement_finalized_after_drafting_is_added_to_the_stored_pdf():
    case_id = make_case()
    client.post(f"/api/v1/billnyay/cases/{case_id}/appeal")
    full_statement(case_id)
    pdf = client.get(f"/api/v1/billnyay/cases/{case_id}/appeal/pdf").content
    assert "ATTRIBUTED CLINICAL STATEMENT" in _pdf_text(pdf)


def test_cancelling_the_review_removes_its_statement_from_the_pdf():
    case_id = make_case()
    ids = full_statement(case_id)
    client.post(f"/api/v1/billnyay/cases/{case_id}/appeal")
    client.post(f"{K}/cases/{case_id}/clinical-reviews/{ids['review_id']}/cancel")
    pdf = client.get(f"/api/v1/billnyay/cases/{case_id}/appeal/pdf").content
    assert "ATTRIBUTED CLINICAL STATEMENT" not in _pdf_text(pdf)


def test_appeal_includes_finalized_statement_verbatim_with_coi_and_verification():
    case_id = make_case()
    full_statement(case_id, coi="HOSPITAL_AFFILIATED")
    body = client.post(f"/api/v1/billnyay/cases/{case_id}/appeal").json()
    assert body["human_clinical_statement_attached"] is True
    annex = body["clinical_annex"]
    assert "In my opinion the documented procedure is consistent with the diagnosis." in annex
    assert "Affiliated with the treating hospital" in annex
    assert "Self-declared registration" in annex
    assert "not an insurer determination" in annex
    assert "In my opinion" not in body["appeal_letter"], "the LLM letter must never contain the human statement"
    pdf = client.get(f"/api/v1/billnyay/cases/{case_id}/appeal/pdf")
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")


def test_cancelled_review_is_excluded_from_appeal():
    case_id = make_case()
    ids = full_statement(case_id)
    client.post(f"{K}/cases/{case_id}/clinical-reviews/{ids['review_id']}/cancel")
    body = client.post(f"/api/v1/billnyay/cases/{case_id}/appeal").json()
    assert body["human_clinical_statement_attached"] is False


def test_fallback_letter_no_longer_asserts_physician_records():
    case_id = make_case()
    body = client.post(f"/api/v1/billnyay/cases/{case_id}/appeal").json()
    assert "records evidence the necessity" not in body["appeal_letter"]


def test_bimanyay_annex_for_case():
    case_id = make_case()
    empty = client.get(f"/api/v1/bimanyay/cases/{case_id}/clinical-statements").json()
    assert empty["human_clinical_statement_attached"] is False
    full_statement(case_id, source_module="bimanyay", coi="TREATING_DOCTOR")
    body = client.get(f"/api/v1/bimanyay/cases/{case_id}/clinical-statements").json()
    assert body["human_clinical_statement_attached"] is True
    assert "Treating doctor for this patient" in body["annex_text"]


def test_bimanyay_analysis_flags_clinical_denials():
    res = client.post(
        "/api/v1/bimanyay/analyze",
        json={
            "policy_number": "P1", "insurer_name": "Acme", "policy_age_years": 2, "claimed_amount": 1000,
            "denied_or_deducted_amount": 1000, "denial_category": "INVESTIGATION_ONLY",
            "denial_reason_raw": "Admission for investigation only", "diagnosis": "Fever",
        },
    )
    assert res.json()["clinical_review"]["requires_clinical_interpretation"] is True


def test_plausibility_plausible_case():
    case_id = make_case()
    body = client.get(f"/api/v1/billnyay/cases/{case_id}/clinical-plausibility").json()
    a = body["assessment"]
    assert a["status"] == "PLAUSIBLE"
    assert a["is_necessity_determination"] is False
    assert a["guideline_citations"] == []
    assert body["clinical_review"]["human_statement_exists"] is False


def test_plausibility_inconsistency_requires_review():
    case_id = make_case(MISMATCH_DOC)
    body = client.get(f"/api/v1/billnyay/cases/{case_id}/clinical-plausibility").json()
    assert body["assessment"]["status"] == "POTENTIAL_INCONSISTENCY"
    assert body["clinical_review"]["status"] == "CLINICAL_REVIEW_REQUIRED"


def test_plausibility_needs_consent():
    case_id = make_case(consent=False)
    assert client.get(f"/api/v1/billnyay/cases/{case_id}/clinical-plausibility").status_code == 403


def test_clinical_context_separates_provenance():
    case_id = make_case()
    full_statement(case_id)
    ctx = client.get(f"{K}/cases/{case_id}/clinical-context").json()
    assert ctx["human_statements"][0]["provenance"] == "HUMAN_AUTHORED"
    assert set(ctx["provenance_legend"]) >= {"AI_DERIVED", "HUMAN_REVIEWED", "HUMAN_AUTHORED", "EXTERNAL_SOURCE"}
    assert "No clinical safety rules are active" in ctx["safety"]["coverage_note"]
