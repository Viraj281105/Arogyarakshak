# ArogyaRakshak Mobile App (`apps/mobile`)

Cross-platform mobile client for **ArogyaRakshak (आरोग्यरक्षक)** built with **Expo**, **React Native**, and **TypeScript**.

---

## 1. Overview

The ArogyaRakshak mobile client provides an accessible, mobile-first companion for patients at hospital billing desks, insurance claim processing, and pharmacy counters.

### Core Foundation Features
- **Expo SDK 52 + React Native (New Architecture enabled)**
- **Strict TypeScript** (`tsconfig.json`) with path aliases (`@/*`)
- **Trilingual Interface**: English, Hindi (हिंदी), and Marathi (मराठी)
- **Accessible Design System**: Dark/light theme palette matching the web app, WCAG 2.1 AA contrast, and strict minimum 44px touch targets (`--min-touch-target: 44px`)
- **Document Scanner & Camera Foundation**: Document framing guides with BYOD zero retention
- **Offline-First Architecture**: Network status listeners, transient secure session storage, and graceful offline banners
- **Shared API Gateway Client**: Type-safe REST client connecting to FastAPI backend (`/api/v1/`) across all 5 modules and Kadi

---

## 2. Directory Structure

```text
apps/mobile/
├── App.tsx                     # Application entry point (SafeArea, Theme, Navigation)
├── app.json                    # Expo configuration manifest
├── package.json                # Dependencies and npm scripts
├── tsconfig.json               # TypeScript configuration with @/* alias
├── .env.example                # Environment variables template
└── src/
    ├── api/                    # Shared API client & domain boundaries
    │   ├── client.ts           # Fetch client with timeout and error normalization
    │   ├── endpoints.ts        # Typed endpoints (kadi, billnyay, bimanyay, etc.)
    │   ├── types.ts            # Request & response interfaces matching FastAPI
    │   └── index.ts
    ├── components/             # Reusable accessible UI primitives (>= 44px)
    │   ├── Badge.tsx           # Status and statutory citation badge
    │   ├── Button.tsx          # Accessible button with 44px tap zone
    │   ├── Card.tsx            # Surface card container with subtle elevation
    │   ├── Header.tsx          # App bar with BYOD badge, language & theme toggle
    │   ├── OfflineBanner.tsx   # Offline connectivity banner
    │   └── index.ts
    ├── config/                 # Environment & constants
    │   └── env.ts              # Typed configuration with platform defaults
    ├── hooks/                  # Custom React & offline-first hooks
    │   ├── useLanguage.ts      # Active language switcher (en, hi, mr)
    │   ├── useNetworkStatus.ts # Network reachability monitor
    │   ├── useOfflineStorage.ts# Transient secure storage (BYOD guard)
    │   └── index.ts
    ├── navigation/             # React Navigation foundation
    │   ├── BottomTabNavigator.tsx # 5 modules + Home tab navigation
    │   ├── RootNavigator.tsx   # Stack navigator with modal CameraScan
    │   ├── types.ts            # Type definitions for route parameters
    │   └── index.ts
    ├── screens/                # Screen shells & container views
    │   ├── HomeScreen.tsx      # Dashboard & scanner launch
    │   ├── CameraScanScreen.tsx# Viewfinder with document framing
    │   ├── BillNyayScreen.tsx  # Hospital bill audit shell
    │   ├── DaaviSetuScreen.tsx # Pre-claim cashless pre-auth shell
    │   ├── BimaNyayScreen.tsx  # Claim denial dispute shell
    │   ├── SchemeSetuScreen.tsx# Welfare eligibility shell
    │   ├── DawaCheckScreen.tsx # Medicine price cap shell
    │   └── index.ts
    ├── services/               # Device peripheral abstractions
    │   └── scanner.ts          # Document scanner service & BYOD upload payload
    ├── theme/                  # Design tokens matching apps/web
    │   ├── colors.ts           # Dark & light palettes
    │   ├── spacing.ts          # 44px touch targets & 8pt grid
    │   ├── typography.ts       # Devanagari-safe line-heights
    │   ├── ThemeContext.tsx    # Theme provider & hook
    │   └── index.ts
    └── translations/           # Trilingual dictionary
        ├── strings.ts          # EN, HI, MR dictionary strings
        └── index.ts
```

