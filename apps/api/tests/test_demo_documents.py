"""Scenarios A, B and D (demo/scenarios/) run with the committed synthetic documents in
demo/documents/ through the real upload pipeline (heuristic extraction, no LLM), so the
judge demo's expected outputs are pinned by tests."""

from pathlib import Path

import pytest

from app.config import settings
from tests.clinical_helpers import ADMIN_KEY, FACT_CONFIRM, K, accept, admin, assign, client, finalize, rh

DOCS = Path(__file__).resolve().parents[3] / "demo" / "documents"
B = "/api/v1/billnyay"


@pytest.fixture
def demo(monkeypatch):
    monkeypatch.setattr(settings, "clinical_governance_admin_key", ADMIN_KEY)
    monkeypatch.setattr(settings, "clinical_demo_mode", True)
    monkeypatch.setattr(settings, "groq_api_key", "")  # deterministic heuristic extraction
    res = client.post(f"{K}/clinical-demo/seed", headers=admin())
    assert res.status_code == 200, res.text
    return res.json()


def _case(*names):
    case_id = client.post(f"{K}/cases", json={"consent_opt_in": True}).json()["id"]
    for name in names:
        res = client.post(f"{K}/cases/{case_id}/upload", files={"file": (name, (DOCS / name).read_bytes())})
        assert res.status_code == 202, res.text
    return case_id


def _pdf_text(pdf: bytes) -> str:
    import fitz

    with fitz.open(stream=pdf, filetype="pdf") as doc:
        return " ".join(" ".join(p.get_text().split()) for p in doc)


def test_documents_are_synthetic_and_labelled():
    for path in DOCS.glob("*.txt"):
        assert "SYNTHETIC DOCUMENT FOR DEMONSTRATION ONLY" in path.read_text(encoding="utf-8"), path.name


def test_scenario_a_bill_to_doctor_statement_to_pdf(demo):
    case_id = _case("A_hospital_bill.txt", "A_discharge_summary.txt")
    plaus = client.get(f"{B}/cases/{case_id}/clinical-plausibility").json()
    a = plaus["assessment"]
    assert a["status"] == "CLINICAL_REVIEW_RECOMMENDED", a["summary"]
    assert "Laparoscopic Cholecystectomy" in a["summary"]
    assert {"Room Rent (Private Ward) 3 days", "Nursing Charges", "Registration Charges"} <= set(a["excluded_administrative_items"])
    assert any("MRI Brain" in i for i in a["not_assessed_items"])
    assert plaus["clinical_review"]["required"] is True
    assert plaus["safety_check"]["status"] == "EVALUATED"

    review = client.post(f"{K}/cases/{case_id}/clinical-reviews", json={
        "source_module": "billnyay", "trigger": "PLAUSIBILITY_FLAG", "share_with_reviewer_consent": True,
    }).json()
    doc = demo["reviewers"]["clinician_a"]
    assert assign(case_id, review["review_id"], doc["reviewer_id"]).status_code == 200
    assert accept(review["review_id"], doc["reviewer_token"], "INDEPENDENT_REVIEWER").status_code == 200
    evidence = client.get(f"{K}/clinical-reviews/{review['review_id']}/evidence", headers=rh(doc["reviewer_token"])).json()["evidence"]
    text = ("The discharge summary I reviewed records a laparoscopic appendectomy only. I found no record "
            "supporting the billed cholecystectomy or the indication for the MRI brain.")
    stmt = client.post(f"{K}/clinical-reviews/{review['review_id']}/statements", headers=rh(doc["reviewer_token"]), json={
        "evidence_reviewed": [e["item_id"] for e in evidence[:3]], "reviewer_statement": text,
        "limitations": "Records review only; I did not examine the patient.",
    }).json()
    assert finalize(review["review_id"], stmt["statement_id"], doc["reviewer_token"]).status_code == 200

    appeal = client.post(f"{B}/cases/{case_id}/appeal").json()
    assert appeal["human_clinical_statement_attached"] is True
    pdf = _pdf_text(client.get(f"{B}/cases/{case_id}/appeal/pdf").content)
    assert "I found no record supporting the billed cholecystectomy" in pdf
    assert "Demo verification only" in pdf, "demo verification is labelled, never 'verified'"


def test_scenario_b_preauth_readiness_and_missing_clinical_confirmation(demo):
    case_id = _case("B_preauth_request.txt")
    inst = {"X-Institution-Token": demo["institution"]["institution_token"]}
    body = client.post(f"/api/v1/daavisetu/cases/{case_id}/readiness", json={"playbook_id": demo["playbook_id"]}, headers=inst).json()
    items = {i["item_id"]: i for i in body["items"]}
    assert items["pb_usg_abdomen"]["status"] == "PRESENT"
    assert items["pb_lft_report"]["status"] == "MISSING"
    assert items["pb_conservative_management"]["status"] == "NEEDS_CLINICAL_CONFIRMATION", "keyword found; only a doctor can confirm"
    assert "approv" not in str(body.get("summary", "")).lower() or "not" in str(body.get("summary", "")).lower()

    needs = [i["item_id"] for i in body["items"] if i["status"] == "NEEDS_CLINICAL_CONFIRMATION"]
    assert needs, "at least one clinical fact must need a doctor's confirmation"
    review = client.post(f"/api/v1/daavisetu/cases/{case_id}/readiness/clinical-confirmations",
                         json={"item_ids": needs[:1], "share_with_reviewer_consent": True}).json()
    doc = demo["reviewers"]["clinician_b"]
    assign(case_id, review["review_id"], doc["reviewer_id"])
    accept(review["review_id"], doc["reviewer_token"], "INDEPENDENT_REVIEWER")
    fact_id = review["facts"][0]["fact_id"]
    res = client.post(f"{K}/clinical-reviews/{review['review_id']}/facts/{fact_id}/decision",
                      json={"decision": "CANNOT_DETERMINE", "note": "Not documented in the records shared.", **FACT_CONFIRM},
                      headers=rh(doc["reviewer_token"]))
    assert res.status_code == 200, res.text
    after = client.post(f"/api/v1/daavisetu/cases/{case_id}/readiness", json={}).json()
    item = next(i for i in after["items"] if i["item_id"] == needs[0])
    assert item["status"] == "REVIEWER_COULD_NOT_DETERMINE", "software never marks a clinical fact satisfied"


def test_scenario_d_denial_letter_raises_safety_escalation(demo):
    case_id = _case("D_insurance_denial_letter.txt")
    body = client.get(f"{K}/cases/{case_id}/safety-escalations").json()
    assert body["status"] == "EVALUATED"
    fast = next(e for e in body["escalations"] if e["rule_key"] == "demo-stroke-fast-signs")
    assert set(fast["matched_terms"]) >= {"slurred speech", "arm weakness"}
    assert fast["severity"] == "URGENT" and "decision-support floor" in fast["disclaimer"]
