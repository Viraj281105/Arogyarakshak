# Scenario D — Safety escalation

**Pinned by:** `apps/api/tests/test_demo_documents.py::test_scenario_d_denial_letter_raises_safety_escalation`

## Starting state
Demo mode, demo seed run (creates two ACTIVE demo rules: FAST stroke signs; WHO ETAT emergency signs).

## Action sequence
1. **Patient:** Demo controls → **Load Scenario D** (or upload `demo/documents/D_insurance_denial_letter.txt`). A retired demo rule is restored to ACTIVE by **Reset demo**.
2. As soon as processing completes, a red **Clinical safety check** banner appears above the modules.
3. (Optional) BimaNyay tab: analyse the denial; the clinical-review trigger can route it to a doctor.
4. (Optional governance) In `/clinical-review` → *Safety governance* as Clinician A: **Request
   retirement** of a rule — it stays ACTIVE and keeps escalating until **Clinician B confirms**.
5. (Optional failure state) Stop the database / break rule loading: the banner reads **Safety check
   unavailable** — never "no escalation".

## Expected output
- Escalation *Possible stroke warning signs (FAST)*, severity **Urgent**, matched words
  `slurred speech`, `arm weakness`, rule version, source (title reference), limitations, and the floor
  disclaimer "This safety layer is a decision-support floor, not a substitute for professional clinical
  assessment."
- Only matched terms are stored for the case (never surrounding text); they are erased with the case.

## Real vs demo-only
Real: full-text scan at upload, rule evaluation, versioning, carry-forward, four-eyes activation and
retirement. Demo-only: the letter and the two demo rules (approved by demo personas, sources by title).

## Known limitations
Keyword rules miss paraphrase and ignore negation ("no slurred speech" still matches). The absence of
an escalation is never a safety assessment.
