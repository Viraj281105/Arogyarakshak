"""Runtime smoke test of the demo golden paths against a RUNNING API (any database).

Drives Scenarios A–D over real HTTP — the same calls the web client makes — and asserts
what each step should mean, not just HTTP 200. Used to validate the Postgres runtime:

    # API in demo mode against Postgres (docker compose up -d postgres), then:
    python scripts/demo_runtime_smoke.py --api http://127.0.0.1:8001 --admin-key <CLINICAL_GOVERNANCE_ADMIN_KEY>

Standard library only. Deletes nothing but demo data (it calls the demo reset).
Exit code 0 = every check passed.
"""

import argparse
import json
import sys
import urllib.error
import urllib.request
import uuid
from pathlib import Path

DOCS = Path(__file__).resolve().parents[1] / "demo" / "documents"
FINALIZE_TEXT = "I confirm that this statement represents my own professional judgment based on the information reviewed."
FACT_TEXT = "I confirm that this decision represents my own professional judgment based on the information reviewed."

CHECKS = []


class Api:
    def __init__(self, base, admin_key):
        self.base = base.rstrip("/")
        self.admin_key = admin_key

    def call(self, method, path, body=None, headers=None, raw=False, files=None):
        url = self.base + path
        hdrs = dict(headers or {})
        data = None
        if files is not None:
            boundary = uuid.uuid4().hex
            name, content = files
            data = (
                f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{name}\"\r\n"
                "Content-Type: application/octet-stream\r\n\r\n"
            ).encode() + content + f"\r\n--{boundary}--\r\n".encode()
            hdrs["Content-Type"] = f"multipart/form-data; boundary={boundary}"
        elif body is not None:
            data = json.dumps(body).encode()
            hdrs["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
        try:
            with urllib.request.urlopen(req, timeout=120) as res:
                payload = res.read()
                return res.status, (payload if raw else (json.loads(payload) if payload else None))
        except urllib.error.HTTPError as err:
            payload = err.read()
            try:
                return err.code, json.loads(payload)
            except Exception:
                return err.code, payload

    def admin(self):
        return {"X-Governance-Admin-Key": self.admin_key}


def check(name, cond, detail=""):
    CHECKS.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name + (f" — {detail}" if detail and not cond else ""))


def case_headers(token):
    return {"X-Case-Access-Token": token}


def rh(token):
    return {"X-Reviewer-Token": token}


def load(api, scenario):
    status, body = api.call("POST", f"/api/v1/kadi/clinical-demo/scenarios/{scenario}", headers=api.admin())
    check(f"Scenario {scenario}: loads", status == 200, str(body)[:300])
    return body


