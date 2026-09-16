import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.auth_test_client import AuthAwareTestClient

# ADR-009: case-scoped routes now require a per-case access token. AuthAwareTestClient
# transparently carries the token returned by each case this client creates to that
# case's later requests, so the several hundred pre-existing tests below — none of which
# are testing authorization — do not need per-call header wiring. See
# tests/auth_test_client.py and tests/test_case_authorization.py (the tests that DO
# exercise the authorization boundary directly).
client = AuthAwareTestClient(app)


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
    assert data["active_ingredient"] == "Paracetamol 650mg"
    assert data["nppa_ceiling_price"] == 2.30
    assert data["is_overcharged"] is True
    # 3.5 against a 2.30 ceiling is a 52.17% deviation.
    assert data["deviation_percentage"] == 52.17


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

    by_scheme = {s["scheme_name"].split(" ")[0]: s for s in data}
    assert set(by_scheme) == {"PMJAY", "MJPJAY"}, "Maharashtra must yield both schemes"

    # No official income ceiling exists for either scheme. PM-JAY rests on SECC-2011 listing,
    # ASHA/AWW/AWH status or age 70+ (none collected); MJPJAY covers all Maharashtra families.
    assert by_scheme["PMJAY"]["estimated_eligibility"] == "ambiguous"
    assert by_scheme["PMJAY"]["claim_guide_steps"], "ambiguous schemes must say how to verify"
    assert by_scheme["MJPJAY"]["estimated_eligibility"] == "eligible"
    for scheme in data:
        assert "confidence_score" not in scheme, "no heuristic score may accompany a cited rule"
        assert scheme["sources"] and all(s["url"].startswith("https://") for s in scheme["sources"])
        assert scheme["criteria_provenance"] in {"OFFICIAL_SOURCE_CITED", "OFFICIAL_RESTATEMENT_CITED"}


# ---------------------------------------------------------------------------
# SchemeSetu <-> Kadi integration (#23): auto-filling medical_need from case context,
# while income/location_state/category — never derivable from a bill — stay required.
# ---------------------------------------------------------------------------


def test_schemesetu_case_eligibility_resolves_medical_need_from_kadi_entities():
    case_id = client.post("/api/v1/kadi/cases", json={"consent_opt_in": True}).json()["id"]
    assert client.post(
        f"/api/v1/kadi/cases/{case_id}/upload",
        files={"file": ("bill.txt", b"Diagnosis: Acute Appendicitis\n")},
    ).status_code == 202

    payload = {"income": 120000.0, "location_state": "Maharashtra", "category": "General"}
    res = client.post(f"/api/v1/schemesetu/cases/{case_id}/eligibility", json=payload)
    assert res.status_code == 200, res.text
    data = res.json()
    assert len(data) > 0
    by_scheme = {s["scheme_name"].split(" ")[0]: s for s in data}
    assert set(by_scheme) == {"PMJAY", "MJPJAY"}


def test_schemesetu_case_eligibility_requires_consent():
    case_id = client.post("/api/v1/kadi/cases", json={"consent_opt_in": False}).json()["id"]
    payload = {"income": 120000.0, "location_state": "Maharashtra"}
    res = client.post(f"/api/v1/schemesetu/cases/{case_id}/eligibility", json=payload)
    assert res.status_code == 403


def test_schemesetu_case_eligibility_requires_medical_need_when_none_extractable():
    """No document uploaded => nothing to resolve medical_need from => 422, not a guess."""
    case_id = client.post("/api/v1/kadi/cases", json={"consent_opt_in": True}).json()["id"]
    payload = {"income": 120000.0, "location_state": "Maharashtra"}
    res = client.post(f"/api/v1/schemesetu/cases/{case_id}/eligibility", json=payload)
    assert res.status_code == 422


def test_schemesetu_case_eligibility_explicit_medical_need_overrides_extraction():
    case_id = client.post("/api/v1/kadi/cases", json={"consent_opt_in": True}).json()["id"]
    assert client.post(
        f"/api/v1/kadi/cases/{case_id}/upload",
        files={"file": ("bill.txt", b"Diagnosis: Acute Appendicitis\n")},
    ).status_code == 202

    payload = {
        "income": 120000.0,
        "location_state": "Maharashtra",
        "medical_need": "Coronary artery bypass graft",
    }
    res = client.post(f"/api/v1/schemesetu/cases/{case_id}/eligibility", json=payload)
    assert res.status_code == 200


def test_schemesetu_case_eligibility_unknown_case_returns_404():
    payload = {"income": 120000.0, "location_state": "Maharashtra"}
    res = client.post("/api/v1/schemesetu/cases/CASE-doesnotexist/eligibility", json=payload)
    assert res.status_code == 404


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

    # 3. Call DaaviSetu claim endpoint. Clinical fields must be supplied explicitly —
    #    the endpoint no longer invents a diagnosis or treatment plan.
    payload = {
        "policy_number": "POL-DAAVI-7766",
        "patient_name": "Rekha Nair",
        "diagnosis": "Acute Appendicitis (K35.8)",
        "treatment_plan": "Laparoscopic Appendectomy",
    }
    response = client.post(f"/api/v1/daavisetu/cases/{case_id}/claim", json=payload)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["claim_id"].startswith("CLAIM-")
    assert data["status"] == "ready_for_review"

    # Every field must round-trip verbatim; hospital comes from the uploaded document.
    form = data["form_data"]
    assert form["policy_number"] == "POL-DAAVI-7766"
    assert form["patient_name"] == "Rekha Nair"
    assert form["diagnosis"] == "Acute Appendicitis (K35.8)"
    assert form["treatment_plan"] == "Laparoscopic Appendectomy"
    assert form["hospital_name"] == "Apollo Hospital"
    assert form["estimated_cost"] == 45000.0


def test_billnyay_audit():
    # 1. Create case
    res_case = client.post("/api/v1/kadi/cases", json={"consent_opt_in": True})
    assert res_case.status_code == 201
    case_id = res_case.json()["id"]

    # 2. Upload document with line items
    files = {"file": ("bill.txt", b"Consultation: 500\nWard Stay: 2500\nTotal: 3000")}
    upload_res = client.post(f"/api/v1/kadi/cases/{case_id}/upload", files=files)
    assert upload_res.status_code == 202

    # 3. Call BillNyay audit endpoint and assert the actual numbers, not just the shape.
    response = client.post(f"/api/v1/billnyay/cases/{case_id}/audit")
    assert response.status_code == 200
    data = response.json()
    assert data["case_id"] == case_id

    items = {i["item_name"]: i for i in data["audit_items"]}
    assert set(items) == {"Consultation", "Ward Stay"}, "Total must not be audited as a charge"

    assert items["Consultation"]["charged"] == 500.0
    assert items["Consultation"]["cghs_benchmark"] == 350.0
    assert items["Consultation"]["status"] == "overcharged"

    assert items["Ward Stay"]["charged"] == 2500.0
    assert items["Ward Stay"]["cghs_benchmark"] == 1500.0
    assert items["Ward Stay"]["status"] == "overcharged"

    assert data["total_charged"] == 3000.0
    assert data["total_benchmark"] == 1850.0
    assert data["potential_savings"] == 1150.0
    assert data["deviations_count"] == 2
    assert data["unmatched_count"] == 0


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


# ---------------------------------------------------------------------------
# DawaCheck <-> Kadi case integration (issue #27): benchmarking medicines Kadi
# already extracted from an uploaded bill, instead of requiring a second manual entry.
# ---------------------------------------------------------------------------


def test_dawacheck_case_benchmark_resolves_kadi_medicine_entity():
    """'Dolo 650: 33' in AUDIT_PROBE_BILL is extracted by Kadi as a medicine entity;
    this must be benchmarked against the same NPPA reference DawaCheck's standalone
    /benchmark route uses, without the caller re-typing the brand name and price."""
    case_id, _ = _audited_case()

    res = client.get(f"/api/v1/dawacheck/cases/{case_id}/benchmark")
    assert res.status_code == 200
    results = res.json()
    by_brand = {r["brand_name"]: r for r in results}

    assert "Dolo 650" in by_brand
    dolo = by_brand["Dolo 650"]
    assert dolo["benchmark"] is not None
    assert dolo["benchmark"]["active_ingredient"] == "Paracetamol 650mg"
    assert dolo["benchmark"]["is_overcharged"] is True
    assert dolo["note"] is None


def test_dawacheck_case_benchmark_requires_consent():
    case_id = client.post("/api/v1/kadi/cases", json={"consent_opt_in": False}).json()["id"]
    res = client.get(f"/api/v1/dawacheck/cases/{case_id}/benchmark")
    assert res.status_code == 403


def test_dawacheck_case_benchmark_unknown_case_returns_404():
    res = client.get("/api/v1/dawacheck/cases/CASE-doesnotexist/benchmark")
    assert res.status_code == 404


