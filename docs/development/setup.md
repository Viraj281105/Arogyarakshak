# Developer Setup Guide

This guide walks you through setting up a complete local development environment for **ArogyaRakshak** on Windows, macOS, or Linux.

---

## 1. System Prerequisites

Ensure you have the following software installed:
- **Git** (`git --version` >= 2.30)
- **Python 3.11** (`python --version` must report 3.11.x; Python 3.12+ or 3.14 may have compatibility issues with certain binary packages)
- **Node.js** (`node --version` >= 18.x or 20.x, with `npm`)
- **Docker Desktop** (with Docker Compose v2)

---

## 2. Clone Repository & Setup Virtual Environment

```bash
# 1. Clone repo
git clone https://github.com/Viraj281105/Arogyarakshak.git
cd Arogyarakshak

# 2. Create Python 3.11 virtual environment
python -m venv .venv

# 3. Activate virtual environment
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# Linux / macOS:
source .venv/bin/activate
```

---

## 3. Configure Environment Variables

```bash
# Copy example configuration
cp .env.example .env
```

Edit `.env` and configure your credentials:
```env
# Groq API configuration
GROQ_API_KEY=gsk_your_real_key_here
GROQ_MODEL=openai/gpt-oss-120b

# PostgreSQL credentials
POSTGRES_USER=arogyarakshak
POSTGRES_PASSWORD=arogyarakshak
POSTGRES_DB=arogyarakshak

# Database URL for local connection
DATABASE_URL=postgresql://arogyarakshak:arogyarakshak@localhost:5432/arogyarakshak
```

---

## 4. Install Dependencies & Editable Packages

ArogyaRakshak is a monorepo containing local Python domain packages. Register them in editable mode (`-e`) so your changes apply instantly:

```bash
# 1. Upgrade pip
python -m pip install --upgrade pip

# 2. Install FastAPI dependencies
pip install -r apps/api/requirements.txt

# 3. Register all packages in editable mode
pip install -e packages/kadi
pip install -e packages/billnyay
pip install -e packages/daavisetu
pip install -e packages/bimanyay
pip install -e packages/schemesetu
pip install -e packages/dawacheck

# 4. Install test harness
pip install pytest pytest-asyncio aiosqlite httpx
```

---

## 5. Install Client Dependencies

### 5.1 Web Application (Next.js)
```bash
cd apps/web
npm install
cd ../..
```

### 5.2 Mobile Application (React Native / Expo)
```bash
cd apps/mobile
npm install
cd ../..
```

---

## 6. Running the Stack

### Option A: Docker Compose (Full Stack)
```bash
docker-compose up --build
```
- **Web App**: [http://localhost:3000](http://localhost:3000)
- **FastAPI**: [http://localhost:8000](http://localhost:8000)
- **Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **PostgreSQL**: `localhost:5432`

### Option B: Local Services (Fast Iteration)
1. Start only the PostgreSQL database container:
   ```bash
   docker-compose up postgres -d
   ```
2. Start the FastAPI backend with hot-reload:
   ```bash
   cd apps/api
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```
3. In a separate terminal, start the Next.js dev server:
   ```bash
   cd apps/web
   npm run dev
   ```
4. In another terminal, run the mobile development bundler:
   ```bash
   cd apps/mobile
   npm run start
   ```

---

## 7. Verify Your Setup

Verify the backend and database health check:
```bash
curl http://localhost:8000/health
# Expected output: {"status":"ok","version":"1.0.0"}
```

Run test suites:
```bash
# Backend & domain package tests (32 tests)
python -m pytest packages/ apps/api/tests/

# Mobile client invariant & contract tests (10 tests)
cd apps/mobile
npm test
cd ../..
```
