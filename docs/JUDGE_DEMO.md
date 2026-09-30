# Judge Demo Runbook

For a teammate who has never seen this repository. Follow it top to bottom; every step
says what you should see. Total demo time: 8–12 minutes.

> **Everything shown is synthetic.** No real patient, hospital, insurer, doctor or
> registry is involved. Say so at the start.

---

## 0. Before the judges arrive (10 minutes)

### Start the stack

**Docker (recommended):**

```powershell
# From the repository root. Pick any long random operator key and keep it to hand.
$env:CLINICAL_DEMO_MODE = "true"
$env:CLINICAL_GOVERNANCE_ADMIN_KEY = "choose-a-long-random-demo-key"
docker compose up -d --build
```

- Web: http://localhost:3000 · API: http://localhost:8000/health (`"status":"ok"`).
- Leave `GROQ_API_KEY` **unset** for a deterministic demo (rule-based extraction; every
  scenario is pinned by tests with this setting).
- `APP_ENV=production` together with demo mode is refused at start-up — that is deliberate.

**Without Docker:** API from `apps/api` with the same two variables set and
`uvicorn app.main:app --port 8000`; web from `apps/web` with `npm run dev`. The API then
uses the `DATABASE_URL` in `.env` (Postgres) — see `docs/development/setup.md`.

### Prove it works (1 minute)

```powershell
python scripts/demo_runtime_smoke.py --api http://127.0.0.1:8000 --admin-key choose-a-long-random-demo-key
```

Expect `49/49 checks passed`. It runs Scenarios A–D over HTTP and resets afterwards.

### Prepare the browser

1. Tab 1: http://localhost:3000 — the patient app. A striped **DEMO MODE** banner must be
   visible. If it is not, the API is not in demo mode: stop and fix that first.
2. Open **Demo controls** → paste the operator key → **Reset demo**. Confirm the dialog.
   The panel lists the demo personas with **Copy** buttons (reviewer ID and token).
   *These credentials are shown once and live only in this tab — do not reload it.*
3. Tab 2: http://localhost:3000/clinical-review — the reviewer workspace. It shows the
   same DEMO MODE banner.

---

## 1. Opening (1 minute) — what to say

> "Patients cannot check hospital bills, insurance denials or medicine prices. Most AI
> tools make this worse: they read a smudged prescription wrongly and then build a price
> check or an appeal on the mistake, or they compare a strip price with a per-tablet
> ceiling and shout '1,300% overcharged'. ArogyaRakshak's rule is: **nothing uncertain is
> acted on until a named human settles it, and every output says whether a machine or a
> person produced it.**"

Click **What is simulated?** in the banner and read the list aloud — it comes from the
running server, so it is accurate for this configuration.

---

## 2. Scenario C — the trust gate (3 minutes) · *the most important one*

1. Demo controls → **Load Scenario C**. Wait for "Scenario C loaded". The page opens the
   DawaCheck tab and the processing log says a demo fixture was replayed.
2. Point at **What has happened to this case**: document received → information extracted
   → "Unclear readings could not be tied to one medicine…" → automatic checks. Each line
   is a stored record with its own time; nothing appears before it happened.
3. **Medicines from your documents**:
   - *Augmntn 625mg* — **Awaiting human reading** (its whole line was read with low
     confidence and names exactly this medicine).
   - *Pan 40* and *Pan-D* — held back: the faded "Tab Pan" could be either.
   - *Amoxicillin 500* — held back: the software "corrected" the spelling; a correction is
     not a confirmation.
   - *Dolo 650* — clearly read, price-checked: **₹2.10 billed per tablet · NPPA ceiling
     ₹2.30 per tablet → Within ceiling**. Point at "Price basis read from the document's
     rate column". *This is the per-unit rule.*
4. In **Unclear prescription text**, tick consent and assign **Demo Pharmacist** and
   **Demo Medical Transcriptionist** by their reviewer IDs (Copy from Demo controls).
5. Tab 2: paste the pharmacist's token → **Transcriptions** → type
   `Tab Augmentin 625mg 1-0-1 x 5 days` → submit. Show that the reader **never sees the
   software's guess**. Repeat with the transcriptionist's token.
6. Tab 1: the Augmentin row is now **Human-reviewed** and price-checked:
   **₹22.00 per tablet vs ₹20.10 → Above ceiling (+9.45%)**. The timeline gains "Two
   independent readers agreed".

**Show the price-basis refusal (30 s):** in "Check any medicine by name" enter
`Dolo 650mg Tablet (15s)`, amount `33.5`, choose *One tablet / capsule / vial* →
**Cannot compare reliably** ("the name mentions a pack"). Change to *One pack* with 15
units → ₹2.23 per tablet, within ceiling.

## 3. Scenario A — human-authored vs machine-derived (4 minutes)

1. **Load Scenario A** (bill **and** discharge summary in one case). BillNyay opens.
2. **Run CGHS Benchmark Audit**. Point at:
   - *Room Rent (Private Ward) 3 days* — **₹4,500 per day × 3 days** → within reference.
   - *Specialist Consultation*, *Paracetamol IV* — **not compared**: the reference is per
     visit / per bottle and the line does not say how many.
   - The footer: CGHS rates are **reference rates, not a legal cap** — a gap is a reason
     to ask for justification, not proof.
3. **Check clinical plausibility** → **Clinical review recommended**: the bill has a
   cholecystectomy but the documented diagnosis is appendicitis. Administrative lines are
   set aside; MRI is "not assessed". Badge: **Machine-derived**. "Not a necessity
   determination."
