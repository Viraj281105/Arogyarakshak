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

# 3. Register all packages in editable mode. -c keeps torch/torchvision on the CPU-only
#    build (see apps/api/constraints-cpu.txt). [semantic] is optional: it adds
#    sentence-transformers for Kadi's IndicSBERT signal (ADR-006), which stays off unless
#    KADI_SEMANTIC_MATCHING=true and downloads a ~950 MB model on first use.
pip install -c apps/api/constraints-cpu.txt -e "packages/kadi[semantic]"
pip install -c apps/api/constraints-cpu.txt -e packages/billnyay
pip install -c apps/api/constraints-cpu.txt -e packages/daavisetu
pip install -c apps/api/constraints-cpu.txt -e packages/bimanyay
pip install -c apps/api/constraints-cpu.txt -e packages/schemesetu
pip install -c apps/api/constraints-cpu.txt -e packages/dawacheck

# 4. Install test harness and architecture tooling
pip install pytest pytest-asyncio aiosqlite httpx import-linter==2.1 PyYAML
```

The database schema is managed by Alembic (ADR-020). With the default
`SCHEMA_MANAGEMENT=migrate` the API upgrades the database at start-up; to do it by hand:

```bash
cd apps/api && alembic upgrade head && cd ../..
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

### 5.2.1 Self-hosted fonts (no Google Fonts)
Fonts are served from npm packages, never from Google at build or runtime:
- Web (`apps/web`): `@fontsource-variable/{fraunces,plus-jakarta-sans,inter,jetbrains-mono}`,
  imported as CSS in `app/globals.css`. Their `@font-face` rules use `unicode-range`, so browsers
  fetch only the latin / latin-ext files they need. Do not use `next/font/google`.
- Mobile (`apps/mobile`): `@expo-google-fonts/{fraunces,plus-jakarta-sans,inter,jetbrains-mono}`
  (font files ship in the app binary), plus `expo-font` and `expo-splash-screen`, loaded by
  `src/hooks/useAppFonts.ts` while the splash screen stays up.
- The font stacks live in `packages/design-tokens/tokens.json` and keep a Devanagari-capable
  fallback (`'Noto Sans Devanagari', 'Nirmala UI', Mangal`) because none of the four families
  include Devanagari. After editing them run `npm run generate`.

### 5.2.2 Web motion system (`apps/web/app/motion`)
Two animation dependencies, both pinned: `motion` 14.14.0 (Motion for React, official npm) and
`lenis` 1.3.27 (smooth scroll). No GSAP, no Three.js. ESLint `no-restricted-imports` confines
`motion`, `framer-motion`, `lenis` and `gsap` to `app/motion/**`.
- Budget rule: routes that do not use a motion pattern must not pay for it. `SmoothScroll`
  (mounted in `layout.tsx`) imports Lenis dynamically after mount and skips it under reduced
  motion; Motion's `domAnimation` loads lazily via `LazyMotion` and only `Magnetic` uses it.
- `Reveal`, `Parallax` and `ScrollScrub` are CSS-only (`animation-timeline: view()` behind
  `@supports` and `prefers-reduced-motion: no-preference`); the server-rendered state is the
  final visible state. `CountUp` server-renders its final value. `format` is a function, so pass
  it from a client component.
- `/motion-lab` (dev only, route group `(dev)`, not linked) shows every pattern and returns 404
  when `NODE_ENV === "production"`.

### 5.3 Shared TypeScript code (vendoring)
Shared web/mobile code (tokens, API client, i18n) is authored in `packages/<name>/src` and
copied into each app by the root tooling (ADR-022). Install it once at the repo root:
```bash
npm install            # root: tsx + scripts only, no workspaces
npm run generate       # regenerate vendored copies (runs scripts/generators/*.mjs)
npm run check:generated  # fail if any vendored copy is stale (runs scripts/checks/*.mjs)
npm test               # Node tests in scripts/tests and packages/*/tests
```
Never hand-edit vendored files (they start with a GENERATED banner); edit the source in
`packages/<name>/src`, run `npm run generate`, and commit both.
`packages/api-client` also needs the root devDependency `openapi-typescript` (official npm registry): it generates
`src/generated/schema.d.ts` from the committed `docs/api/openapi.json`, so re-export that file first (`scripts/export_openapi.py`) after an API change.
Vendoring also removes files left behind in a vendored dir after a source file is deleted (and `check:generated` reports them).
`packages/i18n` holds the `Language` type and the `common` string namespace (only keys whose EN/HI/MR text is identical on web and mobile; spread into both catalogues). `check:generated` also fails if `common` has a key missing or blank in any language; `packages/i18n/tools/parity.ts` has the parity helpers (`findMissingKeys`, `findUnreviewedStubs`, `findUnusedKeys`).

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
# Expected output: {"status":"ok","version":"1.0.0","groq_configured":false,"groq_model":"openai/gpt-oss-120b"}
```

Run test suites:
```bash
# Backend, package and infrastructure-policy tests (counts in PROJECT_CONTEXT.md)
python -m pytest

# Architecture contracts (ADR-018)
PYTHONPATH=apps/api lint-imports

# Mobile client invariant & contract tests (10 tests)
cd apps/mobile
npm test
cd ../..
```