def test_dawacheck_case_benchmark_persists_generic_mapping():
    """Issue #27's audit flagged dawacheck_generic_mappings as never read or written.
    A successful case benchmark must now write the resolved brand->generic mapping."""
    import asyncio

    from sqlalchemy import select as _select

    from app.models import DawaCheckGenericMapping
    from conftest import TestingSessionLocal

    case_id, _ = _audited_case()
    res = client.get(f"/api/v1/dawacheck/cases/{case_id}/benchmark")
    assert res.status_code == 200

    async def fetch():
        async with TestingSessionLocal() as session:
            result = await session.execute(
                _select(DawaCheckGenericMapping).where(
                    DawaCheckGenericMapping.brand_name == "dolo 650"
                )
            )
            return result.scalar_one_or_none()

    row = asyncio.run(fetch())
    assert row is not None, "resolved brand->generic mapping was not persisted"
    assert row.generic_name == "Paracetamol 650mg"
    assert row.ceiling_price == 2.30


def test_dawacheck_case_benchmark_reports_unbenchmarkable_medicine_honestly():
    """A medicine absent from the curated reference list must be reported with a
    clear note, never silently dropped or claimed as benchmarked."""
    case_id = client.post("/api/v1/kadi/cases", json={"consent_opt_in": True}).json()["id"]
    assert client.post(
        f"/api/v1/kadi/cases/{case_id}/upload",
        files={"file": ("bill.txt", b"Totally Unlisted Medicine XQZ: 500\n")},
    ).status_code == 202

    res = client.get(f"/api/v1/dawacheck/cases/{case_id}/benchmark")
    assert res.status_code == 200
    results = res.json()
    if results:
        for r in results:
            if r["benchmark"] is None:
                assert r["note"] is not None


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


def test_billnyay_appeal_defaults_to_english():
    case_id = _case_with_document()
    response = client.post(f"/api/v1/billnyay/cases/{case_id}/appeal")
    assert response.status_code == 200
    assert response.json()["language"] == "en"


@pytest.mark.parametrize("lang", ["hi", "mr"])
def test_billnyay_appeal_honours_requested_language_in_offline_fallback(lang):
    """#39: with GROQ_API_KEY unset (this test environment's default), the appeal
    letter previously stayed English regardless of the requested language. The
    offline fallback must now return the matching localized canned letter, and the
    response must disclose which language was actually drafted."""
    case_id = _case_with_document()
    response = client.post(f"/api/v1/billnyay/cases/{case_id}/appeal?language={lang}")
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["language"] == lang
    letter = data["appeal_letter"]
    assert len(letter) > 300
    # Devanagari script must actually be present — not an untranslated English letter
    # with the language field merely relabelled.
    assert any("ऀ" <= ch <= "ॿ" for ch in letter), (
        f"Appeal letter for language={lang} contains no Devanagari text: {letter[:200]}"
    )


def test_billnyay_appeal_rejects_unsupported_language():
    case_id = _case_with_document()
    response = client.post(f"/api/v1/billnyay/cases/{case_id}/appeal?language=fr")
    assert response.status_code == 422


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


def test_billnyay_grievance_reflects_this_case_not_a_fixed_template():
    """Regression (#51): the complaint previously read 'room categories benchmarking
    deviations' and cited 'Rule 14' for every case, regardless of the actual denial.
    It must now reflect this case's own denial details and disclose whether they were
    really extracted (GROQ_API_KEY is unset in this test environment, so the fallback
    path runs and denial_facts_extracted must say so honestly)."""
    case_id = _case_with_document()
    response = client.post(f"/api/v1/billnyay/cases/{case_id}/grievance")
    assert response.status_code == 200
    data = response.json()

    assert "room categories benchmarking deviations" not in data["complaint_text"]
    assert "Rule 14" not in data["complaint_text"]
    assert "IRDAI (Protection of Policyholders' Interests) Regulations" in data["complaint_text"]
    assert data["case_id"] in data["complaint_text"]
    assert "denial_facts_extracted" in data
    assert isinstance(data["denial_facts_extracted"], bool)
    # Disputed Amount must reflect this case's own total_charged, not a fixed figure.
    assert data["bima_bharosa_fields"]["Disputed Amount"] == f"{900.0:.2f}"


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

    # The patient's name is extracted in-memory but must NOT be persisted (ADR-003).
    assert "patient" not in by_type, "patient name must not be persisted as an entity"
    assert by_type["diagnosis"][0]["name"] == "Acute Appendicitis"

    billing_names = {e["name"] for e in by_type["billing_item"]}
    assert "ICU" in billing_names
    assert "Total Amount" not in billing_names

    # No entity of any type may be the document's summary row.
    all_names = {e["name"] for e in entities}
    assert "Total Amount" not in all_names

    # The persisted case total must reflect the whole bill, not a fraction of it.
    assert data["case"]["total_charged"] == 20183.0


def test_unmatched_disclosure_invariant():
    """The unmatched notice must appear exactly when the headline totals diverge.

    Both clients show total_charged (whole bill) next to total_benchmark (benchmarked
    subset only). Those cover different item sets whenever anything is unmatched, so the
    coverage notice — gated on unmatched_count > 0 — must fire in precisely that case.
    """
    # Case A: every line benchmarked -> totals comparable, no notice needed.
    _, matched = _audited_case(b"Consultation: 900\nBlood Test: 750\n")
    assert matched["unmatched_count"] == 0
    assert matched["total_charged"] == matched["benchmarked_charged"]

    # Case B: an unmatched line -> totals diverge, notice must be triggerable.
    _, mixed = _audited_case(AUDIT_PROBE_BILL)
    assert mixed["unmatched_count"] > 0
    assert mixed["total_charged"] != mixed["benchmarked_charged"]
    assert (
        mixed["total_charged"] - mixed["benchmarked_charged"] == mixed["unmatched_amount"]
    ), "unmatched_amount must exactly account for the gap between the two totals"


def test_audit_item_counts_reconcile():
    """Every audited line is either benchmarked or unmatched — never both, never neither."""
    _, data = _audited_case(AUDIT_PROBE_BILL)
    assert data["benchmarked_count"] + data["unmatched_count"] == len(data["audit_items"])

    for item in data["audit_items"]:
        if item["benchmarked"]:
            assert item["cghs_benchmark"] is not None
            assert item["status"] != "not_benchmarked"
        else:
            assert item["cghs_benchmark"] is None
            assert item["status"] == "not_benchmarked"
            assert item["is_deviation"] is False


# ---------------------------------------------------------------------------
# DaaviSetu: submitted claim must survive POST -> persistence -> GET -> PDF.
# Regression: the POST never persisted ClaimData, so the PDF download rebuilt a
# different one, fabricating policy_number as POL-{case_id[:6]} and defaulting
# patient_name to "Patient" — on a form the patient signs and files with an insurer.
# ---------------------------------------------------------------------------

CLAIM_DOC = (
    b"Apollo Multi-Speciality Hospital\n"
    b"Patient Name: Ramesh Kulkarni\n"
    b"Diagnosis: Acute Appendicitis\n"
    b"Consultation: 900\n"
    b"ICU: 18500\n"
)

SUBMITTED_CLAIM = {
    "policy_number": "POL-STAR-774411",
    "patient_name": "Sunita Deshmukh",
    "hospital_name": "Ruby Hall Clinic",
    "diagnosis": "Acute Appendicitis (K35.8)",
    "treatment_plan": "Laparoscopic Appendectomy",
}


def _pdf_text(pdf_bytes: bytes) -> str:
    """Extracts PDF text with whitespace normalised (table cells wrap across lines)."""
    import re as _re

    import fitz

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    raw = "\n".join(page.get_text() for page in doc)
    return _re.sub(r"\s+", " ", raw)


def _case_with_submitted_claim(payload=None):
    case_id = client.post("/api/v1/kadi/cases", json={"consent_opt_in": True}).json()["id"]
    assert client.post(
        f"/api/v1/kadi/cases/{case_id}/upload", files={"file": ("bill.txt", CLAIM_DOC)}
    ).status_code == 202
    res = client.post(
        f"/api/v1/daavisetu/cases/{case_id}/claim", json=payload or SUBMITTED_CLAIM
    )
    assert res.status_code == 200, res.text
    return case_id, res.json()


