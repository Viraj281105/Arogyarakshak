# Scenario A — Clinical review → doctor-authored statement → appeal PDF

**Pinned by:** `apps/api/tests/test_demo_documents.py::test_scenario_a_bill_to_doctor_statement_to_pdf`

## Starting state
- API in demo mode, `GROQ_API_KEY` unset, demo seed run (see `demo/README.md`).
- Browser A: patient app `http://localhost:3000`. Browser B (or private window): `/clinical-review`.

## Action sequence
1. **Patient:** upload `demo/documents/A_hospital_bill.txt` (tick consent). Wait for "Document processed".
   (`A_discharge_summary.txt` is the supporting clinical document; the web uploader starts a new case
   per upload, so the live demo uses the bill alone and the automated test adds both to one case.)
2. BillNyay tab → **Run CGHS Benchmark Audit** (shows benchmarked lines and unmatched lines).
3. **Check clinical plausibility** → status **Clinical review recommended** (mixed result).
4. In "Clinical Review by a Named Doctor": tick consent → **Request Clinical Review**.
5. Assign by reviewer ID: paste **Dr. Demo Clinician A**'s `reviewer_id` from the seed output → the
   looked-up profile shows "Demo verification only — not checked against any real medical registry".
6. **Reviewer (browser B):** paste Clinician A's `reviewer_token` → open the review → declare COI
   (e.g. *Independent*) → **Accept** → **Open shared evidence** → tick the items reviewed → write the
   statement in their own words + limitations → **Save draft** → **Lock for finalization** → tick the
   confirmation sentence → **Finalize and sign**.
7. **Patient:** **Refresh status** in the review panel → the finalized statement appears (purple
   "Human-authored" badge, COI, demo-verification label).
8. **Draft IRDAI Appeal Letter** → **Download Signed Appeal PDF** → the annex carries the statement verbatim.
9. (Optional) Reviewer **Withdraws** the statement → patient re-downloads the PDF → the annex is gone.

## Expected output
- Plausibility: `CLINICAL_REVIEW_RECOMMENDED`; summary names *Laparoscopic Cholecystectomy* as an
  intervention the curated table associates with a diagnosis that is not documented; Room Rent, Nursing,
  Registration and Consultation are listed as administrative, not assessed as interventions; MRI Brain is
  "not assessed".
- The appeal letter is badged **Machine-derived**; the statement is badged **Human-authored**.
- The PDF annex contains the reviewer's text verbatim, their COI and "Demo verification only".
- Without a statement, the patient sees "No statement from a named clinician is attached"; **the PDF
  carries no such notice** (it would only weaken the claimant's filing).

## Real vs demo-only
Real: extraction (rule-based), plausibility, consent, assignment, COI, evidence packet, statement
lifecycle, hashing, PDF signing and re-rendering. Demo-only: the bill, the demo clinician persona and
its DEMO_VERIFIED label.

## Known limitations
The plausibility table covers 6 ICD-10 prefixes. The web uploader creates one case per upload. The
appeal letter text is a static template without Groq (disclosed in the UI).
