"""Demo kit controls: status, reset and scenario loading (demo mode only).

A judge demo must recover from mistakes without touching real data: reset removes only
cases that hold a committed synthetic demo document, restores the demo safety rules and
rotates demo credentials; it is refused outside demo mode, under APP_ENV=production,
without the governance key, and without the typed confirmation.
"""

import asyncio
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.clinical import demo_control
from app.config import Settings, settings
from tests.clinical_helpers import ADMIN_KEY, K, admin, client, rh

DOCS = Path(__file__).resolve().parents[3] / "demo" / "documents"
CONFIRM = {"confirm": "RESET DEMO"}


@pytest.fixture
def demo(monkeypatch):
    monkeypatch.setattr(settings, "clinical_governance_admin_key", ADMIN_KEY)
    monkeypatch.setattr(settings, "clinical_demo_mode", True)
    monkeypatch.setattr(settings, "groq_api_key", "")  # deterministic extraction


def _load(scenario):
    res = client.post(f"{K}/clinical-demo/scenarios/{scenario}", headers=admin())
    assert res.status_code == 200, res.text
    body = res.json()
    client._case_tokens[body["case_id"]] = body["access_token"]
    return body


def _case_exists(case_id):
    return client.get(f"{K}/cases/{case_id}").status_code == 200


# --- Guards -----------------------------------------------------------------------------


def test_status_is_public_and_honest_when_demo_mode_is_off(monkeypatch):
    monkeypatch.setattr(settings, "clinical_demo_mode", False)
    body = client.get(f"{K}/clinical-demo/status").json()
    assert body["demo_mode"] is False and body["banner"] is None
    assert body["scenarios"] == [] and body["simulated"] == []
    assert body["governance_configured"] is False, "nothing about the governance key is disclosed"


def test_status_in_demo_mode_says_what_is_simulated(demo):
    body = client.get(f"{K}/clinical-demo/status").json()
    assert body["demo_mode"] is True
    assert "DEMO MODE" in body["banner"] and "synthetic" in body["banner"]
    items = {s["item"]: s for s in body["simulated"]}
    assert items["Scenario C OCR confidences and extraction"]["status"] == "SIMULATED"
    assert items["Reviewer personas and their verification"]["status"] == "SIMULATED"
    # Without a Groq key the extraction line says it is rule-based, not "AI".
    assert items["Entity extraction"]["status"] == "REAL (rule-based)"
    assert [s["id"] for s in body["scenarios"]] == ["A", "B", "C", "D", "E"]
    assert all(s["actions"] and s["expected"] and s["starting_state"] for s in body["scenarios"])


def test_demo_mode_cannot_be_configured_for_production():
    with pytest.raises(ValidationError):
        Settings(clinical_demo_mode=True, app_env="production")
    assert Settings(clinical_demo_mode=False, app_env="production").demo_operations_allowed is False


def test_reset_and_load_are_refused_under_a_production_profile(demo, monkeypatch):
    # Even if the flag were flipped at runtime, the operations check the profile again.
    monkeypatch.setattr(settings, "app_env", "production")
    assert client.post(f"{K}/clinical-demo/reset", json=CONFIRM, headers=admin()).status_code == 403
    assert client.post(f"{K}/clinical-demo/scenarios/A", headers=admin()).status_code == 403
    assert client.post(f"{K}/clinical-demo/seed", headers=admin()).status_code == 403
    assert client.get(f"{K}/clinical-demo/status").json()["demo_mode"] is False


def test_reset_is_refused_outside_demo_mode_or_without_key_or_confirmation(demo, monkeypatch):
    assert client.post(f"{K}/clinical-demo/reset", json=CONFIRM).status_code == 403, "no key"
    assert client.post(
        f"{K}/clinical-demo/reset", json=CONFIRM, headers={"X-Governance-Admin-Key": "wrong"}
    ).status_code == 403
    assert client.post(f"{K}/clinical-demo/reset", json={"confirm": "yes"}, headers=admin()).status_code == 422
    monkeypatch.setattr(settings, "clinical_demo_mode", False)
    assert client.post(f"{K}/clinical-demo/reset", json=CONFIRM, headers=admin()).status_code == 403


def test_unknown_scenario_is_rejected(demo):
    assert client.post(f"{K}/clinical-demo/scenarios/Z", headers=admin()).status_code == 422


# --- Loading scenarios ------------------------------------------------------------------


def test_scenario_a_loads_both_documents_into_one_processed_case(demo):
    body = _load("A")
    assert body["documents"] == ["A_hospital_bill.txt", "A_discharge_summary.txt"]
    assert [p["status"] for p in body["processing"]] == ["completed", "completed"]
    entities = client.get(f"{K}/cases/{body['case_id']}").json()["entities"]
    names = {e["name"] for e in entities}
    assert any("Laparoscopic Cholecystectomy" in n for n in names), "from the bill"
    excerpts = [e for e in entities if e["type"] == "document_text"]
    assert len(excerpts) == 2, "both documents were ingested into the same case"
    # The loaded case works like any uploaded case: plausibility runs on it.
    plaus = client.get(f"/api/v1/billnyay/cases/{body['case_id']}/clinical-plausibility")
    assert plaus.status_code == 200 and plaus.json()["assessment"]["status"] == "CLINICAL_REVIEW_RECOMMENDED"


