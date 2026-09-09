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
| `EXPO_PUBLIC_USE_MOCK_DATA` | Bypass network for UI dev | `false` | `false` |

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

---

## 4. Architectural Invariants

1. **Zero Retention (BYOD)**: Raw document photos (hospital bills, prescriptions, denial letters) are stored strictly in transient memory. They are expunged immediately after Kadi OCR extraction. Storing patient files permanently on device storage is blocked by design.
2. **Accessible Touch Targets**: All interactive elements (buttons, segmented tabs, icons) adhere to WCAG 2.1 SC 2.5.5 and WCAG 2.2 SC 2.5.8 with a minimum `44px x 44px` touch target.
3. **Module Boundaries**: The mobile client consumes the FastAPI gateway (`/api/v1/`) without embedding business rules locally.
