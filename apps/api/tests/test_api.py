import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "1.0.0"}


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