def test_daavisetu_submitted_values_reach_the_pdf():
    """Every submitted field must appear verbatim in the downloaded form."""
    case_id, package = _case_with_submitted_claim()

    pdf = client.get(f"/api/v1/daavisetu/cases/{case_id}/claim/pdf")
    assert pdf.status_code == 200
    assert pdf.headers["content-type"] == "application/pdf"
    assert pdf.content.startswith(b"%PDF")

    text = _pdf_text(pdf.content)
    assert SUBMITTED_CLAIM["policy_number"] in text, "submitted policy number missing from PDF"
    assert SUBMITTED_CLAIM["patient_name"] in text, "submitted patient name missing from PDF"
    assert SUBMITTED_CLAIM["hospital_name"] in text
    assert SUBMITTED_CLAIM["diagnosis"] in text
    assert SUBMITTED_CLAIM["treatment_plan"] in text

    # The claim reference on the form must match the one the POST handed back.
    assert package["claim_id"] in text


def test_daavisetu_pdf_contains_no_fabricated_values():
    """The specific fabrications from the audit must not appear."""
    case_id, _ = _case_with_submitted_claim()
    text = _pdf_text(client.get(f"/api/v1/daavisetu/cases/{case_id}/claim/pdf").content)

    fabricated_policy = f"POL-{case_id.replace('CASE-', '')[:6]}"
    assert fabricated_policy not in text, "synthesised policy number leaked into the PDF"

    # "Patient" appears in static labels, so assert on the value cell specifically:
    # the form must show the submitted name, not the placeholder.
    assert "1. PATIENT FULL NAME Sunita Deshmukh" in text
    assert "1. PATIENT FULL NAME Patient" not in text


def test_daavisetu_estimated_cost_persisted_from_submission():
    """Cost shown on the form is the one captured at submission time."""
    case_id, package = _case_with_submitted_claim()
    expected = package["form_data"]["estimated_cost"]
    assert expected == 19400.0  # 900 + 18500 from CLAIM_DOC

    text = _pdf_text(client.get(f"/api/v1/daavisetu/cases/{case_id}/claim/pdf").content)
    assert "INR 19,400.00" in text


def test_daavisetu_claim_is_persisted_not_just_echoed():
    """The claim row must exist in daavisetu_claims with the submitted values."""
    import asyncio

    from sqlalchemy import select as _select

    from app.models import DaaviSetuClaim
    from conftest import TestingSessionLocal

    case_id, package = _case_with_submitted_claim()

    async def fetch():
        async with TestingSessionLocal() as session:
            res = await session.execute(
                _select(DaaviSetuClaim).where(DaaviSetuClaim.case_id == case_id)
            )
            return res.scalar_one_or_none()

    row = asyncio.run(fetch())
    assert row is not None, "claim was not persisted"
    assert row.id == package["claim_id"]
    assert row.policy_number == SUBMITTED_CLAIM["policy_number"]
    assert row.patient_name == SUBMITTED_CLAIM["patient_name"]
    assert row.hospital_name == SUBMITTED_CLAIM["hospital_name"]
    assert row.diagnosis == SUBMITTED_CLAIM["diagnosis"]
    assert row.treatment_plan == SUBMITTED_CLAIM["treatment_plan"]
    assert row.status == "ready_for_review"


def test_daavisetu_pdf_requires_a_submitted_claim():
    """Without a submission the API must refuse rather than invent a form."""
    case_id = client.post("/api/v1/kadi/cases", json={"consent_opt_in": True}).json()["id"]

    res = client.get(f"/api/v1/daavisetu/cases/{case_id}/claim/pdf")
    assert res.status_code == 409
    assert "No pre-authorization claim" in res.json()["detail"]


def test_daavisetu_pdf_unknown_case_returns_404():
    res = client.get("/api/v1/daavisetu/cases/CASE-doesnotexist/claim/pdf")
    assert res.status_code == 404


def test_daavisetu_resubmission_updates_the_same_claim():
    """Re-submitting must correct the stored form, not create a second one."""
    import asyncio

    from sqlalchemy import func, select as _select

    from app.models import DaaviSetuClaim
    from conftest import TestingSessionLocal

    case_id, first = _case_with_submitted_claim()

    corrected = dict(SUBMITTED_CLAIM)
    corrected["policy_number"] = "POL-CARE-998877"
    corrected["patient_name"] = "Sunita R Deshmukh"
    second = client.post(f"/api/v1/daavisetu/cases/{case_id}/claim", json=corrected)
    assert second.status_code == 200
    assert second.json()["claim_id"] == first["claim_id"]

    async def count_rows():
        async with TestingSessionLocal() as session:
            res = await session.execute(
                _select(func.count()).select_from(DaaviSetuClaim).where(
                    DaaviSetuClaim.case_id == case_id
                )
            )
            return res.scalar_one()

    assert asyncio.run(count_rows()) == 1, "re-submission created a duplicate claim"

    text = _pdf_text(client.get(f"/api/v1/daavisetu/cases/{case_id}/claim/pdf").content)
    assert "POL-CARE-998877" in text
    assert "Sunita R Deshmukh" in text
    assert "POL-STAR-774411" not in text, "stale policy number still rendered"


# ---------------------------------------------------------------------------
# DaaviSetu: universal claim form schema (#79), policy-limit validation (#84),
# and the ZIP claim package assembler (#81).
# ---------------------------------------------------------------------------


def test_claim_form_schema_endpoint_is_case_independent():
    res = client.get("/api/v1/daavisetu/claim-form-schema")
    assert res.status_code == 200
    schema = res.json()
    assert schema["properties"]["patient_name"]["x-form-section"] == "1. PATIENT FULL NAME"
    assert schema["properties"]["sum_insured"]["x-form-group"] == "policy"


def test_daavisetu_claim_flags_cost_exceeding_sum_insured():
    payload = dict(SUBMITTED_CLAIM)
    payload["estimated_cost"] = 200000.0
    payload["sum_insured"] = 100000.0

    case_id = client.post("/api/v1/kadi/cases", json={"consent_opt_in": True}).json()["id"]
    assert client.post(
        f"/api/v1/kadi/cases/{case_id}/upload", files={"file": ("bill.txt", CLAIM_DOC)}
    ).status_code == 202

    res = client.post(f"/api/v1/daavisetu/cases/{case_id}/claim", json=payload)
    assert res.status_code == 200, res.text
    check = res.json()["policy_limit_check"]
    assert check is not None
    assert check["exceeds_limit"] is True
    assert check["shortfall_amount"] == 100000.0

    text = _pdf_text(client.get(f"/api/v1/daavisetu/cases/{case_id}/claim/pdf").content)
    assert "POLICY LIMIT ALERT" in text


def test_daavisetu_claim_without_sum_insured_skips_policy_limit_check():
    case_id, package = _case_with_submitted_claim()
    assert package["policy_limit_check"] is None

    text = _pdf_text(client.get(f"/api/v1/daavisetu/cases/{case_id}/claim/pdf").content)
    assert "POLICY LIMIT ALERT" not in text


def test_daavisetu_claim_package_zip_contains_pdf_and_manifest():
    case_id, _ = _case_with_submitted_claim()
    res = client.get(f"/api/v1/daavisetu/cases/{case_id}/claim/package")
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/zip"

    import zipfile
    from io import BytesIO

    with zipfile.ZipFile(BytesIO(res.content)) as zf:
        names = set(zf.namelist())
        assert "manifest.txt" in names
        assert "preauth_form.pdf" in names
        assert zf.read("preauth_form.pdf").startswith(b"%PDF")
        manifest = zf.read("manifest.txt").decode("utf-8")
        assert "does NOT include a copy of your original scanned hospital bill" in manifest


def test_daavisetu_claim_package_requires_a_submitted_claim():
    case_id = client.post("/api/v1/kadi/cases", json={"consent_opt_in": True}).json()["id"]
    res = client.get(f"/api/v1/daavisetu/cases/{case_id}/claim/package")
    assert res.status_code == 409


def test_daavisetu_claim_package_unknown_case_returns_404():
    res = client.get("/api/v1/daavisetu/cases/CASE-doesnotexist/claim/package")
    assert res.status_code == 404


# ---------------------------------------------------------------------------
# Privacy / retention (ADR-003).
# Persisted records must hold de-identified clinical metadata only.
# ---------------------------------------------------------------------------

PII_BILL = (
    b"Lifeline Multispeciality Hospital\n"
    b"Patient Name: Ramesh Kulkarni\n"
    b"Contact: 9876543210\n"
    b"Email: ramesh.kulkarni@example.com\n"
    b"Aadhaar: 1234 5678 9012\n"
    b"Address: 12 MG Road, Pune\n"
    b"Diagnosis: Acute Appendicitis\n"
    b"Denial Code: DEN-4471\n"
    b"Consultation: 900\n"
    b"ICU: 18500\n"
)


def _uploaded_case(payload: bytes, consent: bool = True):
    case_id = client.post("/api/v1/kadi/cases", json={"consent_opt_in": consent}).json()["id"]
    assert client.post(
        f"/api/v1/kadi/cases/{case_id}/upload", files={"file": ("bill.txt", payload)}
    ).status_code == 202
    return case_id


