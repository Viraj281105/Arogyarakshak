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
