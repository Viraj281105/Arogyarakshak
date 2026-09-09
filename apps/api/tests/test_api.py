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