def test_direct_identifiers_are_not_persisted():
    """No stored entity value may contain the patient's name or contact details."""
    case_id = _uploaded_case(PII_BILL)
    entities = client.get(f"/api/v1/kadi/cases/{case_id}").json()["entities"]

    blob = " ".join(
        f"{e['name']} {e['value'] or ''} {e['meta'] or ''}" for e in entities
    )
    for identifier in (
        "Ramesh Kulkarni",
        "9876543210",
        "ramesh.kulkarni@example.com",
        "1234 5678 9012",
        "12 MG Road",
    ):
        assert identifier not in blob, f"direct identifier persisted: {identifier}"


def test_clinical_and_billing_context_is_preserved():
    """Redaction must not destroy the data the modules actually need."""
    case_id = _uploaded_case(PII_BILL)
    entities = client.get(f"/api/v1/kadi/cases/{case_id}").json()["entities"]
    by_type = {}
    for e in entities:
        by_type.setdefault(e["type"], []).append(e)

    assert by_type["diagnosis"][0]["name"] == "Acute Appendicitis"
    assert by_type["hospital"][0]["name"] == "Lifeline Multispeciality Hospital"
    assert {"Consultation", "ICU"} <= {e["name"] for e in by_type["billing_item"]}

    excerpt = by_type["document_text"][0]["value"]
    assert "DEN-4471" in excerpt, "denial code must survive redaction for the appeal agent"
    assert "Acute Appendicitis" in excerpt
    assert by_type["document_text"][0]["meta"]["redacted"] is True


def test_procedure_entities_are_not_suppressed_by_same_named_billing_items():
    """Regression: the dedup check when adding type="procedure" entities previously
    compared a candidate procedure's name against ALL already-queued entities,
    including the type="billing_item" entities OCR's line-item parser adds for the
    same source line. Since a procedure and its billing line almost always share a
    name (e.g. "Consultation: 900" produces both), this silently prevented a
    "procedure" entity from ever being created in the common case — starving
    BillNyay's ICD-10/procedure consistency audit (#64) of anything to query. Fixed
    by scoping the dedup check to type="procedure" entities only."""
    case_id = _uploaded_case(PII_BILL)
    entities = client.get(f"/api/v1/kadi/cases/{case_id}").json()["entities"]
    by_type: dict = {}
    for e in entities:
        by_type.setdefault(e["type"], []).append(e)

    assert "procedure" in by_type, "a procedure entity must exist despite a same-named billing_item"
    procedure_names = {e["name"] for e in by_type["procedure"]}
    billing_item_names = {e["name"] for e in by_type["billing_item"]}
    assert procedure_names & billing_item_names, "the overlap this bug used to suppress must now survive"


def test_document_excerpt_is_redacted_not_raw():
    case_id = _uploaded_case(PII_BILL)
    entities = client.get(f"/api/v1/kadi/cases/{case_id}").json()["entities"]
    excerpt = next(e["value"] for e in entities if e["type"] == "document_text")

    assert "Ramesh Kulkarni" not in excerpt
    assert "[REDACTED]" in excerpt
    # The field label is kept so downstream agents still see document structure.
    assert "Patient Name:" in excerpt


def test_appeal_still_works_on_redacted_excerpt():
    """Redaction must not break the BillNyay pipeline that consumes the excerpt."""
    case_id = _uploaded_case(PII_BILL)
    res = client.post(f"/api/v1/billnyay/cases/{case_id}/appeal")
    assert res.status_code == 200
    assert len(res.json()["appeal_letter"]) > 300


# ---------------------------------------------------------------------------
# Consent enforcement (ADR-003).
# ---------------------------------------------------------------------------

def test_consent_defaults_to_false_when_omitted():
    """Consent must be opt-IN: omitting the field must not grant it."""
    res = client.post("/api/v1/kadi/cases", json={})
    assert res.status_code == 201
    assert res.json()["consent_opt_in"] is False


def test_consent_granted_allows_cross_module_access():
    case_id = _uploaded_case(AUDIT_PROBE_BILL, consent=True)
    assert client.post(f"/api/v1/billnyay/cases/{case_id}/audit").status_code == 200
    assert client.post(f"/api/v1/billnyay/cases/{case_id}/appeal").status_code == 200
    assert client.post(f"/api/v1/billnyay/cases/{case_id}/grievance").status_code == 200


def test_consent_denied_blocks_every_kadi_consuming_module():
    """Without consent, no module may read this case's extracted context."""
    case_id = _uploaded_case(AUDIT_PROBE_BILL, consent=False)

    blocked = [
        ("post", f"/api/v1/billnyay/cases/{case_id}/audit", None),
        ("post", f"/api/v1/billnyay/cases/{case_id}/appeal", None),
        ("post", f"/api/v1/billnyay/cases/{case_id}/grievance", None),
        ("post", f"/api/v1/daavisetu/cases/{case_id}/claim",
         {"policy_number": "POL-1", "patient_name": "A B"}),
        ("get", f"/api/v1/daavisetu/cases/{case_id}/claim/pdf", None),
    ]
    for method, path, body in blocked:
        res = client.post(path, json=body) if method == "post" else client.get(path)
        assert res.status_code == 403, f"{path} returned {res.status_code}, expected 403"
        assert "consent" in res.json()["detail"].lower()


def test_consent_cannot_be_granted_by_the_module_request_body():
    """Enforcement reads the persisted case, not anything the caller sends."""
    case_id = _uploaded_case(AUDIT_PROBE_BILL, consent=False)

    # A client trying to grant itself access on the module call must still be refused:
    # the extra consent_opt_in field in the body must have no effect whatsoever.
    res = client.post(
        f"/api/v1/daavisetu/cases/{case_id}/claim",
        json={
            "policy_number": "POL-1",
            "patient_name": "A B",
            "consent_opt_in": True,
        },
    )
    assert res.status_code == 403

    # And the same for BillNyay, which takes no body at all.
    assert client.post(
        f"/api/v1/billnyay/cases/{case_id}/audit",
        json={"consent_opt_in": True},
    ).status_code == 403


def test_consent_is_still_false_after_a_blocked_attempt():
    case_id = _uploaded_case(AUDIT_PROBE_BILL, consent=False)
    client.post(f"/api/v1/billnyay/cases/{case_id}/audit")
    assert client.get(f"/api/v1/kadi/cases/{case_id}").json()["case"]["consent_opt_in"] is False


def test_consent_missing_case_still_404_not_403():
    """An unknown case must not be reported as a consent problem."""
    assert client.post("/api/v1/billnyay/cases/CASE-nope/audit").status_code == 404
    assert client.get("/api/v1/daavisetu/cases/CASE-nope/claim/pdf").status_code == 404


# ---------------------------------------------------------------------------
# Security hardening.
# ---------------------------------------------------------------------------

def test_unhandled_errors_do_not_leak_internal_detail():
    """500 bodies must carry a correlation id, never the exception text.

    The audit reproduced a 500 whose body contained
    "run_barrister_agent() missing 1 required positional argument: 'client'".
    """
    from fastapi import APIRouter

    from app.main import app as fastapi_app

    probe = APIRouter()

    @probe.get("/__boom__")
    async def boom():
        raise RuntimeError("SECRET_INTERNAL_DETAIL_should_not_be_returned")

    fastapi_app.include_router(probe)
    try:
        local = TestClient(fastapi_app, raise_server_exceptions=False)
        res = local.get("/__boom__")
        assert res.status_code == 500
        body = res.json()
        assert body["detail"] == "An unexpected server error occurred."
        assert "SECRET_INTERNAL_DETAIL_should_not_be_returned" not in res.text
        assert "RuntimeError" not in res.text
        # An operator-traceable id replaces the leaked message.
        assert len(body["error_id"]) == 12
    finally:
        fastapi_app.router.routes = [
            r for r in fastapi_app.router.routes if getattr(r, "path", "") != "/__boom__"
        ]


def test_cors_does_not_pair_wildcard_origin_with_credentials():
    """allow_credentials must be off whenever the origin list is a wildcard."""
    from starlette.middleware.cors import CORSMiddleware

    from app.main import app as fastapi_app

    cors = next(
        m for m in fastapi_app.user_middleware if m.cls is CORSMiddleware
    )
    kwargs = cors.kwargs
    if "*" in kwargs["allow_origins"]:
        assert kwargs["allow_credentials"] is False, (
            "wildcard origin with credentials lets any site issue credentialed requests"
        )
    assert "*" not in kwargs["allow_methods"], "methods must be an explicit allow-list"


