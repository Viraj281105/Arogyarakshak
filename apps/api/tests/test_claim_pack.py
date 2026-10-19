"""ADR-015 Claim Pack: one in-memory ZIP across modules, authorized, consented, honest."""

import io
import json
import zipfile

from tests.clinical_helpers import K, case_token, client, make_case

PACK = "/api/v1/kadi/cases/{}/claim-pack"
def _track(case_id):
    return client.post(
        f"/api/v1/bimanyay/timeline?case_id={case_id}",
        json=TIMELINE_PAYLOAD,
        headers={"X-Case-Access-Token": case_token(case_id)},
    )


TIMELINE_PAYLOAD = {"insurer_name": "Acme Health", "date_initiated": "2026-01-10", "claim_number": "CLM-77"}


def _zip(res) -> zipfile.ZipFile:
    assert res.status_code == 200, res.text
    assert res.headers["content-type"] == "application/zip"
    return zipfile.ZipFile(io.BytesIO(res.content))


def _manifest(z):
    return json.loads(z.read("manifest.json"))


def _files(manifest):
    return {f["section"]: f for f in manifest["files"]}


def test_requires_case_access_token():
    case_id = make_case()
    res = client.get(PACK.format(case_id), headers={"X-Case-Access-Token": "wrong-token"})
    assert res.status_code == 403
    body = res.json()
    assert "detail" in body and "message" in body


def test_requires_consent():
    case_id = make_case(consent=False)
    assert client.get(PACK.format(case_id)).status_code == 403


def test_unknown_case_is_404_or_denied():
    assert client.get(PACK.format("CASE-does-not-exist")).status_code in (403, 404)


def test_empty_case_says_not_available_and_invents_nothing():
    case_id = make_case(doc=None)
    z = _zip(client.get(PACK.format(case_id)))
    files = _files(_manifest(z))
    for key in ("deadline_timeline", "bill_audit", "appeal_draft", "medicine_price_check", "preauth_form"):
        assert files[key]["included"] is False, key
        assert "Not available for this case" in files[key]["summary"]
    assert "preauth_form.pdf" not in z.namelist()
    assert "Not available for this case" in z.read("04_appeal_draft.txt").decode()
    assert "not available for this case" in z.read("README.txt").decode()


def test_case_with_data_includes_checklist_audit_and_medicines():
    case_id = make_case()
    z = _zip(client.get(PACK.format(case_id)))
    m = _manifest(z)
    files = _files(m)
    assert files["documentation_checklist"]["included"] is True
    checklist = z.read("01_documentation_checklist.txt").decode()
    assert "PRE-AUTHORIZATION READINESS CHECKLIST" in checklist
    assert files["bill_audit"]["included"] is True
    assert "CGHS" in z.read("03_bill_audit.txt").decode()
    assert files["medicine_price_check"]["included"] is True
    assert "OCR_EXTRACTED" in files["medicine_price_check"]["provenance"]
    # No LLM work is triggered implicitly: no appeal exists unless the patient drafted one.
    assert files["appeal_draft"]["included"] is False
    # Paperwork only: no approval predictions anywhere in the pack.
    for name in z.namelist():
        if name.endswith(".txt"):
            text = z.read(name).decode().lower()
            assert "approval probability" not in text and "likely to be approved" not in text


def test_manifest_matches_zip_contents_exactly():
    case_id = make_case()
    assert _track(case_id).status_code == 200
    z = _zip(client.get(PACK.format(case_id)))
    m = _manifest(z)
    names = set(z.namelist())
    included = {f["file"] for f in m["files"] if f["included"]}
    excluded = {f["file"] for f in m["files"] if not f["included"]}
    assert included <= names
    # Unavailable sections that are text files still ship (stating so); the PDF does not.
    assert "preauth_form.pdf" in excluded and "preauth_form.pdf" not in names
    assert {"README.txt", "manifest.txt", "manifest.json"} <= names
    assert names - {"README.txt", "manifest.txt", "manifest.json"} == {f["file"] for f in m["files"]} - {"preauth_form.pdf"}
    timeline = z.read("02_deadline_timeline.txt").decode()
    assert "Acme Health" in timeline and "CLM-77" in timeline
    assert _files(m)["deadline_timeline"]["included"] is True
    assert m["provenance_classes"]
    assert any("original uploaded documents" in x for x in m["not_included"])


def test_existing_appeal_and_claim_form_are_included_when_present():
    case_id = make_case()
    appeal = client.post(f"/api/v1/billnyay/cases/{case_id}/appeal")
    assert appeal.status_code == 200, appeal.text
    claim = client.post(
        f"/api/v1/daavisetu/cases/{case_id}/claim",
        json={"policy_number": "POL-1", "patient_name": "Asha Rao", "hospital_name": "City Care Hospital",
              "diagnosis": "K35.8", "treatment_plan": "Appendectomy"},
    )
    assert claim.status_code == 200, claim.text
    z = _zip(client.get(PACK.format(case_id)))
    files = _files(_manifest(z))
    assert files["appeal_draft"]["included"] is True and "AI_DRAFTED" in files["appeal_draft"]["provenance"]
    assert z.read("preauth_form.pdf")[:4] == b"%PDF"


def test_no_original_file_bytes_and_nothing_persisted():
    marker = b"UNIQUE-ORIGINAL-FILE-MARKER-9f3a"
    doc = (
        b"City Care Hospital\nDiagnosis: K35.8 Acute appendicitis\n"
        b"Laparoscopic Appendectomy 45000\nTotal: 45000\n" + marker + b"\n"
    )
    case_id = make_case(doc=doc)
    res = client.get(PACK.format(case_id))
    z = _zip(res)
    assert marker not in res.content
    for name in z.namelist():
        assert marker not in z.read(name)
    # Read-only: building the pack must not add generic mappings or other rows.
    before = client.get(f"{K}/cases/{case_id}").json()
    client.get(PACK.format(case_id))
    assert client.get(f"{K}/cases/{case_id}").json() == before


def test_pack_is_isolated_per_case():
    a = make_case()
    b = make_case(doc=None)
    assert _track(a).status_code == 200
    z = _zip(client.get(PACK.format(b)))
    assert _files(_manifest(z))["deadline_timeline"]["included"] is False
