# WS0 Foundation — Design Spec

**Date:** 2026-11-06
**Status:** Approved in conversation; awaiting written-spec review
**Scope:** Shared foundation for the web (Next.js) and mobile (Expo) clients. Prerequisite for all UI work and for the parallel workstreams in the roadmap below.

## 1. Purpose and success criteria

Give ArogyaRakshak two native UIs (web, mobile) that look and behave as one product, are fast and light, and can be redesigned page by page without drift between platforms.

Success means:
- One edit to a design token reaches both platforms; CI fails if generated outputs are stale.
- Web and mobile call the backend through one typed client generated from the FastAPI OpenAPI schema.
- Every user-visible string lives in one EN/HI/MR catalogue (Hindi/Marathi stubbed for human review).
- Performance budgets (section 6) are enforced by CI, not by convention.
- Every animation has a reduced-motion fallback.

## 2. Decisions already made

- **Two native UIs.** Web stays Next.js 16 / React 19; mobile stays Expo 52 / RN 0.76 / React 18. Components are **not** shared (React versions differ). Tokens, API client, i18n and types are shared.
- **Palette and typography:** keep the existing forest / brass / sage palette and the Fraunces + Inter look.

## 3. Out of scope

Page redesigns, the observability stack, LLM reliability work, job queue, security/supply-chain work, fraud detection, and any backend change. Each is a later workstream with its own spec.

## 4. Findings from the current code

- Colours are hand-duplicated: `apps/web/app/globals.css` (CSS variables) and `apps/mobile/src/theme/colors.ts` ("mirrors" web). They can drift.
- `globals.css` is one ~4,400-line file.
- Web loads four font families (Fraunces, Inter, JetBrains Mono, Plus Jakarta Sans) via a runtime Google Fonts `@import`: render-blocking and an external network call.
- Web (`app/lib/apiBase.ts` and friends) and mobile (`src/api/`) each have their own client and types.

## 5. Components

### 5.1 `packages/design-tokens`
- Single `tokens.json`: colour (dark and light), type scale, spacing, radii, elevation, z-index, motion durations and easings.
- Build script emits `tokens.css` (web) and `tokens.ts` (mobile).
- CI step regenerates and fails on diff.
- Initial `tokens.json` is derived from the current `globals.css` values so nothing visibly changes on adoption.

### 5.2 `packages/api-client`
- Typed client generated from the API's OpenAPI schema. Plain TypeScript, no React, so it runs on web and in React Native.
- Honours the existing error payload `{"detail", "message"}` and per-case authorization (ADR-009).
- Generation is scripted; CI fails if the generated client is stale against the schema.

### 5.3 `packages/i18n`
- One catalogue: English complete; Hindi and Marathi stubbed and flagged for human review (per AGENTS.md).
- Replaces `apps/web/app/translations.ts` and `apps/mobile/src/translations`.
- A CI check fails on keys missing in any locale or unused keys.

### 5.4 Motion system
A fixed vocabulary, implemented once per platform and reused by every page:
reveal-on-scroll, parallax layer, magnetic hover, shared-element transition, count-up, scroll-scrubbed timeline.

- **Web:** native CSS scroll-driven animations (`animation-timeline: view()`) as the base; Lenis smooth scroll (~3 KB); Motion via `LazyMotion` for interactive pieces; View Transitions between routes. Hero visuals are SVG/canvas. No WebGL.
- **Mobile:** Reanimated 3 + Gesture Handler; FlashList for long lists; haptics on key interactions.
- Each pattern ships with a reduced-motion variant. A lint rule rejects animation code that bypasses the shared patterns.

### 5.5 Fonts
- Self-hosted and subsetted with `next/font` on web; bundled assets on mobile. No Google Fonts calls.
- Fonts not used by the redesigned pages are dropped.

## 6. Performance budgets (CI gates)

| Platform | Budget |
|---|---|
| Web | Initial JS ≤ 170 KB per route; LCP < 2 s and CLS < 0.1 on throttled mid-range Android profile; Lighthouse CI on each PR |
| Web | Animated pages hold 60 fps in a scripted scroll trace |
| Mobile | JS bundle size cap; cold-start target; 60 fps check on animated screens |
| Both | Reduced-motion fallback present for every pattern |

Exact mobile numbers are fixed after a baseline measurement in the first plan task; they must not be set from guesses.

## 7. Governance

- New ADRs: token pipeline; self-hosted-only telemetry (WS1); job queue superseding the "without a broker" decision in ADR-019 (WS3).
- `PROJECT_CONTEXT.md` and relevant docs are updated per the Docs-as-Code gate.
- Zero-retention rule (ADR-003) is unchanged; nothing in this workstream stores documents.

## 8. Roadmap context (not part of WS0)

| WS | Topic |
|---|---|
| 1 | Observability: Prometheus, Grafana, Loki, Tempo, OTel Collector, Alertmanager (separate compose override file) |
| 2 | LLM reliability and CI eval harness (extends the existing Phase-4 evaluation work) |
| 3 | Platform: job queue with SSE progress, k6, chaos tests, SBOM/cosign, OPA/Kyverno |
| 4 | Web redesign, page by page |
| 5 | Mobile app, screen by screen |
| 6 | Bill anomaly detection (requires labelled data; no accuracy claims without it) |

Execution: WS0 first (serial). Then WS1, WS2, WS4-shell and WS5-shell in parallel git worktrees with disjoint files; WS3 and WS6 next. `main.py` and compose files are conflict hotspots: one owner per wave, observability in its own override file.

## 9. Risks and open items

- Pulling self-hosted Docker images (WS1) needs explicit user approval under the Network Boundaries rule. Not needed for WS0.
- Telemetry and logs must carry no PHI; redaction tests are required in WS1.
- Generated OpenAPI client quality depends on accurate response models in the API; gaps found will be listed in the plan, not silently worked around.
- Mobile performance targets depend on a baseline not yet measured.

## 10. Testing

- Token build: snapshot tests plus the stale-output CI check.
- API client: contract test against the running API's OpenAPI document.
- i18n: key parity and unused-key checks.
- Budgets: Lighthouse CI and mobile bundle-size check in CI.
- After any frontend change: dev server run and browser verification, per AGENTS.md.
