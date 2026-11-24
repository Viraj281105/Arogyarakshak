# Developer Setup Guide

This guide walks you through setting up a complete local development environment for **ArogyaRakshak** on Windows, macOS, or Linux.

---

## 1. System Prerequisites

Ensure you have the following software installed:
- **Git** (`git --version` >= 2.30)
- **Python 3.11** (`python --version` must report 3.11.x; Python 3.12+ or 3.14 may have compatibility issues with certain binary packages)
- **Node.js** (`node --version` >= 20 with `npm`; use 22.19 or newer only if you run Lighthouse CI locally, see `performance-budgets.md`)
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

### 5.1.1 Web motion system (`apps/web/app/motion`)
Two animation dependencies, both pinned: `motion` 14.14.0 (Motion for React, official npm) and
`lenis` 1.3.27 (smooth scroll). No GSAP, no Three.js. ESLint `no-restricted-imports` confines
`motion`, `framer-motion`, `lenis` and `gsap` to `app/motion/**`.
- Budget rule: routes that do not use a motion pattern must not pay for it. `SmoothScroll`
  (opt-in per page, not mounted in `layout.tsx`; it sets `allowNestedScroll` so inner scroll
  containers keep working) imports Lenis dynamically after mount and skips it under reduced
  motion; Motion's `domAnimation` loads lazily via `LazyMotion` and only `Magnetic` uses it.
- `Reveal`, `Parallax` and `ScrollScrub` are CSS-only (`animation-timeline: view()` behind
  `@supports` and `prefers-reduced-motion: no-preference`); the server-rendered state is the
  final visible state. `CountUp` server-renders its final value. `format` is a function, so pass
  it from a client component.
- `/motion-lab` (dev only, route group `(dev)`, not linked) shows every pattern and returns 404
  when `NODE_ENV === "production"`.

### 5.2 Mobile Application (React Native / Expo)
```bash
cd apps/mobile
npm install
cd ../..
```

### 5.2.1 Mobile motion system dependencies
`apps/mobile` uses `@shopify/flash-list` (1.7.x) and `expo-haptics` (~14.0), at the versions Expo SDK 52 pins
(`npx expo install <names>`; official npm registry only). Motion patterns (`Reveal`, `Parallax`, `Pressable`,
`CountUp`, `SlidingIndicator`, `Pulse`, `tap`) live in `apps/mobile/src/motion/`, animate with React Native's
built-in `Animated` API (native driver on device) and honour the OS reduce-motion setting.
**Updated 2026-11-18 (WS5-shell, ruling):** `react-native-reanimated` and `react-native-gesture-handler` were removed
from `apps/mobile/package.json` (unused; Reanimated measured +785,115 B and Gesture Handler about +0.97 MB on the Hermes
bundle). No app code may import either (tests enforce it); re-adding one needs a concrete screen, a fresh
measurement and a budget ruling (`docs/development/performance-budgets.md`). `babel.config.js` lists only
`babel-preset-expo` (if Reanimated ever returns, the preset adds its plugin itself; do not list it again). If
`npx expo install` fails with `EALLOWSCRIPTS`, run `npm install` in `apps/mobile` after it has edited `package.json`.

**Known limitation (Hindi/Marathi text weight):** the bundled font families have no Devanagari glyphs. Shell text
uses `textStyleFor()` / `fontFor()` (`src/theme/fontFamily.ts`): Devanagari strings get the system face with a
numeric `fontWeight`, Latin strings keep the custom family without `fontWeight` (a custom family plus `fontWeight`
can synthesise a double bold on Android). Verified only in the browser preview; not checked on a device. Screen
text that still uses `fontWeight` directly is unaffected (system font).

### 5.2.1a Mobile browser preview (WS5-shell)
`apps/mobile` also depends on `react-native-web` (~0.19.13), `react-dom` (18.3.1) and `@expo/metro-runtime`
(~4.0.1), the versions `npx expo install` selects for SDK 52 (its npm step failed with `EALLOWSCRIPTS`; finished
with plain `npm install`; official npm registry only). They resolve only for the web platform; the Android bundle
does not contain them. Run the preview with:

```bash
cd apps/mobile
EXPO_NO_TELEMETRY=1 npm run web      # Expo web on Metro, http://localhost:8081
```

It is a **preview, not a device-faithful run**: no haptics (skipped on web), no native stack/screens behaviour,
animations run on the JS thread (no native driver), fonts load through `@font-face`, `SecureStore` and
`FileSystem` have no web backend (the camera/upload flow is not meaningful in the browser), and text metrics come
from the browser. The app calls `EXPO_PUBLIC_API_URL` (default `http://localhost:8000`) as on device.

### 5.2.2 Self-hosted fonts (web and mobile, no Google Fonts)
Fonts are served from npm packages, never from Google at build or runtime:
- Web (`apps/web`): `@fontsource-variable/{manrope,inter,jetbrains-mono}` (Manrope + Inter since the
  Deep Forest rebrand, ADR-028; Fraunces and Plus Jakarta Sans were removed), imported as CSS in
  `app/globals.css`, with the latin faces preloaded through `next/font/local` in `app/fonts.ts`. Their `@font-face` rules use `unicode-range`, so browsers
  fetch only the latin / latin-ext files they need. Do not use `next/font/google`.
- Mobile (`apps/mobile`): `@expo-google-fonts/{fraunces,plus-jakarta-sans,inter,jetbrains-mono}`
  (still the pre-rebrand families; moving mobile to Manrope is part of the mobile pass, M7)
  (font files ship in the app binary), plus `expo-font` and `expo-splash-screen`, loaded by
  `src/hooks/useAppFonts.ts` while the splash screen stays up.
- The font stacks live in `packages/design-tokens/tokens.json` and keep a Devanagari-capable
  fallback (`'Noto Sans Devanagari', 'Nirmala UI', Mangal`) because none of the four families
  include Devanagari. After editing them run `npm run generate`.

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
Root devDependencies (all from the official npm registry, pinned in the root `package-lock.json`): `tsx` (runs the TypeScript tests and generators), `openapi-typescript` (API client types) and `@lhci/cli` (Lighthouse CI for the LCP/CLS budgets). The root install is separate from the app installs; `apps/web` and `apps/mobile` keep their own lockfiles.
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

# Root tooling tests and the stale-generated-files check (repo root)
npm test
npm run check:generated

# Web and mobile client tests, lint and types
cd apps/web && npm test && npm run lint && cd ../..
cd apps/mobile && npm run type-check && npm test && cd ../..
```

---

## Observability dependencies (WS1)

`apps/api/requirements.txt` now includes `prometheus-client` and the OpenTelemetry SDK, OTLP/HTTP exporter and FastAPI/httpx/SQLAlchemy instrumentations (all from PyPI). Tracing code is imported only when `OTEL_ENABLED=true`. To run the optional local stack see `docs/operations/observability.md`.
