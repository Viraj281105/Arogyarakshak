# ArogyaRakshak — Testing, Performance & Deployment Verification Plan

**Status:** Approved Planning Blueprint  
**Goal:** Guarantee zero regressions across backend contracts, frontend bundle budgets, WCAG AA accessibility, and privacy invariants throughout the transformation.

---

## 1. Automated Testing Strategy

### Existing Test Suites (Must Stay 100% Green)
- **Backend (`pytest`):** 143 test files (`apps/api/tests`, `packages/*/tests`, `tests/chaos`, `tests/infrastructure`), 6 `import-linter` contracts, `alembic check`, `scripts/ci_guardrails.py`, `scripts/check_eval_regression.py`.
- **Web (`apps/web/tests/`):** 28 test suites (`tsx --test`) covering primitives, shell, workspace, public site, contracts, icons, fonts, motion, tokens adoption, code splitting, package crypto, and translations.
- **Mobile (`apps/mobile/`):** Jest test suite + `tsc --noEmit`.
- **Design Tokens (`packages/design-tokens/`):** `build.test.mjs` and `contrast.test.mjs` (113+ pairs/theme).

### New Tests to Add During Transformation
1. **Token & Light-Default Lock (`tokens_adoption.test.ts` + `contrast.test.mjs`):**
   - Assert `:root` resolves to Warm Ivory (`#F4F1E8`) / Deep Forest (`#142F2B`) Light mode by default.
   - Assert every one of the 6 semantic badge pairs meets WCAG AA (`>= 4.5:1` for text, `>= 3.0:1` for UI fill/icon).
   - Assert zero legacy navy/cyan hex literals (`#101B2A`, `#43C6D5`, `#0B6B64`) remain in production CSS.
2. **Evidence Explorer & Chart Honesty Tests:**
   - Assert `EvidenceGraph`, `WaterfallChart`, `DonutChart`, `ReasoningFlowChart`, and `PriceBar` each render `role="img"`, an accessible `<table>`, and explicit `source` / `basis` metadata.
   - Assert no clinical or financial finding uses `CountUp` animation from zero.
3. **Interactive Browser E2E Verification (Playwright or Browser Subagent Checklist):**
   - Add a lightweight CI-optional Playwright smoke suite (or scripted browser verification) exercising: Public `/` → Guest Upload → SSE stream → BillNyay Audit → Evidence Explorer node click → Register/Login → Claim Case → Settings Theme/Reduced-Motion → Permanent Delete.
4. **Reduced-Motion & Responsive Matrix:**
   - Automated check for `0px` horizontal overflow across `360px`, `390px`, `768px`, `1024px`, `1280px`, `1440px` in both Light and Dark themes.
   - Verify `data-motion="reduce"` and `prefers-reduced-motion: reduce` freeze all ambient & workflow animations.

---

## 2. Performance Budgets & Guardrails

| Metric / Asset | Hard Budget | Enforcement Mechanism |
|---|---|---|
| **Web Initial JS per Route** | **`<= 170 KB` gzip** (`KNOWN_VIOLATIONS = {}`) | `scripts/build-checks/web-bundle-budget.mjs` (CI-blocking) |
| **Public Pages (`/`, `/platform/*`, `/security`, `/terms`)** | **`<= 155 KB` gzip** | Pure Server Components; zero client copy bundles; static `publicIcons.ts` |
| **Mobile Android Export** | **`<= 2,600,000 B`** | `npm run check:mobile-budget` |
| **Lighthouse Mobile LCP** | **`<= 2,000 ms`** (warn `1,500 ms`) | `apps/web/lighthouserc.json` (`412×823`, 4× CPU) |
| **Lighthouse CLS** | **`<= 0.05`** (error `0.10`) | Metric-matched local `@fontsource-variable/manrope` + `inter` fallbacks |
| **SVG Asset Size** | Emblems `<= 2 KB`, Spot `<= 6 KB`, Hero `<= 14 KB` | SVGO pass + static test check |
| **Ambient Animation CPU** | GPU `transform`/`opacity` only, paused off-screen | `IntersectionObserver` gating; zero `filter`/`box-shadow` keyframe animations |

---

## 3. Deployment & Runtime Considerations

1. **Single-Process API Invariant (ADR-019):** Live SSE processing progress and login throttling remain in-memory per API process; keep single-worker Uvicorn (`apps/api/Dockerfile`) and `replicas: 1` in Kubernetes until a Redis/queue ADR is adopted.
2. **Cookie & CORS Production Alignment (ADR-026):** Production deployments MUST configure explicit `CORS_ORIGINS` (HTTPS web origin), `AUTH_TRUSTED_ORIGINS`, `SESSION_COOKIE_SECURE=true`, and non-default `DOCUMENT_SIGNING_SECRET`.
3. **No Service Worker (ADR-003):** Keep `manifest.webmanifest` with the newly generated PNG/SVG Deep Forest icons, and continue **omitting** a Service Worker so sensitive API responses or medical excerpts are never cached on shared devices.
4. **Zero-Network Font & Icon Privacy:** All fonts (`Manrope`, `Inter`, `JetBrains Mono`) and SVGs are bundled locally in `apps/web` — zero requests to `fonts.googleapis.com` or external CDNs.
