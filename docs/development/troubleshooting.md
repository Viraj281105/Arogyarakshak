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
  entry (typically the task was a whole uncertain line). The entity records
  `human_transcription.status = "NOT_APPLIED"` and is deliberately kept unsettled (ADR-011).
- **Remedy**: confirm the medicine with the dispensing pharmacist, then have the case holder
  flag the whole entry (`POST .../transcriptions`, `field_type: MEDICINE_NAME`) so two readers
  read it in full; a later partial reading will not clear the state. Do not "fix" this by
  falling back to the OCR name; that is the defect this state prevents.

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
