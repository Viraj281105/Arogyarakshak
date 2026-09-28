# Scenario B — Pre-authorization readiness + missing clinical confirmation

**Pinned by:** `apps/api/tests/test_demo_documents.py::test_scenario_b_preauth_readiness_and_missing_clinical_confirmation`

## Starting state
Demo mode, demo seed run. You need the seed's `institution.institution_token` and `playbook_id`
(the demo hospital desk's private checklist for laparoscopic cholecystectomy).

## Action sequence
1. **Patient:** Demo controls → **Load Scenario B** (or upload `demo/documents/B_preauth_request.txt` with consent ticked) and wait for completion. The institution credential and `playbook_id` are in the Demo controls panel after **Reset demo**.
2. DaaviSetu tab → **Check documentation readiness**, entering the demo `playbook_id` and the
   institution credential when asked.
3. The checklist shows each item with its status. Select the item(s) marked **Needs a doctor's
   confirmation** → tick consent → **Ask a doctor to confirm** → assign **Dr. Demo Clinician B** by ID.
4. **Reviewer (Clinician B):** accept (COI) → decide the fact: *Confirmed by the records*, *Not
   supported*, or *Cannot determine* → tick the confirmation sentence → **Record decision**.
5. **Patient:** re-check readiness; optionally download the claim package ZIP.

## Expected output
- *Ultrasound (USG) abdomen report* → **Found in your documents** (keyword match — weak evidence).
- *Liver function test report* → **Not found in the text checked** ("missing" means not found in the
  extracted entities / first 1,000 characters, not "absent from your records").
- *Documentation of conservative management tried* → **Needs a doctor's confirmation**: the document
  mentions an analgesic/antispasmodic "as reported by the patient"; software never marks a clinical fact
  satisfied.
- After the doctor decides, the item shows the doctor's decision with name and COI. In the pinned test
  the doctor chooses *Cannot determine* → **Doctor could not determine**.
- No output mentions approval probability.

## Real vs demo-only
Real: readiness evaluation, fact routing, reviewer decision and its display. Demo-only: the document,
the demo institution, playbook ("illustrative only, not real insurer guidance") and Clinician B.

## Known limitations
Keyword evidence is weak and whole-word ("analgesics" would not match "analgesic"). The baseline
checklist is generic, not insurer-specific.
