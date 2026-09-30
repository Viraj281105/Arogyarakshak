# Scenario E — Diabetes admission: documentation readiness + missing document

**Pinned by:** `apps/api/tests/test_demo_documents.py::test_scenario_e_diabetes_admission_readiness_with_one_missing_document`

**Theme fit:** Diabetes care → patient/caregiver → financial and administrative support. This
scenario is **paperwork only**: it lists which commonly requested documents can be found in the
case. It never reads, interprets or scores a clinical value (an HbA1c number, a glucose level),
never assesses diabetes control, and never predicts an insurer's decision.

## Starting state
Demo mode, demo seed run. You need the seed's `institution.institution_token` and
`diabetes_playbook_id` (the demo hospital desk's checklist for a diabetes-related admission;
it is a second playbook beside Scenario B's `playbook_id`). Both are shown in **Demo controls**
after **Reset demo** ("Scenario E desk").

## Action sequence
1. **Patient:** Demo controls → **Load Scenario E** (or upload
   `demo/documents/E_diabetes_admission_note.txt` with consent ticked) and wait for completion.
   The page opens DaaviSetu.
2. DaaviSetu tab → open **Hospital desk: apply your institution's private playbook**, enter the
   `diabetes_playbook_id` and the institution credential → **Check documentation readiness**.
3. The checklist shows the generic baseline items plus the four diabetes-playbook items. Select
   the item(s) marked **Needs a doctor's confirmation** → tick consent → **Ask a doctor to
   confirm** → assign **Dr. Demo Clinician B** by ID.
4. **Reviewer (Clinician B):** accept (COI) → decide the fact: *Confirmed by the records*, *Not
   supported*, or *Cannot determine* → tick the confirmation sentence → **Record decision**.
5. **Patient:** re-check readiness (with the playbook again).

## Expected output
- *HbA1c (glycated haemoglobin) report* → **Found in your documents** (keyword match — weak evidence).
- *Blood glucose report (fasting or post-meal)* → **Found in your documents** (keyword match — weak evidence).
- *Renal function report (creatinine / eGFR)* → **Not found in the text checked**. The synthetic
  note deliberately omits it, so the recommended action names exactly one missing document.
  ("Missing" means not found in the extracted entities / first 1,000 characters, not "absent
  from your records".)
- *Documentation of diabetes treatment tried before admission* → **Needs a doctor's
  confirmation**: the note mentions a medicine the patient is on; software never marks a
  clinical fact satisfied. The generic *Previous treatment history* baseline item also asks for
  confirmation.
- After the doctor decides, the item shows the doctor's decision with name and COI (the pinned
  test uses *Confirmed*, giving **Confirmed by reviewer**). The missing renal function report is
  **not** cleared by that confirmation.
- No output mentions approval probability.

## Real vs demo-only
Real: extraction (rule-based without a Groq key), readiness evaluation, fact routing, reviewer
decision and its display. Demo-only: the document, the demo institution, the playbook
("illustrative only, not real insurer guidance") and Clinician B.

## Known limitations
- The checklist wording is **unsourced and illustrative**. No public insurer requirement was
  verified for it; a real hospital desk would author its own playbook. Have the clinical lead
  review it before it is presented as realistic.
- Keyword evidence is weak, whole-word, and limited to the first 1,000 characters of the
  redacted excerpt (`docs/architecture/clinical-review.md`); "metformin" matches but
  "metformins" would not.
- This scenario does not price-check medicines (DawaCheck's curated list holds one diabetes
  drug, metformin) and does not compute scheme eligibility (SchemeSetu never decides from
  documents).
- Scenario E is pinned by pytest only; `scripts/demo_runtime_smoke.py` still runs A–D.