def scenario_a(api, creds):
    body = load(api, "A")
    cid, ch = body["case_id"], case_headers(body["access_token"])
    check("A: both documents processed into one case", [p["status"] for p in body["processing"]] == ["completed", "completed"])
    _, audit = api.call("POST", f"/api/v1/billnyay/cases/{cid}/audit", headers=ch)
    check("A: CGHS audit benchmarks lines", audit.get("benchmarked_count", 0) > 0, str(audit)[:200])
    _, plaus = api.call("GET", f"/api/v1/billnyay/cases/{cid}/clinical-plausibility", headers=ch)
    a = plaus["assessment"]
    check("A: plausibility = clinical review recommended", a["status"] == "CLINICAL_REVIEW_RECOMMENDED", a["status"])
    check("A: cholecystectomy named as conflicting", "Laparoscopic Cholecystectomy" in a["summary"])
    status, review = api.call("POST", f"/api/v1/kadi/cases/{cid}/clinical-reviews",
                              {"source_module": "billnyay", "share_with_reviewer_consent": True}, ch)
    check("A: review requested", status == 201, str(review)[:200])
    rid = review["review_id"]
    doc = creds["reviewers"]["clinician_a"]
    status, _ = api.call("POST", f"/api/v1/kadi/cases/{cid}/clinical-reviews/{rid}/assign", {"reviewer_id": doc["reviewer_id"]}, ch)
    check("A: Clinician A assigned by id", status == 200)
    status, _ = api.call("GET", f"/api/v1/kadi/clinical-reviews/{rid}/evidence", headers=rh(doc["reviewer_token"]))
    check("A: evidence locked before COI/acceptance", status in (403, 409))
    status, _ = api.call("POST", f"/api/v1/kadi/clinical-reviews/{rid}/accept", {"coi_category": "INDEPENDENT_REVIEWER"}, rh(doc["reviewer_token"]))
    check("A: accept with COI", status == 200)
    _, ev = api.call("GET", f"/api/v1/kadi/clinical-reviews/{rid}/evidence", headers=rh(doc["reviewer_token"]))
    ids = [i["item_id"] for i in ev["evidence"]]
    check("A: evidence packet opens after COI", len(ids) > 0)
    text = "Synthetic demo statement: the documented diagnosis does not explain the second procedure."
    status, st = api.call("POST", f"/api/v1/kadi/clinical-reviews/{rid}/statements",
                          {"evidence_reviewed": ids[:2], "reviewer_statement": text, "limitations": "Demo; patient not examined."},
                          rh(doc["reviewer_token"]))
    check("A: draft saved", status == 201, str(st)[:200])
    sid = st["statement_id"]
    _, view = api.call("GET", f"/api/v1/kadi/cases/{cid}/clinical-reviews/{rid}", headers=ch)
    check("A: patient never sees the draft", view.get("current_statement") is None and text not in json.dumps(view))
    status, _ = api.call("POST", f"/api/v1/kadi/clinical-reviews/{rid}/statements/{sid}/submit", headers=rh(doc["reviewer_token"]))
    check("A: locked for finalization", status == 200)
    status, _ = api.call("POST", f"/api/v1/kadi/clinical-reviews/{rid}/statements/{sid}/finalize",
                         {"confirmation": True, "confirmation_text": FINALIZE_TEXT}, rh(doc["reviewer_token"]))
    check("A: finalized with explicit confirmation", status == 200)
    status, _ = api.call("POST", f"/api/v1/kadi/clinical-reviews/{rid}/statements/{sid}/finalize",
                         {"confirmation": True, "confirmation_text": FINALIZE_TEXT}, rh(doc["reviewer_token"]))
    check("A: second finalize refused (immutable)", status == 409)
    _, view = api.call("GET", f"/api/v1/kadi/cases/{cid}/clinical-reviews/{rid}", headers=ch)
    stmt = view["current_statement"]
    check("A: statement is HUMAN_AUTHORED and verbatim", stmt["provenance"] == "HUMAN_AUTHORED" and stmt["reviewer_statement"] == text)
    check("A: demo verification label, never 'verified doctor'",
          "demo" in stmt["reviewer_snapshot"]["verification_label"].lower())
    status, appeal = api.call("POST", f"/api/v1/billnyay/cases/{cid}/appeal", headers=ch)
    check("A: appeal generated", status == 200, str(appeal)[:200])
    status, pdf = api.call("GET", f"/api/v1/billnyay/cases/{cid}/appeal/pdf", headers=ch, raw=True)
    check("A: signed PDF downloads", status == 200 and bytes(pdf[:4]) == b"%PDF")
    status, _ = api.call("GET", f"/api/v1/billnyay/cases/{cid}/appeal/pdf", headers=case_headers("wrong-token"), raw=True)
    check("A: PDF refused with a wrong token", status in (401, 403))
    _, tl = api.call("GET", f"/api/v1/kadi/cases/{cid}/timeline", headers=ch)
    labels = [e["label"] for e in tl["events"]]
    check("A: timeline shows finalization after acceptance",
          labels.index("Doctor-authored statement finalized and signed") > labels.index("Reviewer accepted the review"))
    times = [e["at"] for e in tl["events"]]
    check("A: timeline is chronological", times == sorted(times))
    return cid, ch