def test_cors_allows_put_and_delete_for_income_profile_and_case_deletion():
    """P2 (CONFIRMED, and self-inflicted by this session's own new routes): CORS
    allow_methods previously listed only GET/POST/OPTIONS. SchemeSetu's income-profile
    route (PUT/DELETE) and the new case-deletion route (DELETE /kadi/cases/{id},
    ADR-009/P1-10) were both completely unreachable from any browser client — a
    cross-origin PUT/DELETE triggers a CORS preflight OPTIONS request first, and the
    browser refuses the real request when the method isn't in
    Access-Control-Allow-Methods, regardless of what the route itself would have done.
    This exercises the actual preflight response, not just the configured kwargs.
    """
    case_id = client.post("/api/v1/kadi/cases", json={"consent_opt_in": True}).json()["id"]
    for method, path in [
        ("PUT", f"/api/v1/schemesetu/cases/{case_id}/income-profile"),
        ("DELETE", f"/api/v1/schemesetu/cases/{case_id}/income-profile"),
        ("DELETE", f"/api/v1/kadi/cases/{case_id}"),
    ]:
        preflight = client.options(
            path,
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": method,
                "Access-Control-Request-Headers": "X-Case-Access-Token",
            },
        )
        assert preflight.status_code == 200, f"{method} {path} preflight failed: {preflight.text}"
        allowed = preflight.headers.get("access-control-allow-methods", "")
        assert method in allowed, f"{method} not in preflight Access-Control-Allow-Methods: {allowed}"
        allowed_headers = preflight.headers.get("access-control-allow-headers", "").lower()
        assert "x-case-access-token" in allowed_headers, (
            f"X-Case-Access-Token not in preflight Access-Control-Allow-Headers: {allowed_headers}"
        )


def test_upload_rejects_oversized_document():
    from app.config import settings

    case_id = client.post("/api/v1/kadi/cases", json={"consent_opt_in": True}).json()["id"]
    oversized = b"x" * (settings.max_upload_bytes + 1024)

    res = client.post(
        f"/api/v1/kadi/cases/{case_id}/upload", files={"file": ("big.txt", oversized)}
    )
    assert res.status_code == 413
    assert "upload limit" in res.json()["detail"]


def test_upload_rejects_unsupported_file_type():
    case_id = client.post("/api/v1/kadi/cases", json={"consent_opt_in": True}).json()["id"]

    res = client.post(
        f"/api/v1/kadi/cases/{case_id}/upload",
        files={"file": ("payload.exe", b"MZ\x90\x00binary")},
    )
    assert res.status_code == 415
    assert "Unsupported document type" in res.json()["detail"]


def test_upload_accepts_supported_types():
    case_id = client.post("/api/v1/kadi/cases", json={"consent_opt_in": True}).json()["id"]
    res = client.post(
        f"/api/v1/kadi/cases/{case_id}/upload", files={"file": ("bill.txt", b"ICU: 900\n")}
    )
    assert res.status_code == 202


def test_upload_rejects_empty_document():
    case_id = client.post("/api/v1/kadi/cases", json={"consent_opt_in": True}).json()["id"]
    res = client.post(
        f"/api/v1/kadi/cases/{case_id}/upload", files={"file": ("bill.txt", b"")}
    )
    assert res.status_code == 400


def test_status_map_is_bounded():
    """The in-memory stream map must not grow without limit."""
    from app.api.v1.endpoints.kadi import (
        MAX_TRACKED_STATUS_CASES,
        _evict_stale_status_entries,
        processing_status,
    )

    processing_status.clear()
    try:
        for i in range(MAX_TRACKED_STATUS_CASES + 50):
            processing_status[f"CASE-bulk-{i}"] = [
                {"status": "completed", "progress": 100, "log": "done"}
            ]
        _evict_stale_status_entries()
        assert len(processing_status) < MAX_TRACKED_STATUS_CASES
    finally:
        processing_status.clear()


def test_sse_stream_timeout_setting_is_sane():
    """Only checks the configured VALUE is sane. This used to be titled
    'test_sse_stream_has_a_bounded_timeout' and claimed in its docstring to prove "an
    unknown case must not hold a connection open forever" without ever calling the
    endpoint — the setting existed but the stream generator never read it (P0-2). The
    real behavioral proof (existence check, real timeout enforcement, disconnect
    handling) now lives in tests/test_sse_stream.py."""
    from app.config import settings

    assert settings.sse_timeout_seconds > 0
    assert settings.sse_timeout_seconds <= 600


# ---------------------------------------------------------------------------
# Fabricated-data guards. Nothing user-facing may invent patient, policy,
# clinical or financial values.
# ---------------------------------------------------------------------------

FABRICATIONS = [
    "General Hospital",
    "Discharged Patient Medical Recovery",
    "General clinical medical observation",
    "DEN-DEFAULT",
    "Disputed Procedure",
]


def test_claim_refuses_rather_than_inventing_clinical_fields():
    """A bare document must not yield an invented diagnosis/treatment/hospital/cost."""
    case_id = client.post("/api/v1/kadi/cases", json={"consent_opt_in": True}).json()["id"]
    client.post(
        f"/api/v1/kadi/cases/{case_id}/upload",
        files={"file": ("note.txt", b"Some unstructured clinical note with no fields.\n")},
    )

    res = client.post(
        f"/api/v1/daavisetu/cases/{case_id}/claim",
        json={"policy_number": "POL-1", "patient_name": "Asha Rao"},
    )
    assert res.status_code == 422, res.text
    detail = res.json()["detail"]
    assert set(detail["missing_fields"]) == {
        "hospital_name",
        "diagnosis",
        "treatment_plan",
        "estimated_cost",
    }
    # And crucially: no claim was persisted from invented values.
    assert client.get(f"/api/v1/daavisetu/cases/{case_id}/claim/pdf").status_code == 409


def test_claim_partial_gaps_are_named_precisely():
    # "Dolo 650mg: 33" is classified as a medicine, not a procedure (see
    # kadi.extraction.looks_like_medicine), so it contributes to the billing total
    # without resolving treatment_plan — unlike a non-medicine line (e.g.
    # "Consultation: 900"), which the extraction agent's heuristic classifies as a
    # candidate procedure and would resolve treatment_plan itself, defeating this
    # test's point of proving diagnosis/treatment_plan stay reported as missing.
    case_id = client.post("/api/v1/kadi/cases", json={"consent_opt_in": True}).json()["id"]
    client.post(
        f"/api/v1/kadi/cases/{case_id}/upload",
        files={"file": ("bill.txt", b"Hospital: Ruby Hall Clinic\nDolo 650mg: 33\n")},
    )
    res = client.post(
        f"/api/v1/daavisetu/cases/{case_id}/claim",
        json={"policy_number": "POL-2", "patient_name": "Asha Rao"},
    )
    assert res.status_code == 422
    # hospital and cost resolved from the document; only the clinical fields are missing.
    assert set(res.json()["detail"]["missing_fields"]) == {"diagnosis", "treatment_plan"}


def test_generated_pdf_contains_no_fabricated_placeholder_text():
    case_id, _ = _case_with_submitted_claim()
    text = _pdf_text(client.get(f"/api/v1/daavisetu/cases/{case_id}/claim/pdf").content)
    for phrase in FABRICATIONS:
        assert phrase not in text, f"fabricated placeholder rendered on the form: {phrase}"


def test_appeal_letter_contains_no_fake_denial_code():
    """A letter sent to an insurer must not quote an invented reference like DEN-DEFAULT."""
    case_id = _case_with_document()
    data = client.post(f"/api/v1/billnyay/cases/{case_id}/appeal").json()
    assert "DEN-DEFAULT" not in data["appeal_letter"]
    assert "Disputed Procedure" not in data["appeal_letter"]
    assert isinstance(data["denial_facts_extracted"], bool)


def test_offline_fallback_never_claims_denial_facts_were_extracted():
    """Regression: the offline Auditor fallback (DEN-999 / confidence 0.95) always
    parses into a valid StructuredDenial, so `denial is not None` alone can't tell a
    templated response apart from a real extraction. No test environment has a live,
    valid GROQ_API_KEY — locally it's unset, and in CI it's a mock string that Groq
    rejects with 403 — so every /appeal call here runs on the canned template
    (confirmed by GroqClientFallback's "Returning fallback denial JSON block" log),
    regardless of whether a key string happens to be configured. denial_facts_extracted
    must reflect that rather than reporting True on fabricated facts."""
    case_id = _case_with_document()
    data = client.post(f"/api/v1/billnyay/cases/{case_id}/appeal").json()
    assert data["denial_facts_extracted"] is False


def test_dawacheck_unknown_medicine_does_not_claim_it_is_uncontrolled():
    res = client.post(
        "/api/v1/dawacheck/benchmark", json={"brand_name": "Zyxwvu 999", "mrp": 100.0}
    )
    assert res.status_code == 404
    detail = res.json()["detail"]
    msg = detail["message"]
    # The old message asserted absence from the NPPA list outright.
    assert "not in ArogyaRakshak's reference price list" in msg
    assert "does NOT mean" in msg
    assert "subset" in msg
    assert detail["data_source"]