---

## 3. Development Setup

### 3.1 Prerequisites
- Node.js >= 18.0 (Node 24 recommended)
- npm >= 9.0
- Expo Go app on Android/iOS (or Android Studio / Xcode simulator)

### 3.2 Installation
```bash
cd apps/mobile
npm install
```

### 3.3 Environment Configuration
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

| Variable | Description | Default (Android) | Default (iOS / Web) |
|---|---|---|---|
| `EXPO_PUBLIC_API_URL` | FastAPI Backend Gateway | `http://10.0.2.2:8000` | `http://localhost:8000` |

> **Note for Android Emulator:** The Android emulator uses `10.0.2.2` to access the host machine's `localhost:8000`.

### 3.4 Running the Application
```bash
# Start Expo development server
npm start

# Run on Android emulator
npm run android

# Run on iOS simulator
npm run ios

# Run in Web browser
npm run web
```

### 3.5 First device / emulator run — checklist

The app is unit-tested and type-checked but **has not yet been run on a device or emulator**
(the development machine has no emulator image). For the first run:

1. API in demo mode on the host: `CLINICAL_DEMO_MODE=true`, a governance key, `uvicorn app.main:app --host 0.0.0.0 --port 8000`
   (bind `0.0.0.0` only on a trusted network, for a physical device).
2. `EXPO_PUBLIC_API_URL`: emulator → `http://10.0.2.2:8000` (default on Android); physical device → `http://<host LAN IP>:8000`.
   Allow the host firewall to accept port 8000.
3. `npm install && npm start`, open in Expo Go / `npm run android`.
4. Walk: Home → **Scan** (camera permission) → photograph `demo/documents/A_hospital_bill.txt` printed, or any bill →
   watch the processing card reach *complete* (or *taking longer than expected* → **Refresh status**) → BillNyay
   (audit, per-day/visit notes) → DawaCheck (case medicines; manual check requires choosing what the amount paid for) →
   DaaviSetu → BimaNyay. Switch tabs mid-processing: the active case must survive.
5. Record what failed in `PROJECT_CONTEXT.md` (§9 validation debt) — do not claim device validation without it.

---

## 4. Architectural Invariants

1. **Zero Retention (BYOD)**: Raw document photos (hospital bills, prescriptions, denial letters) are stored strictly in transient memory. They are expunged immediately after Kadi OCR extraction. Storing patient files permanently on device storage is blocked by design.
2. **Accessible Touch Targets**: All interactive elements (buttons, segmented tabs, icons) adhere to WCAG 2.1 SC 2.5.5 and WCAG 2.2 SC 2.5.8 with a minimum `44px x 44px` touch target.
3. **Module Boundaries**: The mobile client consumes the FastAPI gateway (`/api/v1/`) without embedding business rules locally.
4. **Patient-facing only**: reviewer, transcription-reader and safety-board work is web-only (`/clinical-review`).

---

## 5. Case Processing Lifecycle

`scan → upload 202 → processing → SSE → extraction complete → case ready`

- `src/services/caseProcessing.ts` is a pure state machine (`idle | processing | ready | failed | timeout`), unit-tested in `tests/case_processing.test.ts`; `src/hooks/useCaseProcessing.ts` binds it to the SSE stream.
- A screen given a case is `processing` from its **first render**; case data (audit, medicines, readiness, safety) is loaded only when the server reports `completed` or `idle`. A stream that closes without a terminal event is never treated as completion.
- 90 s without any event → "Processing is taking longer than expected." with **Refresh status** (reopens the stream; the server replays the status or reports `idle`).
- Async loads are sequence-guarded (`createRequestGuard`), so an early or stale response cannot overwrite newer state.
- The scan records the **active case** (`src/services/activeCase.ts`); BillNyay, DaaviSetu, BimaNyay and DawaCheck use the route `caseId` or fall back to it, so a bill scanned in BillNyay reaches DaaviSetu readiness and DawaCheck without a second scan.
- BillNyay's post-scan audit runs only once extraction is ready.

**Runtime status:** type-checked and unit-tested only. The app has **not** been run on a device or emulator (no emulator image/AVD is installed on the development machine).
