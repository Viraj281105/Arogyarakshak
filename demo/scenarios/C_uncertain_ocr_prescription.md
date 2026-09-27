# Scenario C — Uncertain medicine OCR + two-reader agreement / disagreement

**Pinned by:** `apps/api/tests/test_demo_scenario_c.py::test_scenario_c_end_to_end`

## Starting state
Demo mode (required — see below), demo seed run. You need the seed credentials of **Demo
Pharmacist** and **Demo Medical Transcriptionist** (the two independent readers).

## Why a fixture
EasyOCR's per-word confidence varies by machine and model download, so which words come out
"uncertain" is not reproducible. In `CLINICAL_DEMO_MODE` only, uploading the committed
`demo/documents/C_prescription_uncertain.png` (recognised by its SHA-256) **replays a recorded OCR
and extraction result** (`apps/api/app/clinical/demo_ocr.py`). The processing log says so ("Demo
fixture: …"). Everything after extraction is the real pipeline. Any other image — or this one
outside demo mode — runs real OCR.

## Action sequence
1. **Patient:** Demo controls → **Load Scenario C** (or upload `C_prescription_uncertain.png`). The log shows the demo-fixture notice and
   "1 unclear reading needs a human reader … 3 medicine(s) … will not be price-checked".
2. DawaCheck tab → **Medicines from your documents** shows the trust decision per medicine.
3. In "Unclear prescription text", tick consent and assign **both** demo readers to the task.
4. **Readers (reviewer workspace → Transcriptions):** each types what the line says, blind to the
   software's guess and to each other. Agreement: both type `Tab Augmentin 625mg 1-0-1 x 5 days`.
5. **Patient:** the Augmentin row becomes **Human-reviewed** and is price-checked:
   "₹22.00 billed per tablet · NPPA ceiling ₹20.10 per tablet" → *Above ceiling (+9.45%)*. The
   basis note says it was read from the document's rate column ("Rate per tablet/capsule").
6. Disagreement: on the *Amoxicillin 500* row press **Ask for a human reading of this entry**, assign
   both readers; one reads `Amoxycillin 500`, the other `Azithromycin 500` → the row shows **Readers
   disagreed — confirm with pharmacist** and stays un-benchmarked.

## Expected output (before any reading)
| Medicine | State | Why |
|---|---|---|
| Augmntn 625mg | Awaiting human reading | Its whole line was read with confidence 0.34 and names exactly this medicine → a two-reader task |
| Pan 40, Pan-D | Unclear — not yet read by a human (*Unclear reading could match more than one medicine*) | The faded "Tab Pan 1-0-0" could be either; software does not pick one |
| Amoxicillin 500 | Unclear — not yet read by a human (*Unclear reading only resembles this name*) | OCR was unsure of "Amoxycilin"; the extractor normalised the spelling — a normalisation is not a confirmation |
| Dolo 650 | Machine-extracted, price-checked ("₹2.10 billed per tablet · NPPA ceiling ₹2.30 per tablet" → within) | Clearly read; the slip's "Rate per tablet/capsule" heading sets the price basis |

The prescriber line ("Dr. … MBBS Reg. No.") was also low-confidence but is never sent to readers.

## Real vs demo-only
Demo-only: the image, the replayed OCR confidences and extraction (including the deliberate
"Amoxycilin → Amoxicillin" normalisation), the reader personas. Real: linking, ambiguity and
possible-match detection, the task cap, blind consensus, NOT_APPLIED handling, the trust gate,
DawaCheck.

## Known limitations
Prices on the synthetic slip are declared **per tablet/capsule** by its rate column, the unit the
NPPA ceilings use. Since ADR-012, DawaCheck converts a strip/pack price only when the pack size is
stated ("Strip of 15", "15's") and otherwise shows **Cannot compare reliably** — never a percentage.
Demonstrate this with the manual check: `Dolo 650mg Tablet (15s)`, ₹33.50, "One tablet" → refused
(the name states a pack); "One pack" of 15 → ₹2.23 per tablet, within the ceiling.
Readers read the original the patient holds (no image is stored), so this works in person, not
remotely. Two agreeing non-prescriber readers is weaker than confirmation by the dispensing pharmacist.
