"""DawaCheck price basis through the real upload pipeline.

upload -> OCR text -> extraction (possibly LLM-normalised names) -> Kadi grounds each
medicine to its bill line -> DawaCheck records what the line says about quantity/pack ->
case benchmark compares per unit, or refuses.

Before this change a bill line "Tab Pan 40 (Strip of 15) 60.00" whose name the LLM
normalised to "Pan 40" was compared as ₹60 per tablet against the ₹3.20 ceiling
("+1,775%"); a strip price on its own line was compared the same way.
"""

from app.api.v1.endpoints import kadi as kadi_endpoint
from kadi.extraction import ExtractedEntities
from tests.clinical_helpers import K, client


def _upload(monkeypatch, text, medicines):
    def fake_parse(file_bytes, filename):
        return {"extraction_ok": True, "full_text_content": text, "line_items": [], "ocr_segments": []}

    def fake_extract(_text, api_key=None, model=None):
        return ExtractedEntities(hospital_name="Synthetic Demo Pharmacy", medicines=[dict(m) for m in medicines])

    monkeypatch.setattr(kadi_endpoint, "parse_document", fake_parse)
    monkeypatch.setattr(kadi_endpoint, "extract_entities_from_text", fake_extract)
    case_id = client.post(f"{K}/cases", json={"consent_opt_in": True}).json()["id"]
    res = client.post(f"{K}/cases/{case_id}/upload", files={"file": ("bill.pdf", text.encode())})
    assert res.status_code == 202, res.text
    return case_id


def _bench(case_id):
    res = client.get(f"/api/v1/dawacheck/cases/{case_id}/benchmark")
    assert res.status_code == 200, res.text
    return {r["brand_name"]: r for r in res.json()}


def test_llm_normalised_name_keeps_the_strip_size_stated_on_its_bill_line(monkeypatch):
    text = "SYNTHETIC PHARMACY BILL\nTab Pan 40 (Strip of 15) 60.00\nTab Dolo 650 Qty: 10 25.00\nTotal 85.00"
    case_id = _upload(
        monkeypatch,
        text,
        # What an LLM extractor returns: clean names, pack and quantity dropped.
        [{"name": "Pan 40", "dosage": "40mg", "cost": 60.0}, {"name": "Dolo 650", "dosage": "650mg", "cost": 25.0}],
    )
    bench = _bench(case_id)

    pan = bench["Pan 40"]["benchmark"]
    assert pan["comparison_status"] == "COMPARED"
    assert pan["price_basis_label"] == "per strip of 15" and pan["basis_source"] == "DOCUMENT_LINE"
    assert pan["billed_unit_price"] == 4.0 and pan["is_overcharged"] is True
    assert pan["deviation_percentage"] == 25.0

    dolo = bench["Dolo 650"]["benchmark"]
    assert dolo["price_basis"] == "LINE_TOTAL" and dolo["price_basis_label"] == "total for 10 tablets"
    assert dolo["billed_unit_price"] == 2.5 and dolo["is_overcharged"] is True


def test_the_raw_bill_line_is_not_stored_only_the_derived_facts(monkeypatch):
    text = "Tab Pan 40 (Strip of 15) 60.00"
    case_id = _upload(monkeypatch, text, [{"name": "Pan 40", "cost": 60.0}])
    entities = client.get(f"{K}/cases/{case_id}").json()["entities"]
    pan = next(e for e in entities if e["type"] == "medicine")
    meta = pan.get("meta") or {}
    assert "source_line" not in meta
    assert meta["price_facts"]["basis"] == "PER_STRIP"
    assert meta["price_facts"]["evidence"] == "strip of 15"


def test_a_name_on_two_lines_with_the_same_amount_is_not_guessed(monkeypatch):
    # Two lines could be the source: grounding refuses, the basis stays unknown, and the
    # medicine is matched but not compared.
    text = "Tab Pan 40 (Strip of 15) 60.00\nTab Pan 40 (Strip of 10) 60.00"
    case_id = _upload(monkeypatch, text, [{"name": "Pan 40", "cost": 60.0}])
    pan = _bench(case_id)["Pan 40"]["benchmark"]
    assert pan["comparison_status"] == "CANNOT_COMPARE"
    assert pan["comparison_reason_code"] == "BASIS_UNKNOWN"
    assert pan["is_overcharged"] is None


def test_missing_ceiling_is_reported_not_compared(monkeypatch):
    # A medicine absent from the curated reference has no ceiling: no benchmark at all,
    # with a note that absence is not evidence of being uncontrolled.
    text = "Tab Zyxwvu 50 (Strip of 10) 90.00"
    case_id = _upload(monkeypatch, text, [{"name": "Zyxwvu 50", "cost": 90.0}])
    row = _bench(case_id)["Zyxwvu 50"]
    assert row["benchmark"] is None
    assert "does NOT mean" in row["note"]


def test_missing_cost_is_reported_not_compared(monkeypatch):
    text = "Tab Pan 40 (Strip of 15)"
    case_id = _upload(monkeypatch, text, [{"name": "Pan 40", "cost": None}])
    row = _bench(case_id)["Pan 40"]
    assert row["benchmark"] is None
    assert row["note"]


def test_auto_trigger_summary_does_not_count_an_unclear_basis_as_benchmarked(monkeypatch):
    text = "Pan 40 60.00\nTab Dolo 650 (Strip of 15) 33.00"
    case_id = _upload(
        monkeypatch, text, [{"name": "Pan 40", "cost": 60.0}, {"name": "Dolo 650", "cost": 33.0}]
    )
    insights = client.get(f"{K}/cases/{case_id}/insights").json()
    summary = next(i for i in insights["insights"] if i["module_check"] == "dawacheck_benchmark")["summary"]
    assert summary["benchmarked"] == 1  # Dolo, from its strip of 15
    assert summary["price_basis_unclear"] == 1  # Pan 40: ₹60 for an unstated quantity
    assert summary["overcharged"] == 0


def test_manual_check_takes_the_declared_basis():
    strip = client.post(
        "/api/v1/dawacheck/benchmark",
        json={"brand_name": "Dolo 650", "mrp": 33.0, "price_basis": "PER_STRIP", "units_per_pack": 15},
    ).json()
    assert strip["comparison_status"] == "COMPARED" and strip["billed_unit_price"] == 2.2
    assert strip["basis_source"] == "DECLARED" and strip["is_overcharged"] is False

    contradicted = client.post(
        "/api/v1/dawacheck/benchmark",
        json={"brand_name": "Dolo 650mg Tablet (15s)", "mrp": 33.5, "price_basis": "PER_UNIT"},
    ).json()
    assert contradicted["comparison_status"] == "CANNOT_COMPARE"
    assert contradicted["comparison_reason_code"] == "BASIS_CONTRADICTS_NAME"
    assert contradicted["is_overcharged"] is None

    missing = client.post(
        "/api/v1/dawacheck/benchmark", json={"brand_name": "Dolo 650", "mrp": 33.0, "price_basis": "PER_STRIP"}
    ).json()
    assert missing["comparison_reason_code"] == "PACK_SIZE_MISSING"

    bad = client.post("/api/v1/dawacheck/benchmark", json={"brand_name": "Dolo 650", "mrp": 3.0, "price_basis": "PER_BOX"})
    assert bad.status_code == 422
