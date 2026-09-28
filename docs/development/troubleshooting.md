# Troubleshooting & Common Failure Modes

This document catalogs known failure modes, error messages, and verified solutions for **ArogyaRakshak**.

---

## 1. Environment & Dependency Issues

### `ModuleNotFoundError: No module named 'kadi'` (or `billnyay`, `schemesetu`, etc.)
- **Cause**: The monorepo packages have not been registered as editable packages in your active Python virtual environment.
- **Remedy**: Run editable installs from root:
  ```bash
  pip install -e packages/kadi
  pip install -e packages/billnyay
  pip install -e packages/daavisetu
  pip install -e packages/schemesetu
  pip install -e packages/dawacheck
  ```

### `python.exe: No module named pytest`
- **Cause**: Using a global Python installation (e.g. Python 3.14) instead of the project virtual environment (Python 3.11) where testing dependencies are installed.
- **Remedy**: Verify your virtual environment is active:
  ```bash
  # Windows PowerShell:
  .venv\Scripts\Activate.ps1
  # Linux/macOS:
  source .venv/bin/activate
  ```

---

## 2. Database & Connection Issues

### `sqlalchemy.exc.OperationalError: could not translate host name "postgres" to address`
- **Cause**: The default `DATABASE_URL` points to `postgres:5432` (the Docker network service name). When running `apps/api` locally outside Docker, `postgres` cannot be resolved.
- **Remedy**: In your local `.env`, configure `DATABASE_URL` to point to `localhost`:
  ```env
  DATABASE_URL=postgresql://arogyarakshak:arogyarakshak@localhost:5432/arogyarakshak
  ```

### `psycopg2.OperationalError: Connection refused (port 5432)`
- **Cause**: The PostgreSQL container is not running.
- **Remedy**: Start the database service:
  ```bash
  docker-compose up postgres -d
  ```

---

## 3. Groq API & LLM Issues

### `404/400 Error: Model 'llama3-70b' or 'llama-3.3-70b-versatile' is not found / deprecated`
- **Cause**: Calling deprecated Groq models. Groq deprecated Llama 3 70B/8B on June 17, 2026.
- **Remedy**: Ensure `.env` sets:
  ```env
  GROQ_MODEL=openai/gpt-oss-120b
  ```
  Check that your code reads `os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")`.

