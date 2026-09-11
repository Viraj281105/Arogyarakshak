import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "ok"
    assert data["version"] == "1.0.0"

    # Degraded-mode visibility: operators must be able to see whether the LLM path is
    # actually reachable instead of discovering it from output quality.
    assert "groq_configured" in data
    assert isinstance(data["groq_configured"], bool)
    assert data["groq_model"], "groq_model must be reported"


def test_create_and_get_case():
    # Create case
    payload = {"consent_opt_in": True}
    response = client.post("/api/v1/kadi/cases", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["consent_opt_in"] is True
    
    case_id = data["id"]

    # Upload document
    files = {"file": ("bill.txt", b"Consultation: 200\nWard Stay: 1200\nTotal: 1400")}
    upload_res = client.post(f"/api/v1/kadi/cases/{case_id}/upload", files=files)
    assert upload_res.status_code == 202
    assert upload_res.json()["status"] == "processing"

    # Test Stream
    stream_res = client.get(f"/api/v1/kadi/cases/{case_id}/stream")
    assert stream_res.status_code == 200
    assert "text/event-stream" in stream_res.headers["content-type"]
    
    # Retrieve case
    get_response = client.get(f"/api/v1/kadi/cases/{case_id}")
    assert get_response.status_code == 200
    get_data = get_response.json()
    assert get_data["case"]["id"] == case_id
    assert isinstance(get_data["entities"], list)
    assert len(get_data["entities"]) >= 2
    entity_names = [e["name"] for e in get_data["entities"]]
    assert any("Consultation" in name for name in entity_names)
    assert any("Ward Stay" in name for name in entity_names)



def test_dawacheck_benchmark():
    payload = {"brand_name": "paracetamol 650mg", "mrp": 3.5}
    response = client.post("/api/v1/dawacheck/benchmark", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["brand_name"] == "paracetamol 650mg"
    assert data["is_overcharged"] is True


def test_schemesetu_eligibility():
    payload = {
        "income": 120000.0,
        "location_state": "Maharashtra",
        "category": "General",
        "medical_need": "Heart bypass surgery",
    }
    response = client.post("/api/v1/schemesetu/eligibility", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert data[0]["scheme_name"].startswith("PMJAY")


def test_bimanyay_analyze():
    payload = {
        "policy_number": "POL-554433",
        "insurer_name": "Star Health Insurance",
        "policy_age_years": 6.5,
        "claimed_amount": 180000.0,
        "denied_or_deducted_amount": 180000.0,
        "denial_category": "PED_NON_DISCLOSURE",
        "denial_reason_raw": "Pre-existing condition non-disclosure at inception.",
        "diagnosis": "Cardiovascular Stent Placement",
    }
    response = client.post("/api/v1/bimanyay/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["is_wrongful_denial"] is True
    assert data["reversal_probability_score"] >= 0.90
    assert len(data["regulatory_violations"]) > 0
    assert "GRO" in data["level_1_gro_appeal"]
    assert "bimabharosa" in data["level_2_bimabharosa_text"].lower() or len(data["level_2_bimabharosa_text"]) > 0


def test_bimanyay_analyze_multilingual():
    payload = {
        "policy_number": "POL-MULTI-8877",
        "insurer_name": "Star Health",
        "policy_age_years": 6.0,
        "claimed_amount": 150000.0,
        "denied_or_deducted_amount": 150000.0,
        "denial_category": "PED_NON_DISCLOSURE",
        "denial_reason_raw": "Hypertension not disclosed",
        "diagnosis": "Myocardial Infarction",
    }
    # Test Hindi
    res_hi = client.post("/api/v1/bimanyay/analyze?language=hi", json=payload)
    assert res_hi.status_code == 200
    assert "शिकायत निवारण अधिकारी (GRO)" in res_hi.json()["level_1_gro_appeal"]

    # Test Marathi
    res_mr = client.post("/api/v1/bimanyay/analyze?language=mr", json=payload)
    assert res_mr.status_code == 200
    assert "तक्रार निवारण अधिकारी (GRO)" in res_mr.json()["level_1_gro_appeal"]


def test_bimanyay_timeline():
    payload = {
        "insurer_name": "Care Health Insurance",
        "date_initiated": "2026-03-01",
        "claim_number": "CLM-9988",
        "current_tier": "LEVEL_1_GRO",
    }
    response = client.post("/api/v1/bimanyay/timeline", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["insurer_name"] == "Care Health Insurance"
    assert data["claim_number"] == "CLM-9988"
    assert len(data["timeline_events"]) == 3
    assert data["timeline_events"][0]["tier"] == "LEVEL_1_GRO"


def test_daavisetu_claim():
    # 1. Create case
    res_case = client.post("/api/v1/kadi/cases", json={"consent_opt_in": True})
    assert res_case.status_code == 201
    case_id = res_case.json()["id"]

    # 2. Upload document to populate case
    files = {"file": ("treatment.txt", b"Procedure: Laparoscopic Appendectomy\nHospital: Apollo Hospital\nTotal: 45000")}
    upload_res = client.post(f"/api/v1/kadi/cases/{case_id}/upload", files=files)
    assert upload_res.status_code == 202

    # 3. Call DaaviSetu claim endpoint
    payload = {
        "policy_number": "POL-DAAVI-7766",
        "patient_name": "Viraj Jadhao",
    }
    response = client.post(f"/api/v1/daavisetu/cases/{case_id}/claim", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["claim_id"].startswith("CLAIM-")
    assert data["form_data"]["policy_number"] == "POL-DAAVI-7766"
    assert data["form_data"]["patient_name"] == "Viraj Jadhao"
    assert data["status"] == "ready_for_review"


def test_billnyay_audit():
    # 1. Create case
    res_case = client.post("/api/v1/kadi/cases", json={"consent_opt_in": True})
    assert res_case.status_code == 201
    case_id = res_case.json()["id"]

    # 2. Upload document with line items
    files = {"file": ("bill.txt", b"Consultation: 500\nWard Stay: 2500\nTotal: 3000")}
    upload_res = client.post(f"/api/v1/kadi/cases/{case_id}/upload", files=files)
    assert upload_res.status_code == 202

    # 3. Call BillNyay audit endpoint
    response = client.post(f"/api/v1/billnyay/cases/{case_id}/audit")
    assert response.status_code == 200
    data = response.json()
    assert data["case_id"] == case_id
    assert "total_charged" in data
    assert "total_benchmark" in data
    assert isinstance(data["audit_items"], list)


def test_daavisetu_pdf_download():
    # 1. Create case
    res_case = client.post("/api/v1/kadi/cases", json={"consent_opt_in": True})
    assert res_case.status_code == 201
    case_id = res_case.json()["id"]

    # 2. Upload treatment note
    files = {"file": ("treatment.txt", b"Diagnosis: Appendicitis\nHospital: Apollo Hospital\nEstimated Cost: 45000")}
    upload_res = client.post(f"/api/v1/kadi/cases/{case_id}/upload", files=files)
    assert upload_res.status_code == 202

    # 3. Submit claim
    claim_payload = {
        "policy_number": "POL-STAR-774411",
        "patient_name": "Viraj Jadhao",
        "hospital_name": "Apollo Hospital",
        "treatment_plan": "Laparoscopic Appendectomy",
    }
    claim_res = client.post(f"/api/v1/daavisetu/cases/{case_id}/claim", json=claim_payload)
    assert claim_res.status_code == 200

    # 4. Download PDF
    pdf_res = client.get(f"/api/v1/daavisetu/cases/{case_id}/claim/pdf")
    assert pdf_res.status_code == 200
    assert pdf_res.headers["content-type"] == "application/pdf"
    assert pdf_res.content.startswith(b"%PDF")


def test_dawacheck_mobile_samples():
    samples = [
        ("Dolo 650mg Tablet", 33.5),
        ("Augmentin 625 Duo Tablet", 220.0),
        ("Metformin 500mg SR Tablet", 18.0),
        ("Meropenem 1g Injection", 1850.0),
    ]
    for brand, mrp in samples:
        res = client.post("/api/v1/dawacheck/benchmark", json={"brand_name": brand, "mrp": mrp})
        assert res.status_code == 200
        data = res.json()
        assert data["nppa_ceiling_price"] > 0
        assert data["active_ingredient"] != "Unknown"


def test_cghs_rates_loaded_from_json():
    """Proves the loaded CGHS dataset is the complete JSON dataset (> 20 items), not the 5-item fallback."""
    from app.api.v1.endpoints.billnyay import CGHS_RATES
    assert len(CGHS_RATES) > 20, f"Expected CGHS_RATES > 20 from JSON, got {len(CGHS_RATES)}"
    assert "icu" in CGHS_RATES
    assert "specialist consultation" in CGHS_RATES
    assert "laparoscopic appendectomy" in CGHS_RATES


def test_real_image_ocr_upload_and_persistence():
    """Verifies that uploading a real image document executes EasyOCR, extracts entities, and persists them."""
    import io
    from PIL import Image, ImageDraw

    # 1. Create patient case
    res_case = client.post("/api/v1/kadi/cases", json={"consent_opt_in": True})
    assert res_case.status_code == 201
    case_id = res_case.json()["id"]

    # 2. Synthesize PNG bill image
    img = Image.new("RGB", (600, 200), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.text((20, 30), "Hospital: Lifeline Clinic", fill=(0, 0, 0))
    draw.text((20, 70), "Doctor Consultation: 500", fill=(0, 0, 0))
    draw.text((20, 110), "Diagnostic Blood Test: 750", fill=(0, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    png_bytes = buf.getvalue()

    # 3. Upload image to Kadi upload endpoint
    files = {"file": ("hospital_bill.png", png_bytes, "image/png")}
    upload_res = client.post(f"/api/v1/kadi/cases/{case_id}/upload", files=files)
    assert upload_res.status_code == 202

    # 4. Verify entities retrieved from DB
    get_res = client.get(f"/api/v1/kadi/cases/{case_id}")
    assert get_res.status_code == 200
    case_data = get_res.json()
    assert case_data["case"]["id"] == case_id
    entities = case_data["entities"]
    assert len(entities) > 0, "Expected entities to be extracted and persisted from real image OCR"




# ---------------------------------------------------------------------------
# BillNyay appeal pipeline (regression: endpoint previously returned HTTP 500
# because run_barrister_agent was called with a mismatched signature).
# ---------------------------------------------------------------------------

DENIAL_DOC = (
    b"Lifeline Multispeciality Hospital\n"
    b"Claim Rejection Letter\n"
    b"Denial Code: DEN-4471\n"
    b"Reason: Hospitalisation deemed for investigation only.\n"
    b"Policy Clause: Section 4.1 excludes diagnostic admissions.\n"
    b"Procedure: Laparoscopic Appendectomy\n"
    b"Consultation: 900\n"
    b"Total Amount: 48200\n"
)


def _case_with_document(payload: bytes = DENIAL_DOC) -> str:
    res_case = client.post("/api/v1/kadi/cases", json={"consent_opt_in": True})
    assert res_case.status_code == 201
    case_id = res_case.json()["id"]
    upload = client.post(
        f"/api/v1/kadi/cases/{case_id}/upload", files={"file": ("denial.txt", payload)}
    )
    assert upload.status_code == 202
    return case_id


def test_billnyay_appeal_returns_letter_not_500():
    """The 5-agent appeal pipeline must complete and return a prose letter."""
    case_id = _case_with_document()

    response = client.post(f"/api/v1/billnyay/cases/{case_id}/appeal")
    assert response.status_code == 200, response.text

    data = response.json()
    assert data["case_id"] == case_id

    letter = data["appeal_letter"]
    assert isinstance(letter, str)
    assert len(letter) > 300, "Appeal letter is suspiciously short"

    # Regression guard: the fallback client used to return the Auditor's JSON blob
    # for every agent, so the "letter" came back as a JSON object.
    assert not letter.lstrip().startswith("{"), "Appeal letter must be prose, not a JSON blob"
    assert '"denial_code"' not in letter

    # The letter must actually read as a statutory appeal.
    lowered = letter.lower()
    assert "irdai" in lowered
    assert "appeal" in lowered


def test_billnyay_appeal_scorecard_is_well_formed():
    case_id = _case_with_document()
    response = client.post(f"/api/v1/billnyay/cases/{case_id}/appeal")
    assert response.status_code == 200

    data = response.json()
    scorecard = data["scorecard"]

    assert data["status"] in ("approve", "needs_revision")
    assert scorecard["status"] == data["status"]
    assert 0 <= scorecard["overall_score"] <= 100
    assert 0.0 <= scorecard["confidence_estimate"] <= 1.0

    subs = scorecard["sub_scores"]
    for key in (
        "factual_accuracy",
        "citation_consistency",
        "logical_adequacy",
        "tone_professionalism",
        "hallucination_risk",
    ):
        assert 0 <= subs[key] <= 100, f"sub_score {key} out of range"


def test_billnyay_appeal_unknown_case_returns_404():
    response = client.post("/api/v1/billnyay/cases/CASE-doesnotexist/appeal")
    assert response.status_code == 404


def test_billnyay_grievance_package():
    case_id = _case_with_document()
    response = client.post(f"/api/v1/billnyay/cases/{case_id}/grievance")
    assert response.status_code == 200

    data = response.json()
    assert data["case_id"] == case_id
    assert "Bima Bharosa" in data["complaint_text"]
    assert data["deep_link"].startswith("https://bimabharosa.irdai.gov.in")
    assert data["bima_bharosa_fields"]["Insurer Category"] == "Health Insurance Company"


def test_billnyay_grievance_unknown_case_returns_404():
    response = client.post("/api/v1/billnyay/cases/CASE-doesnotexist/grievance")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# BillNyay audit: three-state benchmarking.
# Regression: unmatched items previously defaulted cghs_benchmark to the charged
# amount, producing a 0% deviation and displaying to the patient as "Fair".
# ---------------------------------------------------------------------------

AUDIT_PROBE_BILL = (
    b"Lifeline Multispeciality Hospital\n"
    b"Patient Name: Ramesh Kulkarni\n"
    b"Diagnosis: Acute Appendicitis\n"
    b"Consultation: 900\n"
    b"ICU: 18500\n"
    b"Blood Test: 750\n"
    b"Dolo 650: 33\n"
    b"Total Amount: 20183\n"
)


def _audited_case(payload: bytes = AUDIT_PROBE_BILL):
    case_id = client.post("/api/v1/kadi/cases", json={"consent_opt_in": True}).json()["id"]
    assert client.post(
        f"/api/v1/kadi/cases/{case_id}/upload", files={"file": ("bill.txt", payload)}
    ).status_code == 202
    res = client.post(f"/api/v1/billnyay/cases/{case_id}/audit")
    assert res.status_code == 200, res.text
    return case_id, res.json()


def test_audit_captures_icu_line_and_full_bill_total():
    """The ICU line used to be dropped; total_charged reported 1650 of a 20183 bill."""
    _, data = _audited_case()
    by_name = {i["item_name"]: i["charged"] for i in data["audit_items"]}

    assert "ICU" in by_name, "ICU line must reach the audit"
    assert by_name["ICU"] == 18500.0
    assert by_name["Dolo 650"] == 33.0, "Dosage must not be read as the price"
    assert "Total Amount" not in by_name, "Summary line must not be audited as a charge"
    assert data["total_charged"] == 20183.0


def test_unmatched_item_is_not_reported_as_fair():
    """An item with no CGHS counterpart must be 'not_benchmarked', never 'fair'."""
    _, data = _audited_case()
    items = {i["item_name"]: i for i in data["audit_items"]}

    dolo = items["Dolo 650"]
    assert dolo["benchmarked"] is False
    assert dolo["status"] == "not_benchmarked"
    assert dolo["cghs_benchmark"] is None
    assert dolo["is_deviation"] is False
    # It must not masquerade as a verified-fair line.
    assert dolo["status"] != "within_benchmark"


def test_benchmarked_overcharges_still_flagged():
    _, data = _audited_case()
    items = {i["item_name"]: i for i in data["audit_items"]}

    icu = items["ICU"]
    assert icu["benchmarked"] is True
    assert icu["status"] == "overcharged"
    assert icu["cghs_benchmark"] == 5400.0
    assert icu["is_deviation"] is True
    assert icu["deviation_percentage"] > 200

    consultation = items["Consultation"]
    assert consultation["status"] == "overcharged"
    assert consultation["cghs_benchmark"] == 350.0


def test_audit_totals_separate_benchmarked_from_unmatched():
    _, data = _audited_case()

    assert data["unmatched_count"] == 1
    assert data["unmatched_amount"] == 33.0
    assert data["benchmarked_count"] == 3
    assert data["benchmarked_charged"] == 20150.0
    assert data["total_benchmark"] == 6000.0  # 350 + 5400 + 250

    # Savings must be computed only over items that were actually compared.
    assert data["potential_savings"] == 14150.0
    assert data["potential_savings"] == data["benchmarked_charged"] - data["total_benchmark"]


def test_audit_never_reports_negative_savings():
    payload = b"Consultation: 100\n"
    _, data = _audited_case(payload)
    assert data["potential_savings"] >= 0.0


def test_longest_cghs_key_wins():
    """'ICU Day Charges' must match its own rate, not the shorter 'icu' key."""
    from app.api.v1.endpoints.billnyay import CGHS_RATES, _match_cghs_rate

    rate, bundled = _match_cghs_rate("icu day charges", CGHS_RATES)
    assert rate == 5400.0
    assert bundled is False

    assert _match_cghs_rate("completely unknown item", CGHS_RATES) == (None, False)
    assert _match_cghs_rate("", CGHS_RATES) == (None, False)


def test_bundled_item_flagged_as_deviation():
    payload = b"Nursing Charges: 1200\n"
    _, data = _audited_case(payload)
    item = data["audit_items"][0]
    assert item["status"] == "bundled"
    assert item["is_deviation"] is True


# ---------------------------------------------------------------------------
# Groq configuration visibility.
# Regression: an unset GROQ_API_KEY silently downgraded every LLM path with no
# operator- or caller-visible signal.
# ---------------------------------------------------------------------------

def test_health_reports_groq_state_matching_settings():
    from app.config import settings

    data = client.get("/health").json()
    assert data["groq_configured"] is bool(settings.groq_api_key)
    assert data["groq_model"] == settings.groq_model


def test_appeal_reports_whether_letter_is_llm_backed():
    from app.config import settings

    case_id = _case_with_document()
    data = client.post(f"/api/v1/billnyay/cases/{case_id}/appeal").json()

    assert "llm_backed" in data
    assert data["llm_backed"] is bool(settings.groq_api_key)


def test_env_example_documents_groq_api_key():
    """The Docker quickstart tells users to set GROQ_API_KEY; the template must list it."""
    import pathlib

    root = pathlib.Path(__file__).resolve().parents[3]
    env_example = (root / ".env.example").read_text(encoding="utf-8")
    assert "GROQ_API_KEY" in env_example, ".env.example must document GROQ_API_KEY"


def test_docker_compose_passes_groq_api_key_to_api():
    """Without this the container can never reach Groq regardless of the user's .env."""
    import pathlib

    root = pathlib.Path(__file__).resolve().parents[3]
    compose = (root / "docker-compose.yml").read_text(encoding="utf-8")
    assert "GROQ_API_KEY" in compose, "docker-compose.yml must forward GROQ_API_KEY to the api service"


def test_kadi_entities_are_clean_end_to_end():
    """Full Kadi path: upload -> OCR -> extraction -> persistence.

    Mirrors the live audit probe that produced hospital='Hospital\nPatient Name',
    a 'Total Amount' procedure and a missing ICU line.
    """
    case_id = client.post("/api/v1/kadi/cases", json={"consent_opt_in": True}).json()["id"]
    assert client.post(
        f"/api/v1/kadi/cases/{case_id}/upload", files={"file": ("bill.txt", AUDIT_PROBE_BILL)}
    ).status_code == 202

    data = client.get(f"/api/v1/kadi/cases/{case_id}").json()
    entities = data["entities"]
    by_type = {}
    for e in entities:
        by_type.setdefault(e["type"], []).append(e)

    hospital = by_type["hospital"][0]["name"]
    assert hospital == "Lifeline Multispeciality Hospital"
    assert "\n" not in hospital

    assert by_type["patient"][0]["name"] == "Ramesh Kulkarni"
    assert by_type["diagnosis"][0]["name"] == "Acute Appendicitis"

    billing_names = {e["name"] for e in by_type["billing_item"]}
    assert "ICU" in billing_names
    assert "Total Amount" not in billing_names

    # No entity of any type may be the document's summary row.
    all_names = {e["name"] for e in entities}
    assert "Total Amount" not in all_names

    # The persisted case total must reflect the whole bill, not a fraction of it.
    assert data["case"]["total_charged"] == 20183.0