def scenario_b(api, creds):
    body = load(api, "B")
    cid, ch = body["case_id"], case_headers(body["access_token"])
    inst = {**ch, "X-Institution-Token": creds["institution"]["institution_token"]}
    _, r = api.call("POST", f"/api/v1/daavisetu/cases/{cid}/readiness", {"playbook_id": creds["playbook_id"]}, inst)
    items = {i["item_id"]: i for i in r["items"]}
    check("B: USG found (keyword)", items["pb_usg_abdomen"]["status"] == "PRESENT")
    check("B: LFT not found", items["pb_lft_report"]["status"] == "MISSING")
    check("B: conservative management needs a doctor", items["pb_conservative_management"]["status"] == "NEEDS_CLINICAL_CONFIRMATION")
    check("B: no approval claim", "approval probability" not in json.dumps(r).lower())
    status, review = api.call("POST", f"/api/v1/daavisetu/cases/{cid}/readiness/clinical-confirmations",
                              {"item_ids": ["pb_conservative_management"], "playbook_id": creds["playbook_id"],
                               "share_with_reviewer_consent": True}, inst)
    check("B: doctor confirmation requested", status == 201, str(review)[:200])
    doc = creds["reviewers"]["clinician_b"]
    api.call("POST", f"/api/v1/kadi/cases/{cid}/clinical-reviews/{review['review_id']}/assign", {"reviewer_id": doc["reviewer_id"]}, ch)
    api.call("POST", f"/api/v1/kadi/clinical-reviews/{review['review_id']}/accept", {"coi_category": "INDEPENDENT_REVIEWER"}, rh(doc["reviewer_token"]))
    fact = review["facts"][0]["fact_id"]
    status, _ = api.call("POST", f"/api/v1/kadi/clinical-reviews/{review['review_id']}/facts/{fact}/decision",
                         {"decision": "CANNOT_DETERMINE", "note": "Not documented.", "confirmation": True, "confirmation_text": FACT_TEXT},
                         rh(doc["reviewer_token"]))
    check("B: doctor decision recorded", status == 200)
    _, after = api.call("POST", f"/api/v1/daavisetu/cases/{cid}/readiness", {"playbook_id": creds["playbook_id"]}, inst)
    item = next(i for i in after["items"] if i["item_id"] == "pb_conservative_management")
    check("B: shows the doctor's decision, never 'satisfied'", item["status"] == "REVIEWER_COULD_NOT_DETERMINE")


def scenario_c(api, creds):
    body = load(api, "C")
    cid, ch = body["case_id"], case_headers(body["access_token"])
    _, rows = api.call("GET", f"/api/v1/dawacheck/cases/{cid}/benchmark", headers=ch)
    bench = {r["brand_name"]: r for r in rows}
    check("C: Augmentin awaits a human reading", bench["Augmntn 625mg"]["trust"]["state"] == "AWAITING_HUMAN_READING")
    check("C: ambiguous Pan held back", bench["Pan 40"]["benchmark"] is None and bench["Pan-D"]["benchmark"] is None)
    check("C: normalised Amoxicillin held back", bench["Amoxicillin 500"]["benchmark"] is None)
    dolo = bench["Dolo 650"]["benchmark"]
    check("C: Dolo compared per tablet, within ceiling",
          dolo["comparison_status"] == "COMPARED" and dolo["price_basis_label"] == "per tablet" and dolo["is_overcharged"] is False)
    _, tasks = api.call("GET", f"/api/v1/kadi/cases/{cid}/transcriptions", headers=ch)
    task = tasks[0]["task_id"]
    for key in ("pharmacist", "transcriptionist"):
        api.call("POST", f"/api/v1/kadi/cases/{cid}/transcriptions/{task}/assign",
                 {"reviewer_id": creds["reviewers"][key]["reviewer_id"], "share_with_reviewer_consent": True}, ch)
    _, blind = api.call("GET", "/api/v1/kadi/transcriptions/assigned", headers=rh(creds["reviewers"]["pharmacist"]["reviewer_token"]))
    check("C: readers are blind to the OCR guess", all(t.get("ocr_candidate") is None for t in blind if t["task_id"] == task))
    for key in ("pharmacist", "transcriptionist"):
        api.call("POST", f"/api/v1/kadi/transcriptions/{task}/readings", {"value": "Tab Augmentin 625mg 1-0-1 x 5 days"},
                 rh(creds["reviewers"][key]["reviewer_token"]))
    _, rows = api.call("GET", f"/api/v1/dawacheck/cases/{cid}/benchmark", headers=ch)
    aug = next(r for r in rows if r["entity_id"] == tasks[0]["entity_id"])
    b = aug["benchmark"]
    check("C: agreed reading is HUMAN_REVIEWED", aug["name_provenance"] == "HUMAN_REVIEWED")
    check("C: Augmentin ₹22.00/tablet vs ₹20.10 → above ceiling",
          b and b["billed_unit_price"] == 22.0 and b["nppa_ceiling_price"] == 20.1 and b["is_overcharged"] is True)