### `401 Unauthorized: Invalid Groq API Key`
- **Cause**: `GROQ_API_KEY` is missing or contains placeholder text.
- **Remedy**: Add a valid key from [console.groq.com](https://console.groq.com) into your `.env`.

---

## 4. Port Conflicts

| Port | Service | Conflict Resolution |
|---|---|---|
| `5432` | PostgreSQL | Stop local PostgreSQL service (`sudo service postgresql stop` on Linux, or stop Postgres service in Windows `services.msc`). |
| `8000` | FastAPI | Run on alternate port: `uvicorn app.main:app --port 8001 --reload` (update `apps/web` API proxy accordingly). |
| `3000` | Next.js | Run on alternate port: `npm run dev -- -p 3001`. |

---

### `import file mismatch` / "imported module ... is not the same as the test file we want to collect"
- **Cause**: `pytest.ini` collects `packages/*/tests` and `apps/api/tests` together, and those
  directories have no `__init__.py`, so two test files with the same basename collide
  (e.g. a Kadi `test_clinical_review.py` and the API's `test_clinical_review.py`).
- **Remedy**: give every test module a unique basename (the Kadi one is
  `test_clinical_review_domain.py`), then clear stale bytecode:
  `find . -name __pycache__ -path "*tests*" -prune -exec rm -rf {} +`.

### Clinical governance routes return `503`
- **Cause**: `CLINICAL_GOVERNANCE_ADMIN_KEY` is unset, which disables board seating,
  verification attempts and demo seeding by design (ADR-011).
- **Remedy**: set it to a long random value (and `CLINICAL_DEMO_MODE=true` only for local
  demos), restart the API, and send it as `X-Governance-Admin-Key`.

### DawaCheck shows a medicine as "not benchmarked" after transcription resolved
- **Cause**: two readers agreed, but their reading could not be placed into the extracted
  entry (e.g. the uncertain line carried more than the entry, or the reading named no drug). The entity records
  `human_transcription.status = "NOT_APPLIED"` and is deliberately kept unsettled (ADR-011).
- **Remedy**: confirm the medicine with the dispensing pharmacist, then have the case holder
  flag the whole entry (`POST .../transcriptions`, `field_type: MEDICINE_NAME`) so two readers
  read it in full; a later partial reading will not clear the state. Do not "fix" this by
  falling back to the OCR name; that is the defect this state prevents.

### DawaCheck says "Unclear on the document — not yet read by a human" but no task exists
- **Cause**: an uncertain OCR reading could not be linked to exactly one medicine — it named
  several (`AMBIGUOUS`), only resembled the extracted name (`POSSIBLE_MATCH`, typical after an
  LLM spelling correction), was beyond the 10-task cap (`OVER_CAP`), or matched nothing while
  this medicine's name is absent from the clearly read text (`UNGROUNDED`). The medicine is
  held back in `meta.ocr_uncertainty` by design (`clinical-review.md` §10).
- **Remedy**: press "Ask for a human reading of this entry" (whole-entry flag) and have two
  readers read it; only a whole-entry reading clears the state.

### Two different medicines ("Pan 40", "Pan-D") appear as one entity
- **Cause** (fixed 2026-09-27): entity resolution treated a variant letter on one side as a
  missing qualifier and merged them. Medicines now conflict on a one-sided variant letter.
- **Remedy**: cases created before the fix keep the merged entity; delete and re-upload.

### DawaCheck says "Cannot compare reliably" for a correctly read medicine
- **Cause** (ADR-012): the price basis is unknown or contradictory — the bill line does not
  say whether the amount is for one tablet, a strip or several units; a strip price has no
  pack size; the manual check was declared "per tablet" but the name says "(15s)"; or the
  bill describes an injection while the reference ceiling is for a tablet.
- **Remedy**: use the manual check with the correct basis ("One strip" + units in it). Before
  ADR-012 such lines were compared as if per tablet and showed absurd overcharges
  (e.g. +1,335% for a strip of Dolo 650).

### BillNyay says a room/ICU/consultation line "was not compared"
- **Cause** (ADR-012): the CGHS rate is per day / per visit / per bottle and the bill line
  does not state how many ("ICU 18500"). "Room Rent 3 days 13500" is compared as 3 days.
- **Remedy**: expected. The patient can ask the hospital for the day/visit count.

### A request works in the tests but returns 500 on Postgres (foreign-key violation)
- **Cause**: rows referencing another row by a plain foreign key (no ORM relationship) were
  added in the same flush; SQLAlchemy may insert them first. SQLite ignored it because
  foreign keys were off in tests; Postgres rejects it. Found in the release-candidate
  Postgres run: DaaviSetu's doctor-confirmation request (`clinical.service.create_review`).
- **Remedy**: `await db.flush()` after adding the parent. The test engine now runs
  `PRAGMA foreign_keys=ON` (`apps/api/tests/conftest.py`) so this class of bug fails locally.
  Validate against Postgres with `scripts/demo_runtime_smoke.py`.

### Demo controls: "Demo operations are disabled" / reviewer token invalid after a reset
- **Cause**: `CLINICAL_DEMO_MODE` off, `APP_ENV=production`, or no
  `CLINICAL_GOVERNANCE_ADMIN_KEY`; every reset issues new demo credentials.
- **Remedy**: set the variables and restart the API; copy the credentials again from the
  Demo controls panel (they are never stored).

### The web file picker does not offer `.txt` demo documents
- **Cause** (fixed): the picker accepted only images and PDFs although the API accepts
  `.txt`/`.csv`. `DOCUMENT_ACCEPT` in `DocumentUploader.tsx` now lists them.

### Line endings flip to CRLF after a scripted edit on Windows
- **Cause**: Python `open(path, "w")` without `newline=""` writes CRLF on Windows; a
  regex-based web test failed on it. `.gitattributes` mandates LF.
- **Remedy**: write with `newline=""`, or run `sed -i 's/\r$//' <file>`; `git diff --stat`
  showing whole-file changes is the tell.

### Mobile screen says "Processing is taking longer than expected."
- **Cause**: no processing event arrived for 90 s (hung or dropped stream), or the server
  sent `timeout`. The app never assumes completion.
- **Remedy**: press "Refresh status": the stream is reopened; the server replays the
  status or reports `idle` if nothing is being processed (e.g. after an API restart —
  processing status is held in memory by one process).

### Safety banner says "Safety check unavailable"
- **Cause**: the safety rules could not be evaluated (`status: UNAVAILABLE`) or the request
  failed. This is deliberately different from "no escalation".
- **Remedy**: check the API log for "Clinical safety evaluation failed" and the database.

### Scenario C demo upload runs real OCR instead of the fixture
- **Cause**: `CLINICAL_DEMO_MODE` is off, or the uploaded file is not byte-identical to
  `demo/documents/C_prescription_uncertain.png` (the replay matches its SHA-256).
- **Remedy**: enable demo mode and upload the committed file unmodified; if the image was
  regenerated, update `DEMO_PRESCRIPTION_SHA256` in `app/clinical/demo_ocr.py`.

### A safety escalation disappears after a rule is re-versioned
- **Cause**: full-text scan results carry forward to the new ACTIVE version only for terms
  it still lists. If the board removed the term, the escalation is correctly dropped.
- **Remedy**: check the new version's `trigger.match_any`; terms added later are checked
  only against entities and the 1,000-character excerpt of earlier uploads.

---

## 5. Frontend & Next.js Issues

### `npm run lint` fails on React 19 / Next.js dependencies
- **Cause**: Outdated global Node modules or conflicting lockfiles.
- **Remedy**: Clean and reinstall dependencies:
  ```bash
  cd apps/web
  rm -rf node_modules package-lock.json
  npm install
  npm run lint
  ```
