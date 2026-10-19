"""'Why am I seeing this?' explanations on existing responses (ADR-017).

The explanation is produced next to each decision by the owning package, from stored data
only, and travels on the SAME authorised endpoint — so it needs no new access path.
"""

from app.api.v1.endpoints import kadi as kadi_endpoint
from kadi.extraction import ExtractedEntities
from tests.clinical_helpers import K, client


def _case():
    return client.post(f"{K}/cases", json={"consent_opt_in": True}).json()["id"]


def test_billnyay_audit_lines_carry_evidence_row_and_unrecorded_code():
    case_id = _case()
    client.post(
        f"{K}/cases/{case_id}/upload",
        files={"file": ("hospital_bill.txt", b"Consultation (1 visit): 500\nWard Stay (1 day): 2500\nTotal: 3000")},
    )
    items = {i["item_name"]: i for i in client.post(f"/api/v1/billnyay/cases/{case_id}/audit").json()["audit_items"]}
    exp = items["Consultation (1 visit)"]["explanation"]
    assert exp["finding_type"] == "BILLNYAY_LINE"
    assert exp["evidence"][0]["document"] == "hospital_bill.txt"
    row = next(r for r in exp["rules"] if r["kind"] == "REFERENCE_TABLE_ROW")
    assert row["source"].startswith("CGHS rate schedule")
    assert {f["label"]: f["value"] for f in row["facts"]}["Reference rate"] == "₹350"
    assert any("CGHS procedure code" in n for n in exp["not_recorded"])
    # existing fields are untouched
    assert items["Consultation (1 visit)"]["cghs_benchmark"] == 350.0


def test_unmatched_bill_line_explains_it_was_not_checked():
    case_id = _case()
    client.post(f"{K}/cases/{case_id}/upload", files={"file": ("b.txt", b"Zzyzx Gadget Fee: 900\nTotal: 900")})
    item = client.post(f"/api/v1/billnyay/cases/{case_id}/audit").json()["audit_items"][0]
    assert item["status"] == "not_benchmarked"
    assert item["explanation"]["undetermined"][0]["code"] == "NO_REFERENCE_MATCH"
    assert item["explanation"]["rules"] == []


def test_dawacheck_case_medicine_explanation(monkeypatch):
    text = "Tab Pan 40 (Strip of 15) 60.00"

    def fake_parse(file_bytes, filename):
        return {"extraction_ok": True, "full_text_content": text, "line_items": [], "ocr_segments": []}

    def fake_extract(_text, api_key=None, model=None):
        return ExtractedEntities(hospital_name="Demo Pharmacy", medicines=[{"name": "Pan 40", "cost": 60.0}])

    monkeypatch.setattr(kadi_endpoint, "parse_document", fake_parse)
    monkeypatch.setattr(kadi_endpoint, "extract_entities_from_text", fake_extract)
    case_id = _case()
    client.post(f"{K}/cases/{case_id}/upload", files={"file": ("pharmacy.pdf", text.encode())})
    row = client.get(f"/api/v1/dawacheck/cases/{case_id}/benchmark").json()[0]
    exp = row["explanation"]
    assert exp["finding_type"] == "DAWACHECK_MEDICINE"
    assert exp["trust"]["code"] == "MACHINE_EXTRACTED"
    assert exp["evidence"][0]["document"] == "pharmacy.pdf"
    basis = next(e for e in exp["evidence"] if e["label"].startswith("Price basis"))
    assert basis["source_text"] == "strip of 15"
    assert {r["kind"] for r in exp["rules"]} == {"REFERENCE_TABLE_ROW", "PRICE_BASIS"}


def test_dawacheck_manual_check_marks_everything_as_user_entered():
    body = client.post("/api/v1/dawacheck/benchmark", json={"brand_name": "Dolo 650", "mrp": 5.0}).json()
    exp = body["explanation"]
    assert exp["trust"]["code"] == "USER_ENTERED"
    assert exp["evidence"][0]["provenance"] == "USER_ENTERED"
    assert body["nppa_ceiling_price"] == 2.3  # existing shape preserved


def test_daavisetu_readiness_items_explain_their_rule():
    case_id = _case()
    client.post(
        f"{K}/cases/{case_id}/upload",
        files={"file": ("treatment.txt", b"Procedure: Laparoscopic Appendectomy\nHospital: Apollo Hospital\nTotal: 45000")},
    )
    items = {i["item_id"]: i for i in client.post(f"/api/v1/daavisetu/cases/{case_id}/readiness", json={}).json()["items"]}
    present = items["hospital_identified"]["explanation"]
    assert present["rules"][0]["kind"] == "ENTITY_PRESENCE_RULE"
    assert present["evidence"][0]["document"] == "treatment.txt"
    missing = items["clinical_findings"]["explanation"]
    assert missing["undetermined"][0]["code"] == "NOT_FOUND_IN_SEARCHED_SCOPE"


def test_bimanyay_deadlines_explain_their_period_and_assumptions():
    res = client.post(
        "/api/v1/bimanyay/timeline",
        json={"insurer_name": "Care Health Insurance", "date_initiated": "2026-01-01", "current_tier": "LEVEL_1_GRO"},
    )
    events = {e["tier"]: e for e in res.json()["timeline_events"]}
    exp = events["LEVEL_3_OMBUDSMAN"]["explanation"]
    assert exp["finding_type"] == "BIMANYAY_DEADLINE"
    assert "rule 14(3)(b)" in next(r for r in exp["rules"] if r["kind"] == "STATUTORY_PERIOD")["source"]
    assert "REJECTION_DATE_NOT_USED" in [u["code"] for u in exp["undetermined"]]


def test_explanations_never_come_from_a_model_and_say_so():
    body = client.post("/api/v1/dawacheck/benchmark", json={"brand_name": "Dolo 650", "mrp": 5.0}).json()
    assert "no AI model" in body["explanation"]["generated_by"]