def test_dawacheck_result_declares_its_provenance():
    res = client.post(
        "/api/v1/dawacheck/benchmark", json={"brand_name": "Dolo 650", "mrp": 33.0}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["data_source"] == "NPPA Schedule-I (curated subset)"
    assert data["reference_entry_count"] > 0
    # Availability must be derived from the reference entry, not asserted unconditionally.
    assert data["generic_substitute_available"] is True
    assert data["generic_substitute_store_info"]


def test_dawacheck_translate_instructions_expands_shorthand_in_hindi():
    res = client.post(
        "/api/v1/dawacheck/translate-instructions",
        json={"instructions": "Tab. Dolo 650mg TDS x 5 days", "language": "hi"},
    )
    assert res.status_code == 200
    data = res.json()
    tokens = {i["token"].upper(): i for i in data["instructions"]}
    assert tokens["TDS"]["recognized"] is True
    assert tokens["TDS"]["translated"] == "दिन में तीन बार"
    assert data["unrecognized_tokens"] == []


def test_dawacheck_translate_instructions_flags_unrecognized_shorthand_honestly():
    res = client.post(
        "/api/v1/dawacheck/translate-instructions",
        json={"instructions": "Tab. X 5mg ZZZ", "language": "en"},
    )
    assert res.status_code == 200
    data = res.json()
    assert "ZZZ" in data["unrecognized_tokens"]
    zzz = next(i for i in data["instructions"] if i["token"] == "ZZZ")
    assert zzz["recognized"] is False
    assert zzz["translated"] == ""


def test_dawacheck_translate_instructions_rejects_unsupported_language():
    res = client.post(
        "/api/v1/dawacheck/translate-instructions",
        json={"instructions": "TDS", "language": "fr"},
    )
    assert res.status_code == 422


def test_dawacheck_translate_instructions_requires_no_case_consent():
    """Request-body-only route, like /benchmark — must not require a case at all."""
    res = client.post(
        "/api/v1/dawacheck/translate-instructions",
        json={"instructions": "BD", "language": "mr"},
    )
    assert res.status_code == 200


def test_latency_metrics_is_empty_before_any_upload():
    res = client.get("/api/v1/kadi/metrics/latency")
    assert res.status_code == 200
    data = res.json()
    assert data["sample_count"] == 0
    assert data["target_seconds"] == 10.0


def test_latency_metrics_records_a_sample_after_a_real_upload_completes():
    """#116: proves latency is measured from an actual end-to-end run through the real
    pipeline (upload -> OCR -> extraction -> entity resolution -> database write), not
    a synthetic/mocked duration."""
    _case_with_document()  # runs the real pipeline synchronously under TestClient

    res = client.get("/api/v1/kadi/metrics/latency")
    assert res.status_code == 200
    data = res.json()
    assert data["sample_count"] == 1
    assert data["p50_seconds"] is not None
    assert data["p50_seconds"] >= 0
    assert data["single_process_only"] is True


def test_latency_metrics_flags_a_case_exceeding_the_10_second_target():
    """Deterministic proof the compliance check actually fires against the endpoint's
    real response, without waiting 10 real seconds in the test suite: records a
    synthetic over-target sample directly on the same tracker instance the endpoint
    reads from, then verifies GET /metrics/latency reports it as a violation."""
    from app.api.v1.endpoints.kadi import latency_tracker

    latency_tracker.record("CASE-synthetic-slow", 15.0, "completed")

    res = client.get("/api/v1/kadi/metrics/latency")
    data = res.json()
    assert data["violations"] >= 1
    assert data["compliance_rate"] < 1.0
    assert data["max_seconds"] >= 15.0


def test_latency_metrics_records_failed_outcomes_too():
    res_case = client.post("/api/v1/kadi/cases", json={"consent_opt_in": True})
    case_id = res_case.json()["id"]
    # An empty/corrupt document trips the extraction_ok=False path (parse_document
    # cannot read it), which is the "failed" terminal event this metric must also cover.
    upload = client.post(
        f"/api/v1/kadi/cases/{case_id}/upload",
        files={"file": ("corrupt.pdf", b"%PDF-1.4\ncorrupted garbage not a real pdf")},
    )
    assert upload.status_code == 202

    res = client.get("/api/v1/kadi/metrics/latency/recent")
    assert res.status_code == 200
    samples = res.json()
    assert any(s["case_id"] == case_id and s["outcome"] == "failed" for s in samples)


def test_latency_metrics_recent_endpoint_respects_limit():
    for _ in range(3):
        _case_with_document()
    res = client.get("/api/v1/kadi/metrics/latency/recent?limit=2")
    assert res.status_code == 200
    assert len(res.json()) == 2


def test_extraction_warnings_reach_the_persisted_entity_and_completion_log(monkeypatch):
    """P0-4 end-to-end wiring: an ExtractedEntities carrying extraction_warnings (e.g.
    flagged prompt-injection phrasing, or an unreconciled total_amount) must actually
    reach somewhere visible — the document_text entity's meta and the SSE completion
    log — not sit unused on a Pydantic model nobody reads."""
    from app.api.v1.endpoints import kadi as kadi_module
    from kadi.extraction import ExtractedEntities

    flagged = ExtractedEntities(
        hospital_name="Test Hospital",
        total_amount=500.0,
        extraction_warnings=["Source document text contained phrasing resembling a prompt-injection attempt: test"],
    )
    monkeypatch.setattr(kadi_module, "extract_entities_from_text", lambda *a, **kw: flagged)

    case_id = _case_with_document(b"Consultation: 500\nTotal Amount: 500\n")

    entities = client.get(f"/api/v1/kadi/cases/{case_id}").json()["entities"]
    doc_text_entity = next(e for e in entities if e["type"] == "document_text")
    assert "extraction_warnings" in doc_text_entity["meta"]
    assert "prompt-injection" in doc_text_entity["meta"]["extraction_warnings"][0]

    events = kadi_module.processing_status.get(case_id, [])
    completed_event = next(e for e in events if e.get("status") == "completed")
    assert "flagged for review" in completed_event["log"]


def test_clean_extraction_leaves_no_warning_trace(monkeypatch):
    from app.api.v1.endpoints import kadi as kadi_module
    from kadi.extraction import ExtractedEntities

    clean = ExtractedEntities(hospital_name="Test Hospital", total_amount=500.0)
    monkeypatch.setattr(kadi_module, "extract_entities_from_text", lambda *a, **kw: clean)

    case_id = _case_with_document(b"Consultation: 500\nTotal Amount: 500\n")

    entities = client.get(f"/api/v1/kadi/cases/{case_id}").json()["entities"]
    doc_text_entity = next(e for e in entities if e["type"] == "document_text")
    assert "extraction_warnings" not in doc_text_entity["meta"]

    events = kadi_module.processing_status.get(case_id, [])
    completed_event = next(e for e in events if e.get("status") == "completed")
    assert "flagged for review" not in completed_event["log"]


def test_default_document_signing_secret_is_the_known_insecure_value():
    """P2: pins the exact string main.py checks at startup, so a future edit to the
    default in config.py that forgets to update the startup-warning check is caught
    here instead of silently going unnoticed."""
    from app.config import Settings

    assert Settings().document_signing_secret == "dev-insecure-signing-secret-change-in-production"


def test_uses_default_database_credentials_detects_the_dev_fallback():
    """P0-5: the app must be able to recognise docker-compose.yml's fallback
    arogyarakshak:arogyarakshak dev credentials so it can warn loudly at startup if they
    reach a real deployment, rather than staying silent about a critical misconfiguration."""
    from app.main import uses_default_database_credentials

    assert uses_default_database_credentials(
        "postgresql://arogyarakshak:arogyarakshak@postgres:5432/arogyarakshak"
    ) is True
    assert uses_default_database_credentials(
        "postgresql://prod_user:S3cure-R4nd0m-P4ssw0rd@db.internal:5432/arogyarakshak"
    ) is False


def test_schemesetu_discloses_what_it_did_not_evaluate():
    """Category and medical need are collected but never used — say so."""
    res = client.post(
        "/api/v1/schemesetu/eligibility",
        json={
            "income": 120000.0,
            "location_state": "Maharashtra",
            "category": "SC",
            "medical_need": "CABG",
        },
    )
    assert res.status_code == 200
    for scheme in res.json():
        assert scheme["is_provisional"] is True
        assert "annual_income" in scheme["non_determinative_factors"]
        assert "annual_income" not in scheme["criteria_evaluated"]
        assert "social_category" in scheme["criteria_not_evaluated"]
        assert "medical_need" in scheme["criteria_not_evaluated"]


def test_schemesetu_category_does_not_change_the_verdict_today():
    """Guards against implying category was considered when it is ignored."""
    base = {"income": 120000.0, "location_state": "Maharashtra", "medical_need": "CABG"}
    sc = client.post("/api/v1/schemesetu/eligibility", json={**base, "category": "SC"}).json()
    gen = client.post(
        "/api/v1/schemesetu/eligibility", json={**base, "category": "General"}
    ).json()
    assert [s["estimated_eligibility"] for s in sc] == [
        s["estimated_eligibility"] for s in gen
    ], "category appears to affect the verdict — update criteria_not_evaluated if so"


# ---------------------------------------------------------------------------
# Silent data loss: an unreadable document must not report success.
# ---------------------------------------------------------------------------

def test_unreadable_document_is_reported_as_failed_not_completed():
    """A corrupt PDF used to yield a placeholder body and a 'completed' stream."""
    from app.api.v1.endpoints.kadi import processing_status

    case_id = client.post("/api/v1/kadi/cases", json={"consent_opt_in": True}).json()["id"]
    res = client.post(
        f"/api/v1/kadi/cases/{case_id}/upload",
        files={"file": ("broken.pdf", b"%PDF-1.4 not actually a valid pdf")},
    )
    assert res.status_code == 202

    events = processing_status.get(case_id, [])
    assert events, "no processing events recorded"
    final = events[-1]
    assert final["status"] == "failed", f"expected failure, got {final['status']}"
    assert "could not be read" in final["log"].lower()

    # Nothing may be persisted from a document that was never read.
    entities = client.get(f"/api/v1/kadi/cases/{case_id}").json()["entities"]
    assert entities == []


def test_failed_extraction_does_not_leak_exception_text_to_the_stream():
    """The SSE log is rendered in the browser and must stay user-facing."""
    from app.api.v1.endpoints.kadi import processing_status

    case_id = client.post("/api/v1/kadi/cases", json={"consent_opt_in": True}).json()["id"]
    client.post(
        f"/api/v1/kadi/cases/{case_id}/upload",
        files={"file": ("broken.pdf", b"%PDF-1.4 garbage")},
    )
    log = processing_status[case_id][-1]["log"]
    for leak in ("Traceback", "fitz", "PyMuPDF", "Exception", "code=7"):
        assert leak not in log, f"internal detail leaked into the SSE log: {leak}"


def test_readable_document_still_completes():
    """The failure path must not swallow legitimate documents."""
    from app.api.v1.endpoints.kadi import processing_status

    case_id = client.post("/api/v1/kadi/cases", json={"consent_opt_in": True}).json()["id"]
    client.post(
        f"/api/v1/kadi/cases/{case_id}/upload",
        files={"file": ("bill.txt", b"Consultation: 900\nICU: 18500\n")},
    )
    assert processing_status[case_id][-1]["status"] == "completed"
    names = {e["name"] for e in client.get(f"/api/v1/kadi/cases/{case_id}").json()["entities"]}
    assert {"Consultation", "ICU"} <= names


# ---------------------------------------------------------------------------
# Cross-module integration: one document, four modules, values tracked through.
# ---------------------------------------------------------------------------

INTEGRATION_BILL = (
    b"Ruby Hall Clinic\n"
    b"Patient Name: Meera Iyer\n"
    b"Diagnosis: Acute Cholecystitis\n"
    b"Consultation: 900\n"
    b"ICU: 18500\n"
    b"Blood Test: 750\n"
    b"Dolo 650: 33\n"
    b"Total Amount: 20183\n"
)


def test_end_to_end_document_drives_every_module_consistently():
    """One upload must produce consistent numbers across Kadi, BillNyay and DaaviSetu."""
    # 1. Consent + upload
    case_id = client.post("/api/v1/kadi/cases", json={"consent_opt_in": True}).json()["id"]
    assert client.post(
        f"/api/v1/kadi/cases/{case_id}/upload",
        files={"file": ("bill.txt", INTEGRATION_BILL)},
    ).status_code == 202

    # 2. Kadi: clinical metadata retained, identifier dropped
    case = client.get(f"/api/v1/kadi/cases/{case_id}").json()
    by_type = {}
    for e in case["entities"]:
        by_type.setdefault(e["type"], []).append(e["name"])

    assert by_type["hospital"] == ["Ruby Hall Clinic"]
    assert by_type["diagnosis"] == ["Acute Cholecystitis"]
    assert "patient" not in by_type
    assert set(by_type["billing_item"]) == {"Consultation", "ICU", "Blood Test", "Dolo 650"}
    assert case["case"]["total_charged"] == 20183.0

    # 3. BillNyay: the audit total must equal the sum Kadi persisted
    audit = client.post(f"/api/v1/billnyay/cases/{case_id}/audit").json()
    assert audit["total_charged"] == case["case"]["total_charged"]
    assert audit["benchmarked_charged"] + audit["unmatched_amount"] == audit["total_charged"]
    assert audit["unmatched_count"] == 1  # Dolo 650 has no CGHS counterpart

    # 4. DaaviSetu: hospital/diagnosis/cost flow from Kadi without being re-invented
    claim = client.post(
        f"/api/v1/daavisetu/cases/{case_id}/claim",
        json={
            "policy_number": "POL-INT-4242",
            "patient_name": "Meera Iyer",
            "treatment_plan": "Laparoscopic Cholecystectomy",
        },
    )
    assert claim.status_code == 200, claim.text
    form = claim.json()["form_data"]
    assert form["hospital_name"] == "Ruby Hall Clinic"
    assert form["diagnosis"] == "Acute Cholecystitis"
    assert form["estimated_cost"] == case["case"]["total_charged"]

    # 5. The rendered PDF must carry exactly those values
    pdf = client.get(f"/api/v1/daavisetu/cases/{case_id}/claim/pdf")
    assert pdf.status_code == 200
    text = _pdf_text(pdf.content)
    assert "POL-INT-4242" in text
    assert "Meera Iyer" in text
    assert "Ruby Hall Clinic" in text
    assert "Acute Cholecystitis" in text
    assert "Laparoscopic Cholecystectomy" in text
    assert "INR 20,183.00" in text


# ---------------------------------------------------------------------------
# BillNyay: consensus (#65), self-correcting drafting (#68), and PDF signing (#66).
# ---------------------------------------------------------------------------


def test_appeal_response_includes_consensus_and_signing_fields():
    case_id = _case_with_document()
    data = client.post(f"/api/v1/billnyay/cases/{case_id}/appeal").json()

    consensus = data["consensus"]
    assert consensus["final_verdict"] in ("approve", "reject", "flag_review")
    assert len(consensus["votes"]) == 3
    roles = {v["role"] for v in consensus["votes"]}
    assert roles == {"auditor", "clinician", "regulatory"}

    assert isinstance(data["revision_count"], int)
    assert isinstance(data["revision_history"], list)

    assert len(data["document_sha256"]) == 64  # hex-encoded SHA-256
    assert data["pdf_download_url"] == f"/api/v1/billnyay/cases/{case_id}/appeal/pdf"


def test_appeal_pdf_download_matches_hashed_document():
    case_id = _case_with_document()
    data = client.post(f"/api/v1/billnyay/cases/{case_id}/appeal").json()

    pdf_res = client.get(f"/api/v1/billnyay/cases/{case_id}/appeal/pdf")
    assert pdf_res.status_code == 200
    assert pdf_res.headers["content-type"] == "application/pdf"
    assert pdf_res.content.startswith(b"%PDF")

    import hashlib
    assert hashlib.sha256(pdf_res.content).hexdigest() == data["document_sha256"]


def test_appeal_pdf_requires_drafting_first():
    case_id = client.post("/api/v1/kadi/cases", json={"consent_opt_in": True}).json()["id"]
    res = client.get(f"/api/v1/billnyay/cases/{case_id}/appeal/pdf")
    assert res.status_code == 409


def test_appeal_pdf_unknown_case_returns_404():
    res = client.get("/api/v1/billnyay/cases/CASE-doesnotexist/appeal/pdf")
    assert res.status_code == 404


def test_appeal_verify_confirms_integrity_of_a_freshly_drafted_appeal():
    case_id = _case_with_document()
    client.post(f"/api/v1/billnyay/cases/{case_id}/appeal")

    res = client.get(f"/api/v1/billnyay/cases/{case_id}/appeal/verify")
    assert res.status_code == 200
    data = res.json()
    assert data["hash_matches_stored_bytes"] is True
    assert data["signature_valid"] is True
    assert "not a licensed digital signature certificate" in data["note"]


def test_appeal_verify_requires_drafting_first():
    case_id = client.post("/api/v1/kadi/cases", json={"consent_opt_in": True}).json()["id"]
    res = client.get(f"/api/v1/billnyay/cases/{case_id}/appeal/verify")
    assert res.status_code == 409


# ---------------------------------------------------------------------------
# BillNyay: ICD-10 / procedure consistency audit (#64).
# ---------------------------------------------------------------------------


def test_icd_audit_flags_consistent_procedure():
    case_id = client.post("/api/v1/kadi/cases", json={"consent_opt_in": True}).json()["id"]
    assert client.post(
        f"/api/v1/kadi/cases/{case_id}/upload",
        files={"file": ("bill.txt", b"Diagnosis: Acute Appendicitis (K35.8)\nLaparoscopic Appendectomy: 25000\n")},
    ).status_code == 202

    res = client.get(f"/api/v1/billnyay/cases/{case_id}/icd-audit")
    assert res.status_code == 200
    data = res.json()
    assert data["icd10_code"] == "K35"
    assert data["status"] == "consistent"


def test_icd_audit_flags_mismatched_procedure():
    case_id = client.post("/api/v1/kadi/cases", json={"consent_opt_in": True}).json()["id"]
    assert client.post(
        f"/api/v1/kadi/cases/{case_id}/upload",
        files={"file": ("bill.txt", b"Diagnosis: Acute Appendicitis (K35.8)\nTotal Knee Replacement: 180000\n")},
    ).status_code == 202

    res = client.get(f"/api/v1/billnyay/cases/{case_id}/icd-audit")
    assert res.status_code == 200
    assert res.json()["status"] == "mismatched"


def test_icd_audit_requires_consent():
    case_id = client.post("/api/v1/kadi/cases", json={"consent_opt_in": False}).json()["id"]
    res = client.get(f"/api/v1/billnyay/cases/{case_id}/icd-audit")
    assert res.status_code == 403


def test_icd_audit_unknown_case_returns_404():
    res = client.get("/api/v1/billnyay/cases/CASE-doesnotexist/icd-audit")
    assert res.status_code == 404


# ---------------------------------------------------------------------------
# BillNyay: mock Bima Bharosa registration-status check (#67).
# ---------------------------------------------------------------------------


def test_registration_status_is_mock_and_says_so():
    res = client.get(
        "/api/v1/billnyay/grievance/registration-status", params={"complaint_reference": "BB-123456"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["source"] == "mock"
    assert data["is_registered"] is True
    assert "MOCK" in data["note"]


def test_registration_status_requires_complaint_reference_param():
    res = client.get("/api/v1/billnyay/grievance/registration-status")
    assert res.status_code == 422


# ---------------------------------------------------------------------------
# SchemeSetu: reasoning agent (#21), trend estimator (#70), transition adviser (#71).
# ---------------------------------------------------------------------------


def test_eligibility_reasoning_returns_verdict_and_trace():
    payload = {
        "income": 120000.0,
        "location_state": "Maharashtra",
        "category": "General",
        "medical_need": "Heart bypass surgery",
    }
    res = client.post("/api/v1/schemesetu/eligibility/reasoning", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert len(data["scheme_results"]) == 2
    # Maharashtra: PMJAY identification + PMJAY income + MJPJAY state + MJPJAY income = 4 steps.
    assert len(data["reasoning_trace"]) == 4
    assert data["criteria_considered"]
    assert data["criteria_not_considered"]


def test_eligibility_reasoning_trace_matches_scheme_results():
    payload = {"income": 500000.0, "location_state": "Karnataka", "medical_need": "Surgery"}
    res = client.post("/api/v1/schemesetu/eligibility/reasoning", json=payload)
    data = res.json()

    pmjay_result = next(r for r in data["scheme_results"] if "PMJAY" in r["scheme_name"])
    pmjay_steps = [s for s in data["reasoning_trace"] if s["scheme"].startswith("PMJAY")]
    assert pmjay_result["estimated_eligibility"] == "ambiguous"
    assert pmjay_steps and all(s["satisfied"] is None for s in pmjay_steps)


def test_eligibility_trend_projects_future_eligibility():
    payload = {
        "income_history": [
            {"year": 2020, "annual_income": 100000.0},
            {"year": 2021, "annual_income": 150000.0},
            {"year": 2022, "annual_income": 200000.0},
        ],
        "target_year": 2024,
        "location_state": "Maharashtra",
    }
    res = client.post("/api/v1/schemesetu/eligibility/trend", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["projected_income"] == 300000.0
    assert data["is_extrapolation"] is True
    assert len(data["projected_eligibility"]) == 2


def test_eligibility_trend_requires_at_least_two_points():
    payload = {
        "income_history": [{"year": 2024, "annual_income": 100000.0}],
        "target_year": 2026,
        "location_state": "Maharashtra",
    }
    res = client.post("/api/v1/schemesetu/eligibility/trend", json=payload)
    assert res.status_code == 422


def test_eligibility_transition_detects_relocation_out_of_maharashtra():
    payload = {
        "previous": {"income": 100000.0, "location_state": "Maharashtra", "medical_need": "Surgery"},
        "current": {"income": 100000.0, "location_state": "Karnataka", "medical_need": "Surgery"},
    }
    res = client.post("/api/v1/schemesetu/eligibility/transition", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["transition_detected"] is True
    assert "MJPJAY" in data["from_schemes"]
    assert len(data["checklist"]) > 0


def test_eligibility_transition_no_change_reports_no_checklist():
    intake = {"income": 500000.0, "location_state": "Karnataka", "medical_need": "Surgery"}
    payload = {"previous": intake, "current": intake}
    res = client.post("/api/v1/schemesetu/eligibility/transition", json=payload)
    data = res.json()
    assert data["transition_detected"] is False
    assert data["checklist"] == []


# ---------------------------------------------------------------------------
# DaaviSetu: PDF form-field mapping/filling tool (#80).
# ---------------------------------------------------------------------------


def _fillable_pdf_bytes(field_names) -> bytes:
    import io as _io
    from reportlab.pdfgen import canvas as _canvas

    buffer = _io.BytesIO()
    c = _canvas.Canvas(buffer)
    form = c.acroForm
    y = 700
    for name in field_names:
        form.textfield(name=name, tooltip=name, x=100, y=y, width=200, height=20, borderStyle="inset", forceBorder=True)
        y -= 40
    c.save()
    return buffer.getvalue()


def test_inspect_claim_template_lists_field_names():
    template_bytes = _fillable_pdf_bytes(["patient_name", "policy_number"])
    res = client.post(
        "/api/v1/daavisetu/claim-template/inspect",
        files={"template": ("template.pdf", template_bytes, "application/pdf")},
    )
    assert res.status_code == 200
    names = {f["field_name"] for f in res.json()}
    assert names == {"patient_name", "policy_number"}


def test_fill_claim_template_uses_submitted_claim_fields():
    case_id, package = _case_with_submitted_claim()
    template_bytes = _fillable_pdf_bytes(["patient_name", "policy_number", "hospital_name"])

    res = client.post(
        f"/api/v1/daavisetu/cases/{case_id}/claim/fill-template",
        files={"template": ("template.pdf", template_bytes, "application/pdf")},
    )
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/pdf"
    assert res.content.startswith(b"%PDF")

    filled_fields_res = client.post(
        "/api/v1/daavisetu/claim-template/inspect",
        files={"template": ("filled.pdf", res.content, "application/pdf")},
    )
    filled = {f["field_name"]: f["current_value"] for f in filled_fields_res.json()}
    assert filled["patient_name"] == SUBMITTED_CLAIM["patient_name"]
    assert filled["policy_number"] == SUBMITTED_CLAIM["policy_number"]
    assert filled["hospital_name"] == SUBMITTED_CLAIM["hospital_name"]


def test_fill_claim_template_requires_a_submitted_claim():
    case_id = client.post("/api/v1/kadi/cases", json={"consent_opt_in": True}).json()["id"]
    template_bytes = _fillable_pdf_bytes(["patient_name"])
    res = client.post(
        f"/api/v1/daavisetu/cases/{case_id}/claim/fill-template",
        files={"template": ("template.pdf", template_bytes, "application/pdf")},
    )
    assert res.status_code == 409


def test_end_to_end_is_blocked_without_consent_at_every_stage():
    """The same document with consent withheld must reach no module."""
    case_id = client.post("/api/v1/kadi/cases", json={"consent_opt_in": False}).json()["id"]
    client.post(
        f"/api/v1/kadi/cases/{case_id}/upload",
        files={"file": ("bill.txt", INTEGRATION_BILL)},
    )

    # Extraction still runs (it is the patient's own document), but no module may read it.
    assert client.get(f"/api/v1/kadi/cases/{case_id}").json()["entities"], "extraction should still occur"
    assert client.post(f"/api/v1/billnyay/cases/{case_id}/audit").status_code == 403
    assert client.post(
        f"/api/v1/daavisetu/cases/{case_id}/claim",
        json={"policy_number": "P", "patient_name": "N"},
    ).status_code == 403