def scenario_d(api, creds):
    body = load(api, "D")
    cid, ch = body["case_id"], case_headers(body["access_token"])
    _, esc = api.call("GET", f"/api/v1/kadi/cases/{cid}/safety-escalations", headers=ch)
    titles = [e.get("title") or e.get("rule_title") for e in esc.get("escalations", [])]
    check("D: FAST escalation fires", any("FAST" in (t or "") for t in titles), str(titles))
    check("D: floor disclaimer present", "decision-support floor" in json.dumps(esc))
    a, b = creds["reviewers"]["clinician_a"]["reviewer_token"], creds["reviewers"]["clinician_b"]["reviewer_token"]
    _, rules = api.call("GET", "/api/v1/kadi/safety-rules")
    fast = next(r for r in rules["rules"] if r["rule_key"] == "demo-stroke-fast-signs")
    _, first = api.call("POST", f"/api/v1/kadi/safety-rules/{fast['rule_id']}/retire", {"reason": "Demo."}, rh(a))
    check("D: one board member cannot retire alone", first.get("status") == "ACTIVE")
    status, second = api.call("POST", f"/api/v1/kadi/safety-rules/{fast['rule_id']}/retire", {"reason": "Confirmed."}, rh(b))
    check("D: second member retires it", status == 200 and second.get("status") == "RETIRED")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", default="http://127.0.0.1:8000")
    ap.add_argument("--admin-key", required=True)
    args = ap.parse_args()
    api = Api(args.api, args.admin_key)

    status, health = api.call("GET", "/health")
    check("API health", status == 200 and health.get("status") == "ok")
    _, demo = api.call("GET", "/api/v1/kadi/clinical-demo/status")
    check("Demo mode reported", demo.get("demo_mode") is True)
    status, reset = api.call("POST", "/api/v1/kadi/clinical-demo/reset", {"confirm": "RESET DEMO"}, api.admin())
    check("Reset", status == 200, str(reset)[:300])
    creds = reset["credentials"]

    cid, ch = scenario_a(api, creds)
    scenario_b(api, creds)
    scenario_c(api, creds)
    scenario_d(api, creds)

    status, again = api.call("POST", "/api/v1/kadi/clinical-demo/reset", {"confirm": "RESET DEMO"}, api.admin())
    check("Reset after the run removes the scenario cases", status == 200 and again["demo_cases_removed"] >= 4, str(again)[:200])
    status, _ = api.call("GET", f"/api/v1/kadi/cases/{cid}", headers=ch)
    check("A's case (and its signed PDF) is gone after reset", status in (401, 403, 404))
    _, rules = api.call("GET", "/api/v1/kadi/safety-rules")
    check("Retired demo rule is ACTIVE again after reset",
          any(r["rule_key"] == "demo-stroke-fast-signs" and r["status"] == "ACTIVE" for r in rules["rules"]))

    failed = [n for n, ok in CHECKS if not ok]
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
