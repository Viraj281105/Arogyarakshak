"""
Phase 3 end-to-end API tests.

Entity resolution (#31), feedback calibration (#88), the case graph (#86), ABDM FHIR import
(#54), auto-triggered module insights (#32), consent-bounded scheme triggers (#92) and
outcome estimation (#90). Uses the SQLite test database from conftest. Every document and
the FHIR bundle are synthetic.
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path

from sqlalchemy import select

from app.api.v1.endpoints.kadi import processing_status
from app.background import get_background_session
from app.config import settings
from app.main import app, redact_database_url
from app.models import KadiModuleInsight, KadiResolutionDecision, SchemeSetuCaseProfile
from tests.auth_test_client import AuthAwareTestClient

# ADR-009: see tests/auth_test_client.py — carries each case's access token to this
# client's later requests for that case automatically.
client = AuthAwareTestClient(app)

FHIR_FIXTURE = (
    Path(__file__).resolve().parents[3]
    / "packages" / "kadi" / "tests" / "fixtures" / "abdm" / "discharge_summary_synthetic.json"
)

MERGE_BILL = (
    b"Lifeline Multispeciality Hospital\n"
    b"Diagnosis: Acute Appendicitis\n"
    b"Appendectomy: 45000\n"
    b"Paracetamol 650mg: 20\n"
)
MERGE_PRESCRIPTION = (
    b"Lifeline Multi Speciality Hospital\n"
    b"Diagnosis: Acute Appendicitis\n"
    b"Paracetmol 650mg: 25\n"
)
ASK_DOC_A = b"City Care Hospital\nDiagnosis: Chest infection\nAmoxicillin 500 mg: 120\n"
ASK_DOC_B = b"City Care Hospital\nDiagnosis: Chest infection\nAmpicillin 500 mg: 90\n"
CONFIRM_DOC_A = b"Sunrise Nursing Home\nDiagnosis: Type 2 diabetes mellitus\nMetformin 500 mg: 40\n"
CONFIRM_DOC_B = b"Sunrise Nursing Home\nDiagnosis: Type 2 diabetes mellitus\nMetformin Hydrochloride 500 mg: 45\n"
CROCIN_DOC_A = b"Crocin 650 mg: 30\n"
CROCIN_DOC_B = b"Crosin 650 mg: 30\n"
AUDIT_BILL = (
    b"Lifeline Multispeciality Hospital\n"
    b"Diagnosis: Acute Appendicitis\n"
    b"Consultation: 900\n"
    b"ICU: 18500\n"
    b"Dolo 650: 33\n"
)


def _case(consent: bool = True) -> str:
    return client.post("/api/v1/kadi/cases", json={"consent_opt_in": consent}).json()["id"]


def _upload(case_id: str, payload: bytes, filename: str = "bill.txt"):
    return client.post(f"/api/v1/kadi/cases/{case_id}/upload", files={"file": (filename, payload)})


def _entities(case_id: str, entity_type: str = None):
    entities = client.get(f"/api/v1/kadi/cases/{case_id}").json()["entities"]
    return [e for e in entities if entity_type is None or e["type"] == entity_type]


def _decisions(case_id: str, status: str):
    return client.get(f"/api/v1/kadi/cases/{case_id}/resolutions", params={"status": status}).json()


def _feedback(case_id: str, decision_id: str, same_entity: bool):
    return client.post(
        f"/api/v1/kadi/cases/{case_id}/resolutions/{decision_id}/feedback", json={"same_entity": same_entity}
    )


def _insights(case_id: str):
    return client.get(f"/api/v1/kadi/cases/{case_id}/insights")


def _with_session(fn):
    async def runner():
        async with get_background_session() as session:
            return await fn(session)

    return asyncio.run(runner())


def _import_bundle(case_id: str, payload: bytes):
    return client.post(
        f"/api/v1/kadi/cases/{case_id}/abdm/import", content=payload, headers={"Content-Type": "application/json"}
    )


# --- Duplicate documents and entity resolution (#31) --------------------------

def test_reuploading_the_same_document_adds_nothing():
    case_id = _case()
    assert _upload(case_id, MERGE_BILL).status_code == 202
    before = client.get(f"/api/v1/kadi/cases/{case_id}").json()

    second = _upload(case_id, MERGE_BILL, filename="bill-copy.txt")
    assert second.status_code == 200
    assert second.json()["status"] == "duplicate"

    after = client.get(f"/api/v1/kadi/cases/{case_id}").json()
    assert len(after["entities"]) == len(before["entities"])
    assert after["case"]["total_charged"] == before["case"]["total_charged"] == 45020.0
    assert processing_status[case_id][-1]["duplicate_document"] is True


def test_spelling_variants_across_documents_merge_with_provenance():
    case_id = _case()
    _upload(case_id, MERGE_BILL, "bill.txt")
    _upload(case_id, MERGE_PRESCRIPTION, "prescription.txt")

    assert [e["status"] for e in processing_status[case_id]] == [
        "upload_received", "ocr_start", "extraction_start", "database_write",
        "entity_resolution", "module_checks", "completed",
    ]

    [hospital] = _entities(case_id, "hospital")
    mentions = hospital["meta"]["mentions"]
    assert {m["source_file"] for m in mentions} == {"bill.txt", "prescription.txt"}
    assert {m["name"] for m in mentions} == {"Lifeline Multispeciality Hospital", "Lifeline Multi Speciality Hospital"}

    assert len(_entities(case_id, "diagnosis")) == 1
    [medicine] = _entities(case_id, "medicine")
    assert medicine["name"] == "Paracetamol 650mg"
    # Bill lines are never merged: identical lines can be double billing.
    assert len(_entities(case_id, "billing_item")) == 3
    assert client.get(f"/api/v1/kadi/cases/{case_id}").json()["case"]["total_charged"] == 45045.0

    merged = {(d["entity_type"], d["mention_name"], d["candidate_name"]) for d in _decisions(case_id, "auto_merged")}
    assert ("medicine", "Paracetmol 650mg", "Paracetamol 650mg") in merged
    assert ("hospital", "Lifeline Multi Speciality Hospital", "Lifeline Multispeciality Hospital") in merged
    # An identical diagnosis merges silently; there is nothing for the user to dispute.
    assert all(entity_type != "diagnosis" for entity_type, _, _ in merged)


def _ask_case(doc_a=ASK_DOC_A, doc_b=ASK_DOC_B):
    case_id = _case()
    _upload(case_id, doc_a, "a.txt")
    _upload(case_id, doc_b, "b.txt")
    [decision] = _decisions(case_id, "pending")
    return case_id, decision


def test_uncertain_match_is_kept_separate_and_asked():
    case_id, decision = _ask_case()
    assert decision["action"] == "ASK"
    assert (decision["mention_name"], decision["candidate_name"]) == ("Ampicillin 500 mg", "Amoxicillin 500 mg")
    assert 0.70 <= decision["confidence"] < 0.90
    signals = {s["signal"]: s for s in decision["signals"]}
    assert set(signals) == {"lexical", "phonetic", "semantic"}
    assert signals["semantic"]["status"] == "UNAVAILABLE"
    assert len(_entities(case_id, "medicine")) == 2


def test_rejecting_keeps_both_and_cannot_be_answered_twice():
    case_id, decision = _ask_case()
    response = _feedback(case_id, decision["id"], False)
    assert response.status_code == 200
    body = response.json()
    assert body["decision"]["status"] == "rejected"
    assert body["decision"]["feedback_same_entity"] is False
    assert {c["scope"] for c in body["calibration"]} == {"all_types", "medicine"}
    assert {c["status"] for c in body["calibration"]} == {"INSUFFICIENT_EVIDENCE"}
    assert len(_entities(case_id, "medicine")) == 2

    assert _feedback(case_id, decision["id"], True).status_code == 409


def test_confirming_folds_the_mention_into_the_existing_entity():
    case_id, decision = _ask_case(CONFIRM_DOC_A, CONFIRM_DOC_B)
    assert _feedback(case_id, decision["id"], True).json()["decision"]["status"] == "confirmed"

    [medicine] = _entities(case_id, "medicine")
    assert medicine["id"] == decision["candidate_entity_id"]
    assert {m["name"] for m in medicine["meta"]["mentions"]} == {"Metformin 500 mg", "Metformin Hydrochloride 500 mg"}


def test_feedback_for_a_decision_in_another_case_is_not_found():
    _, decision = _ask_case()
    other = _case()
    assert _feedback(other, decision["id"], True).status_code == 404


def test_disputed_automatic_merge_is_split_back_out():
    case_id = _case()
    _upload(case_id, MERGE_BILL, "bill.txt")
    _upload(case_id, MERGE_PRESCRIPTION, "prescription.txt")
    [auto] = [d for d in _decisions(case_id, "auto_merged") if d["entity_type"] == "medicine"]

    assert _feedback(case_id, auto["id"], False).json()["decision"]["status"] == "split"

    medicines = {m["name"]: m for m in _entities(case_id, "medicine")}
    assert set(medicines) == {"Paracetamol 650mg", "Paracetmol 650mg"}
    restored = medicines["Paracetmol 650mg"]
    assert restored["meta"]["split_from"] == auto["candidate_entity_id"]
    assert restored["meta"]["source_file"] == "prescription.txt"
    original_mentions = medicines["Paracetamol 650mg"]["meta"].get("mentions", [])
    assert "Paracetmol 650mg" not in {m["name"] for m in original_mentions}


# --- Feedback calibration (#88) -----------------------------------------------

def _seed_labeled_decisions(case_id, samples):
    async def seed(session):
        for i, (confidence, same) in enumerate(samples):
            session.add(
                KadiResolutionDecision(
                    id=f"RES-SEED-{i}",
                    case_id=case_id,
                    entity_type="medicine",
                    action="ASK",
                    status="confirmed" if same else "rejected",
                    source="upload",
                    candidate_entity_id="ENT-SEED",
                    candidate_name="seed",
                    mention_payload={"name": "seed"},
                    confidence=confidence,
                    signals=[],
                    reasons=[],
                    thresholds={},
                    feedback_same_entity=same,
                    feedback_at=datetime.utcnow(),
                )
            )
        await session.commit()

    _with_session(seed)


def test_default_thresholds_merge_a_close_spelling_variant():
    case_id = _case()
    _upload(case_id, CROCIN_DOC_A, "a.txt")
    _upload(case_id, CROCIN_DOC_B, "b.txt")
    [auto] = [d for d in _decisions(case_id, "auto_merged") if d["mention_name"] == "Crosin 650 mg"]
    assert auto["thresholds"]["source"] == "default_uncalibrated"


def test_feedback_recalibrates_thresholds_and_later_decisions_use_them():
    seed_case = _case()
    _seed_labeled_decisions(
        seed_case,
        [(0.95, True)] * 15 + [(0.85, True)] * 10 + [(0.75, True)] * 5 + [(0.80, False)] * 5 + [(0.72, False)] * 5,
    )
    assert client.get("/api/v1/kadi/resolution/calibration").json()["active"] == {}

    case_id, decision = _ask_case()  # Ampicillin vs Amoxicillin, answered "different"
    body = _feedback(case_id, decision["id"], False).json()
    assert {c["status"] for c in body["calibration"]} == {"CALIBRATED"}
    # 0.8583 (the rejected pair) now sits between true matches, so precision needs >= 0.95;
    # every true match scores >= 0.75. Both thresholds move by at most one 0.05 step.
    assert {(c["merge_threshold"], c["ask_threshold"]) for c in body["calibration"]} == {(0.95, 0.75)}

    calibration = client.get("/api/v1/kadi/resolution/calibration").json()
    assert calibration["labeled_decisions"] == 41
    assert calibration["active"]["medicine"]["merge"] == 0.95
    assert "Not RLHF" in calibration["method"]

    later = _case()
    _upload(later, CROCIN_DOC_A, "a.txt")
    _upload(later, CROCIN_DOC_B, "b.txt")
    [pending] = [d for d in _decisions(later, "pending") if d["mention_name"] == "Crosin 650 mg"]
    assert pending["action"] == "ASK"  # merged under the defaults, asked under calibration
    assert pending["thresholds"]["source"] == "feedback_calibrated"
    assert pending["thresholds"]["merge"] == 0.95


# --- Case knowledge graph (#86) -----------------------------------------------

def test_case_graph_links_the_stay_entities_and_bill_lines_with_evidence():
    case_id = _case()
    _upload(case_id, MERGE_BILL, "bill.txt")
    graph = client.get(f"/api/v1/kadi/cases/{case_id}/graph").json()

    assert graph["nodes"][0]["kind"] == "hospital_stay"
    assert graph["nodes"][0]["attributes"]["dates_status"] == "UNKNOWN"
    assert all(edge["evidence"] for edge in graph["edges"])
    assert "document_text" not in {n["kind"] for n in graph["nodes"]}

    labels = {n["id"]: n["label"] for n in graph["nodes"]}
    billed_as = {(labels[e["source"]], labels[e["target"]]) for e in graph["edges"] if e["relation"] == "BILLED_AS"}
    assert ("Appendectomy", "Appendectomy") in billed_as
    assert ("Paracetamol 650mg", "Paracetamol 650mg") in billed_as


def test_pending_resolution_appears_as_possibly_same_as():
    case_id, decision = _ask_case()
    graph = client.get(f"/api/v1/kadi/cases/{case_id}/graph").json()
    [edge] = [e for e in graph["edges"] if e["relation"] == "POSSIBLY_SAME_AS"]
    assert (edge["source"], edge["target"]) == (decision["mention_entity_id"], decision["candidate_entity_id"])


def test_graph_for_unknown_case_is_not_found():
    assert client.get("/api/v1/kadi/cases/CASE-missing/graph").status_code == 404


# --- ABDM / FHIR import (#54) -------------------------------------------------

def test_abdm_import_requires_consent():
    case_id = _case(consent=False)
    assert _import_bundle(case_id, FHIR_FIXTURE.read_bytes()).status_code == 403
    assert _entities(case_id) == []


def test_abdm_records_merge_into_existing_case_context():
    case_id = _case()
    _upload(case_id, MERGE_BILL, "bill.txt")

    response = _import_bundle(case_id, FHIR_FIXTURE.read_bytes())
    assert response.status_code == 200
    body = response.json()
    assert body["duplicate"] is False
    assert body["record_types"] == ["Discharge Summary"]
    assert body["dropped_for_privacy"] == {"Patient": 1, "Practitioner": 1}
    assert (body["admission_date"], body["discharge_date"]) == ("2026-08-02", "2026-08-05")

    [diagnosis] = _entities(case_id, "diagnosis")
    assert {m["source"] for m in diagnosis["meta"]["mentions"]} == {"kadi_extraction", "abdm_fhir"}
    [hospital] = _entities(case_id, "hospital")
    assert hospital["meta"]["mentions"][-1]["source"] == "abdm_fhir"
    [procedure] = _entities(case_id, "procedure")
    assert {m["name"] for m in procedure["meta"]["mentions"]} == {"Appendectomy", "Appendicectomy"}
    assert "Pantoprazole 40 mg" in {m["name"] for m in _entities(case_id, "medicine")}

    blob = json.dumps(client.get(f"/api/v1/kadi/cases/{case_id}").json(), ensure_ascii=False)
    for identifier in ("Synthetic Test Patient", "9000000000", "91-0000-0000-0000", "Dr Synthetic Example"):
        assert identifier not in blob

    graph = client.get(f"/api/v1/kadi/cases/{case_id}/graph").json()
    assert graph["nodes"][0]["attributes"]["admission_date"] == "2026-08-02"

    count = len(_entities(case_id))
    again = _import_bundle(case_id, FHIR_FIXTURE.read_bytes()).json()
    assert again["duplicate"] is True
    assert len(_entities(case_id)) == count


def test_abdm_dates_never_overwrite_recorded_dates():
    case_id = _case()
    _import_bundle(case_id, FHIR_FIXTURE.read_bytes())

    bundle = json.loads(FHIR_FIXTURE.read_text(encoding="utf-8"))
    bundle["id"] = "synthetic-discharge-2"
    bundle["entry"][3]["resource"]["period"] = {"start": "2026-09-01", "end": "2026-09-03"}
    body = _import_bundle(case_id, json.dumps(bundle).encode()).json()
    assert any("the recorded date was kept" in w for w in body["warnings"])

    graph = client.get(f"/api/v1/kadi/cases/{case_id}/graph").json()
    assert graph["nodes"][0]["attributes"]["admission_date"] == "2026-08-02"


def test_abdm_import_rejects_malformed_and_oversized_payloads(monkeypatch):
    case_id = _case()
    assert _import_bundle(case_id, b"{not json").status_code == 422
    rejected = _import_bundle(case_id, json.dumps({"resourceType": "Patient"}).encode())
    assert rejected.status_code == 422
    assert "not a FHIR Bundle" in rejected.json()["detail"]["message"]

    monkeypatch.setattr(settings, "max_upload_bytes", 100)
    assert _import_bundle(case_id, FHIR_FIXTURE.read_bytes()).status_code == 413
    assert _entities(case_id) == []


# --- Auto-triggered module insights (#32) -------------------------------------

def test_auto_triggered_insights_match_the_module_routes():
    case_id = _case()
    _upload(case_id, AUDIT_BILL)
    assert "module check(s) ran automatically" in processing_status[case_id][-1]["log"]

    body = _insights(case_id).json()
    insights = {i["module_check"]: i for i in body["insights"]}
    readiness = {r["module_check"]: r for r in body["readiness"]}

    audit = client.post(f"/api/v1/billnyay/cases/{case_id}/audit").json()
    summary = insights["billnyay_audit"]["summary"]
    assert insights["billnyay_audit"]["status"] == "COMPLETED"
    assert insights["billnyay_audit"]["trigger"] == "document_processed"
    for key in ("total_charged", "benchmarked_count", "deviations_count", "potential_savings", "unmatched_count"):
        assert summary[key] == audit[key]

    benchmarks = client.get(f"/api/v1/dawacheck/cases/{case_id}/benchmark").json()
    dawa = insights["dawacheck_benchmark"]["summary"]
    assert dawa["medicines"] == len(benchmarks) >= 1
    assert dawa["benchmarked"] == sum(1 for r in benchmarks if r["benchmark"])

    icd = client.get(f"/api/v1/billnyay/cases/{case_id}/icd-audit").json()
    assert insights["billnyay_icd_audit"]["summary"]["status"] == icd["status"]

    assert readiness["daavisetu_claim"]["auto_run"] is False
    assert "daavisetu_claim" not in insights
    assert readiness["schemesetu_eligibility"]["missing_context"] == ["income_profile"]


def test_without_consent_nothing_is_auto_triggered():
    case_id = _case(consent=False)
    _upload(case_id, AUDIT_BILL)
    assert _insights(case_id).status_code == 403
    assert "module check" not in processing_status[case_id][-1]["log"]

    async def rows(session):
        result = await session.execute(select(KadiModuleInsight).where(KadiModuleInsight.case_id == case_id))
        return result.scalars().all()

    assert _with_session(rows) == []


# --- Consent-bounded scheme recommendation trigger (#92) ----------------------

def _profile_url(case_id):
    return f"/api/v1/schemesetu/cases/{case_id}/income-profile"


def test_income_profile_requires_consent_and_stores_nothing_without_it():
    case_id = _case(consent=False)
    response = client.put(_profile_url(case_id), json={"annual_income_inr": 120000, "state": "Maharashtra"})
    assert response.status_code == 403
    assert _with_session(lambda s: s.get(SchemeSetuCaseProfile, case_id)) is None


def test_first_income_profile_triggers_background_eligibility():
    case_id = _case()
    _upload(case_id, MERGE_BILL)

    saved = client.put(_profile_url(case_id), json={"annual_income_inr": 120000, "state": "Maharashtra"}).json()
    assert saved["trigger"]["status"] == "FIRE"
    assert [m["short_name"] for m in saved["trigger"]["newly_applicable"]] == ["PMJAY", "MJPJAY"]
    assert saved["trigger"]["income_role"] == "NON_DETERMINATIVE"
    assert saved["background_eligibility"] == "queued"

    insight = {i["module_check"]: i for i in _insights(case_id).json()["insights"]}["schemesetu_eligibility"]
    assert insight["status"] == "COMPLETED"
    assert insight["trigger"] == "income_profile_updated"
    assert insight["summary"]["non_determinative_factors"] == ["annual_income"]
    assert "income_threshold_provenance" not in insight["summary"]
    direct = client.post(
        f"/api/v1/schemesetu/cases/{case_id}/eligibility", json={"income": 120000, "location_state": "Maharashtra"}
    ).json()
    assert [(s["scheme_name"], s["estimated_eligibility"]) for s in insight["summary"]["schemes"]] == [
        (r["scheme_name"], r["estimated_eligibility"]) for r in direct
    ]

    # Income is non-determinative: even a large change re-runs nothing.
    again = client.put(_profile_url(case_id), json={"annual_income_inr": 900000, "state": "Maharashtra"}).json()
    assert again["trigger"]["status"] == "NO_CHANGE"
    assert again["background_eligibility"] == "not_triggered"
    assert client.get(_profile_url(case_id)).json()["annual_income_inr"] == 900000

    assert client.delete(_profile_url(case_id)).status_code == 204
    assert client.get(_profile_url(case_id)).status_code == 404
    assert "schemesetu_eligibility" not in {i["module_check"] for i in _insights(case_id).json()["insights"]}


def test_income_trigger_without_medical_context_is_not_ready():
    case_id = _case()
    saved = client.put(_profile_url(case_id), json={"annual_income_inr": 90000, "state": "Karnataka"}).json()
    assert saved["background_eligibility"] == "not_ready"
    assert saved["missing_context"] == ["diagnosis or procedure"]
    insight = {i["module_check"]: i for i in _insights(case_id).json()["insights"]}["schemesetu_eligibility"]
    assert (insight["status"], insight["missing_context"]) == ("NOT_READY", ["diagnosis or procedure"])


def test_income_profile_input_is_validated():
    case_id = _case()
    assert client.put(_profile_url(case_id), json={"annual_income_inr": -5, "state": "MH"}).status_code == 422
    assert client.put(_profile_url(case_id), json={"annual_income_inr": 5000, "state": ""}).status_code == 422


# --- Outcome estimation (#90) and disclosures ---------------------------------

def test_outcome_estimate_refuses_without_historical_data():
    body = client.post("/api/v1/billnyay/outcome-estimate", json={"dispute_category": "PED_NON_DISCLOSURE"}).json()
    assert body["status"] == "INSUFFICIENT_EVIDENCE"
    assert body["probability_favourable"] is None
    assert body["interval_95"] is None
    assert body["admissibility_checks"] == "UNEVALUATED"


def test_bimanyay_analysis_discloses_the_heuristic_probability_basis():
    body = client.post(
        "/api/v1/bimanyay/analyze",
        json={
            "policy_number": "POL-SYNTH-1",
            "insurer_name": "Synthetic Insurer",
            "policy_age_years": 6,
            "claimed_amount": 100000,
            "denied_or_deducted_amount": 100000,
            "denial_category": "PED_NON_DISCLOSURE",
            "denial_reason_raw": "Pre-existing disease not disclosed",
            "diagnosis": "Type 2 diabetes mellitus",
        },
    ).json()
    assert body["probability_basis"] == "HEURISTIC_PRIOR_NOT_HISTORICAL"


def test_database_url_password_is_masked_for_logging():
    masked = redact_database_url("postgresql://arogya:s3cret-pass@db:5432/arogyarakshak")
    assert "s3cret-pass" not in masked
    assert "***" in masked
