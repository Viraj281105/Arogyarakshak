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