4. Tick consent → **Request Clinical Review** → assign **Dr. Demo Clinician A** by ID. The
   profile says "Demo verification only — not checked against any real medical registry".
5. Tab 2 (Clinician A's token): open the review → declare conflict of interest
   (*Independent*) → **Accept** → **Open shared evidence** (locked until COI) → tick items →
   write a statement → **Save draft** → **Lock for finalization** → tick the confirmation
   sentence → **Finalize and sign**.
6. Tab 1: **Refresh status** → the statement appears **Human-authored**, with COI and the
   demo-verification label. The patient never saw the draft.
7. **Draft IRDAI Appeal Letter** (badged Machine-derived) → **Download Signed Appeal PDF**:
   the annex carries the doctor's words verbatim.
8. Optional: the reviewer **Withdraws** → re-download → the annex is gone (the stored PDF
   is re-signed).

## 4. Scenario D — safety floor (1 minute)

**Load Scenario D**. A red **Clinical safety check** banner appears: *Possible stroke
warning signs (FAST)*, matched words *slurred speech*, *arm weakness*, and the disclaimer
"This safety layer is a decision-support floor…". Optional: in the reviewer workspace a
board member can *request* retirement of the rule — it keeps escalating until a second
board member confirms (four-eyes).

## 5. Scenario B — readiness, not approval (optional, 2 minutes)

**Load Scenario B** → DaaviSetu → **Check documentation readiness** with the demo playbook
ID and institution credential (Copy buttons). USG *found* (weak keyword evidence), LFT *not
found*, conservative management **Needs a doctor's confirmation** → ask Dr. Demo Clinician
B. No approval probability anywhere.

## 5a. Scenario E — diabetes paperwork readiness (optional, 2 minutes)

**Load Scenario E** → DaaviSetu → open *Hospital desk*, enter the **Scenario E desk** playbook ID
and the institution credential (Copy buttons) → **Check documentation readiness**. HbA1c and blood
glucose reports *found* (weak keyword evidence), renal function report *not found*, diabetes
treatment history **Needs a doctor's confirmation** → ask Dr. Demo Clinician B. Say plainly: this
is paperwork only — it never reads or scores a glucose or HbA1c value, never assesses diabetes
control, and the checklist wording is illustrative, not real insurer guidance.

---

## 6. Recovering from mistakes

| Problem | Fix |
|---|---|
| Wrong click, messy case, a reader typed the wrong thing | Demo controls → **Reset demo**, then load the scenario again. Reset removes only cases holding a synthetic demo document and restores the demo safety rules. |
| Reviewer token "invalid" | Every reset issues **new** credentials. Copy them again from Demo controls. |
| Page reloaded — credentials gone | Reset again (they are never stored). |
| No DEMO MODE banner | API not in demo mode: set `CLINICAL_DEMO_MODE=true` and restart the API. |
| "Demo operations are disabled" | Demo mode off, `APP_ENV=production`, or no `CLINICAL_GOVERNANCE_ADMIN_KEY` set on the API. |
| Processing "taking longer than expected" | Press **Refresh status**. Processing status is in memory per API process — after an API restart, reload the scenario. |
| Buttons do nothing on double-click | By design: one demo operation at a time (UI and server). |
| Anything else | Run the smoke script; if it passes, the stack is fine — reset and continue. |

## 7. Module cheat-sheet (one line each)

- **Kadi** — shared layer: reads the document in memory, extracts entities, links repeated mentions, holds back what it is unsure of, keeps the case timeline.
- **BillNyay** — bill lines vs CGHS reference rates (per unit, with stated quantities); clinical plausibility; appeal with a doctor's statement attached verbatim.
- **DawaCheck** — medicine price vs NPPA ceiling **per tablet**, only for settled readings.
- **DaaviSetu** — pre-authorization *readiness* checklist; clinical facts go to a doctor.
- **BimaNyay** — insurance denial vs IRDAI 2024 circular; 3-tier appeals and deadlines.
- **SchemeSetu** — provisional PM-JAY / MJPJAY eligibility with sources.

## 8. What is deterministic / simulated (say it plainly)

- The documents, the reviewer personas ("Demo verification only"), the two demo safety rules and the demo insurance-desk playbooks (Scenarios B and E).
- Scenario C only: OCR confidences and extraction are replayed from a recorded fixture keyed to the committed image. Everything after extraction is the real pipeline.
- Without `GROQ_API_KEY`, extraction is rule-based and the appeal letter is a template (the UI says so).

## 9. Limitations to state before a judge finds them

- Reference tables are small curated subsets (7 NPPA formulations, a CGHS subset, a 6-code plausibility table).
- A *confidently* misread word is not detected — only low-confidence readings go to humans.
- No reviewer is verified against a real council; there are no user accounts (per-case tokens only).
- The mobile app has **not** been run on a device or emulator; the demo uses the web app.
- Hindi/Marathi wording awaits native-speaker review.
- Real Groq output was not validated in this release (no key available); the demo does not depend on it.

## 10. Where to point a technical judge

- Trust gate: `packages/kadi/kadi/clinical_review/medicine_trust.py`
- Price basis: `packages/dawacheck/dawacheck/price_basis.py`, `packages/billnyay/billnyay/rate_basis.py` (ADR-012)
- Review lifecycle & verification labels: `packages/kadi/kadi/clinical_review/`, `apps/api/app/clinical/`
- Timeline: `packages/kadi/kadi/timeline.py`
- Demo kit: `apps/api/app/clinical/demo_control.py`, `demo/`
- Tests pinning each scenario: `apps/api/tests/test_demo_*.py`, `test_demo_control.py`; runtime: `scripts/demo_runtime_smoke.py`
