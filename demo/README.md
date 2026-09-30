# ArogyaRakshak — Deterministic Demo Kit

Everything needed to run a reproducible judge demo of the patient → evidence → human
review → administrative decision-support flow. **All documents and people here are
synthetic.** No real patient, prescriber, hospital, insurer or registry is represented.

**Presenting? Use the step-by-step runbook: [docs/JUDGE_DEMO.md](../docs/JUDGE_DEMO.md).**

```text
demo/
├── README.md                 ← this file: setup, reset, what is real vs demo-only
├── scenarios/                ← one script per scenario (A–E): steps, expected output, limits
├── documents/                ← synthetic documents (all labelled SYNTHETIC); also copied into the API image
└── fixtures/README.md        ← where the runtime fixtures live and what they contain
```

## 1. Start the stack in demo mode

Demo mode is the ADR-011 mechanism (`CLINICAL_DEMO_MODE`), not a second seed system.
**Never enable it in a real deployment** — with `APP_ENV=production` the API refuses to start.

```powershell
$env:CLINICAL_DEMO_MODE = "true"
$env:CLINICAL_GOVERNANCE_ADMIN_KEY = "choose-a-long-random-demo-key"
docker compose up -d --build          # web :3000, api :8000, postgres
# or locally: uvicorn app.main:app --port 8000 (apps/api) and npm run dev (apps/web)
```

Leave `GROQ_API_KEY` unset for a fully deterministic demo: extraction then uses the
rule-based path, whose output the tests pin.

## 2. Reset, load, recover

In the web app, a striped **DEMO MODE** banner appears (with **What is simulated?**) and a
**Demo controls** panel:

- **Reset demo** — deletes every case that holds a committed synthetic demo document
  (cases with any other upload are kept), removes the demo safety rules and re-seeds them
  ACTIVE, rotates the demo credentials and shows them once (reviewer IDs + tokens, the demo
  insurance-desk credential and the two playbook ids: Scenario B's and Scenario E's). Idempotent; double clicks are serialised.
- **Load Scenario A / B / C / D / E** — creates a fresh consented case and runs the scenario's
  synthetic documents through the *real* upload pipeline (Scenario A puts the bill **and**
  the discharge summary in one case), then opens the scenario's module and shows its script.

The same operations over HTTP (governance key required, demo mode only):

```bash
curl -X POST http://localhost:8000/api/v1/kadi/clinical-demo/reset -H "X-Governance-Admin-Key: <key>" -H "Content-Type: application/json" -d '{"confirm":"RESET DEMO"}'
curl -X POST http://localhost:8000/api/v1/kadi/clinical-demo/scenarios/A -H "X-Governance-Admin-Key: <key>"
```

Health check for the whole kit (runs A–D over HTTP, then resets; `49/49` expected):

```bash
python scripts/demo_runtime_smoke.py --api http://127.0.0.1:8000 --admin-key <key>
```

## 3. Scenarios

| | Scenario | Documents | Module | Script |
|---|---|---|---|---|
| A | Clinical review → doctor-authored statement → appeal PDF | `A_hospital_bill.txt`, `A_discharge_summary.txt` | BillNyay | [scenarios/A_clinical_review_statement.md](scenarios/A_clinical_review_statement.md) |
| B | Pre-auth readiness + missing clinical confirmation | `B_preauth_request.txt` | DaaviSetu | [scenarios/B_preauth_readiness.md](scenarios/B_preauth_readiness.md) |
| C | Uncertain medicine OCR + two-reader agreement / disagreement + per-tablet price check | `C_prescription_uncertain.png` | DawaCheck | [scenarios/C_uncertain_ocr_prescription.md](scenarios/C_uncertain_ocr_prescription.md) |
| D | Safety escalation | `D_insurance_denial_letter.txt` | Kadi / BimaNyay | [scenarios/D_safety_escalation.md](scenarios/D_safety_escalation.md) |
| E | Diabetes admission: documentation readiness + missing document (paperwork only) | `E_diabetes_admission_note.txt` | DaaviSetu | [scenarios/E_diabetes_admission_readiness.md](scenarios/E_diabetes_admission_readiness.md) |

Each scenario is also an automated test, so its expected output cannot silently drift:
`apps/api/tests/test_demo_documents.py` (A, B, D, E), `test_demo_scenario_c.py` (C),
`test_demo_control.py` (reset / loaders), and `scripts/demo_runtime_smoke.py` (over HTTP; covers A–D only).

## 4. What is real and what is demo-only

| Real (same code as production) | Demo-only |
|---|---|
| Upload, transient processing, entity extraction (rule-based without Groq), entity resolution | The synthetic documents themselves |
| Trust gate, human-reading tasks, blind two-reader consensus, NOT_APPLIED / held-back logic | Scenario C only: OCR confidences + extraction replayed from a recorded fixture |
| DawaCheck price basis (per tablet) and BillNyay rate basis (per day / visit / bottle) | Demo reviewers' `DEMO_VERIFIED` status (labelled "Demo verification only") |
| Plausibility, readiness, safety evaluation, review lifecycle, COI, evidence packets, PDF signing, audit trail, case timeline | Demo safety rules (approved by demo personas; sources cited by title only), demo institution and playbook |
| Case deletion cascade (used by the reset) | The reset / scenario-loader routes themselves |

## 5. Honest limits to state out loud

- No reviewer is verified against a real medical/pharmacy council — the product never claims so.
- Plausibility uses a 6-code project-curated table; it is not a clinical guideline and not a necessity determination.
- Reference prices are small curated subsets; a line or medicine outside them is "not benchmarked", never "fair".
- Readiness keyword evidence is weak and only searches the first 1,000 characters of each document.
- Safety rules are keyword floors; they miss paraphrase and ignore negation.
- Mobile has not been run on a device or emulator; demo on the web app.
- With `GROQ_API_KEY` set, extraction output (and the appeal letter) can vary run to run.