def test_scenario_c_loads_with_the_recorded_ocr_replay(demo):
    body = _load("C")
    bench = {r["brand_name"]: r for r in client.get(f"/api/v1/dawacheck/cases/{body['case_id']}/benchmark").json()}
    assert bench["Augmntn 625mg"]["trust"]["state"] == "AWAITING_HUMAN_READING"
    assert bench["Dolo 650"]["benchmark"]["comparison_status"] == "COMPARED"


def test_scenario_d_raises_the_safety_escalation(demo):
    body = _load("D")
    esc = client.get(f"{K}/cases/{body['case_id']}/safety-escalations").json()
    assert esc["escalations"], "demo rules are seeded on first use and fire on the letter"


# --- Reset --------------------------------------------------------------------------------


def test_reset_removes_demo_cases_only_and_is_idempotent(demo):
    loaded = _load("A")["case_id"]
    # A demo document uploaded by hand through the patient UI is a demo case too.
    manual = client.post(f"{K}/cases", json={"consent_opt_in": True}).json()["id"]
    client.post(f"{K}/cases/{manual}/upload", files={"file": ("D.txt", (DOCS / "D_insurance_denial_letter.txt").read_bytes())})
    # A case with any other document is never touched.
    other = client.post(f"{K}/cases", json={"consent_opt_in": True}).json()["id"]
    client.post(f"{K}/cases/{other}/upload", files={"file": ("bill.txt", b"Consultation: 700\nTotal: 700\n")})

    first = client.post(f"{K}/clinical-demo/reset", json=CONFIRM, headers=admin())
    assert first.status_code == 200, first.text
    body = first.json()
    assert body["demo_cases_removed"] >= 2
    assert body["other_cases_kept"] >= 1
    assert body["credentials"]["reviewers"]["clinician_a"]["reviewer_token"]

    client._case_tokens.pop(loaded, None)
    client._case_tokens.pop(manual, None)
    assert client.get(f"{K}/cases/{other}").status_code == 200, "non-demo case kept"
    for case_id in (loaded, manual):
        assert client.get(f"{K}/cases/{case_id}").status_code in (401, 403, 404)

    second = client.post(f"{K}/clinical-demo/reset", json=CONFIRM, headers=admin()).json()
    assert second["demo_cases_removed"] == 0, "a second reset finds nothing left to remove"
    assert second["demo_rules_restored"] == body["demo_rules_restored"] == 2


def test_reset_rotates_demo_credentials(demo):
    first = client.post(f"{K}/clinical-demo/reset", json=CONFIRM, headers=admin()).json()
    old = first["credentials"]["reviewers"]["clinician_a"]
    second = client.post(f"{K}/clinical-demo/reset", json=CONFIRM, headers=admin()).json()
    new = second["credentials"]["reviewers"]["clinician_a"]
    assert new["reviewer_id"] == old["reviewer_id"], "same persona"
    assert client.get(f"{K}/clinical-reviews/assigned", headers=rh(old["reviewer_token"])).status_code in (401, 403)
    assert client.get(f"{K}/clinical-reviews/assigned", headers=rh(new["reviewer_token"])).status_code == 200


def test_reset_restores_a_demo_rule_retired_during_the_demo(demo):
    creds = client.post(f"{K}/clinical-demo/reset", json=CONFIRM, headers=admin()).json()["credentials"]
    a = creds["reviewers"]["clinician_a"]["reviewer_token"]
    b = creds["reviewers"]["clinician_b"]["reviewer_token"]
    rules = client.get(f"{K}/safety-rules").json()["rules"]
    fast = next(r for r in rules if r["rule_key"] == "demo-stroke-fast-signs" and r["status"] == "ACTIVE")
    client.post(f"{K}/safety-rules/{fast['rule_id']}/retire", json={"reason": "Demo retirement."}, headers=rh(a))
    done = client.post(f"{K}/safety-rules/{fast['rule_id']}/retire", json={"reason": "Confirmed."}, headers=rh(b))
    assert done.status_code == 200 and done.json()["status"] == "RETIRED"

    creds = client.post(f"{K}/clinical-demo/reset", json=CONFIRM, headers=admin()).json()["credentials"]
    rules = client.get(f"{K}/safety-rules", params={"status": "ALL_PUBLIC"}).json()["rules"]
    fast_rules = [r for r in rules if r["rule_key"] == "demo-stroke-fast-signs"]
    assert [r["status"] for r in fast_rules] == ["ACTIVE"], "exactly one demo FAST rule after reset, and it is ACTIVE"

    # And the Scenario D letter escalates again.
    case_id = _load("D")["case_id"]
    assert client.get(f"{K}/cases/{case_id}/safety-escalations").json()["escalations"]


def test_concurrent_resets_do_not_interleave(demo):
    """Two resets fired together (a double click) run one after the other: both succeed
    and the demo ends with exactly one ACTIVE copy of each demo rule."""
    from conftest import TestingSessionLocal

    _load("D")

    async def both():
        async def one():
            async with TestingSessionLocal() as session:
                return await demo_control.reset_demo(session)

        return await asyncio.gather(one(), one())

    first, second = asyncio.run(both())
    assert sorted([first["demo_cases_removed"], second["demo_cases_removed"]])[0] == 0
    creds = client.post(f"{K}/clinical-demo/reset", json=CONFIRM, headers=admin()).json()["credentials"]
    assert creds["reviewers"]["clinician_a"]["reviewer_token"]
    rules = client.get(f"{K}/safety-rules").json()["rules"]
    demo_keys = [r["rule_key"] for r in rules if r["rule_key"].startswith("demo-") and r["status"] == "ACTIVE"]
    assert sorted(demo_keys) == ["demo-emergency-signs-etat", "demo-stroke-fast-signs"]
