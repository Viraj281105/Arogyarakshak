# ArogyaRakshak — Deterministic Demo Kit

Everything needed to run a reproducible judge demo of the patient → evidence → human
review → administrative decision-support flow. **All documents and people here are
synthetic.** No real patient, prescriber, hospital, insurer or registry is represented.

```text
demo/
├── README.md                 ← this file: setup, reset, what is real vs demo-only
├── scenarios/                ← one script per scenario (A–D): steps, expected output, limits
├── documents/                ← synthetic documents to upload (all labelled SYNTHETIC)
└── fixtures/README.md        ← where the runtime fixtures live and what they contain
```

## 1. Start the stack in demo mode

Demo mode is the existing ADR-011 mechanism (`CLINICAL_DEMO_MODE`), not a second seed
system. **Never enable it in a real deployment.**

```powershell
# API (from apps/api). Leave GROQ_API_KEY unset for a fully deterministic demo:
# extraction then uses the rule-based fallback, whose output the tests pin.
$env:CLINICAL_DEMO_MODE = "true"
$env:CLINICAL_GOVERNANCE_ADMIN_KEY = "choose-a-long-random-demo-key"
$env:GROQ_API_KEY = ""
uvicorn app.main:app --port 8000

# Web (from apps/web)
npm run dev          # http://localhost:3000 — reviewer workspace at /clinical-review
```

Seed the demo reviewers, institution, playbook and two demo safety rules (re-running
rotates the credentials; nothing is duplicated):

```bash
curl -X POST http://localhost:8000/api/v1/kadi/clinical-demo/seed -H "X-Governance-Admin-Key: choose-a-long-random-demo-key"
```

Keep the response open during the demo: it holds the one-time credentials for
**Dr. Demo Clinician A/B** (DEMO_VERIFIED board members), **Demo Pharmacist**
(SELF_DECLARED), **Demo Medical Transcriptionist** (UNVERIFIED), and the demo hospital
desk (`institution_token`, `playbook_id`). Credentials are never written to disk.

**Reset between runs:** delete each demo case from the UI ("Delete this case & all data"),
or restart the API with a fresh database. Re-seeding is safe at any time.

## 2. Scenarios

| | Scenario | Documents | Module | Script |
|---|---|---|---|---|
| A | Clinical review → doctor-authored statement → appeal PDF | `A_hospital_bill.txt`, `A_discharge_summary.txt` | BillNyay | [scenarios/A_clinical_review_statement.md](scenarios/A_clinical_review_statement.md) |
| B | Pre-auth readiness + missing clinical confirmation | `B_preauth_request.txt` | DaaviSetu | [scenarios/B_preauth_readiness.md](scenarios/B_preauth_readiness.md) |
| C | Uncertain medicine OCR + two-reader agreement / disagreement | `C_prescription_uncertain.png` | DawaCheck | [scenarios/C_uncertain_ocr_prescription.md](scenarios/C_uncertain_ocr_prescription.md) |
| D | Safety escalation | `D_insurance_denial_letter.txt` | Kadi / BimaNyay | [scenarios/D_safety_escalation.md](scenarios/D_safety_escalation.md) |

Each scenario is also an automated test, so its expected output cannot silently drift:
`apps/api/tests/test_demo_documents.py` (A, B, D) and
`apps/api/tests/test_demo_scenario_c.py` (C).

## 3. What is real and what is demo-only

| Real (same code as production) | Demo-only |
|---|---|
| Upload, BYOD transient processing, entity extraction (rule-based without Groq), entity resolution | The synthetic documents themselves |
| Plausibility check, readiness evaluation, safety rule evaluation, DawaCheck trust gate | Demo reviewers' `DEMO_VERIFIED` status (labelled "Demo verification only") |
| Review requests, consent, assignment, COI, evidence packets, statement lifecycle, PDF signing | Demo safety rules (board-approved by demo personas; sources cited by title only) |
| Transcription tasks, blind two-reader consensus, NOT_APPLIED / held-back logic | Scenario C only: OCR confidences + extraction replayed from a recorded fixture |

## 4. Honest limits to state out loud

- No reviewer is verified against a real medical/pharmacy council — the product never claims so.
- Plausibility uses a 6-code project-curated table; it is not a clinical guideline and not a necessity determination.
- Readiness keyword evidence is weak and only searches the first 1,000 characters of each document.
- Safety rules are keyword floors; they miss paraphrase and ignore negation.
- Mobile has not been run on a device or emulator; demo on the web app.
- With `GROQ_API_KEY` set, extraction output (and the appeal letter) can vary run to run.
