# Brief for Antigravity: page implementation on the Deep Forest / Warm Ivory foundation

**Written:** 2026-11-24 by the Claude Code session that built the foundation.
**Split agreed with the maintainer:** Claude Code built the foundation (tokens, fonts, brand, illustrations,
backgrounds). Antigravity builds the pages. Claude Code then reviews and corrects the result
(correctness, honesty rules, accessibility, budgets, browser checks) before anything is merged.

**Base branch:** `wave3/transformation`. Work on a new branch made from it (for example
`wave3/transformation-pages`). Never commit to `main` and never force-push.

**Mockups:** <https://stitch.google.com/projects/847521722700511340> (screen IDs in [README.md](README.md)).
They are a visual reference, not a source of facts. Where a mockup shows a figure, status or
feature the backend does not produce, follow the ground rules below, not the mockup.

---

## 1. Read these first

1. `AGENTS.md` (repository rules) and `apps/web/AGENTS.md` (this Next.js version differs from training data;
   read `apps/web/node_modules/next/dist/docs/` before using an unfamiliar API).
2. `PROJECT_CONTEXT.md`, the newest "Latest" entry.
3. [OPEN_QUESTIONS_AND_RISKS.md](OPEN_QUESTIONS_AND_RISKS.md): rulings that override the mockups.
4. `docs/architecture/decisions/ADR-028-deep-forest-brand-system.md` (the foundation's decisions).

## 2. What already exists: use it, do not rebuild it

| Need | Use | File |
|---|---|---|
| Colours, spacing, radii, shadows, motion timings | CSS variables only (`var(--bg-base)`, `var(--action-primary)`, `var(--semantic-verified)`, `var(--module-billnyay)`, `var(--shadow-md)` …). **Never write a hex value in page CSS.** | `packages/design-tokens/tokens.json` → `apps/web/app/generated/tokens.css` (generated: edit `tokens.json`, then `npm run generate` at the root) |
| Fonts | `var(--font-display)` (Manrope) for headings, `var(--font-sans)` (Inter) for body text, `var(--font-mono)` | `app/fonts.ts` |
| Logo | `ArogyaEmblem`, `ArogyaWordmark`, `ArogyaLogoAnimated`, `ArogyaLoader` | `app/components/brand/Brand.tsx` |
| Logo files (PDF, docs, OG images) | `public/brand/*.svg`, `public/icons/*` (regenerate with `npx tsx scripts/brand-assets.ts` in `apps/web`) | — |
| Illustrations (15) | `AnatomyIllustration`, `DnaIllustration`, `HeartbeatIllustration`, `CellIllustration`, `MoleculeIllustration`, `CapsuleIllustration`, `TabletsIllustration`, `PrescriptionIllustration`, `HospitalIllustration`, `PatientIllustration`, `MedicalRecordIllustration`, `InsuranceShieldIllustration`, `DocumentScanIllustration`, `OcrIllustration`, `EvidenceVerificationIllustration` (`animate` prop to turn on motion) | `app/components/illustrations/Illustrations.tsx` |
| Ambient backgrounds (5) | `MolecularNetworkBackground`, `ScientificGridBackground`, `BotanicalGeometryBackground`, `MedicalWaveformBackground`, `DocumentIntelligenceBackground` (put inside a `position: relative` parent) | `app/components/illustrations/Backgrounds.tsx` |
| Evidence labels (9 states) | `EvidenceBadge` with `verified`, `provisional`, `unevaluated`, `insufficient-evidence`, `ai-generated`, `human-reviewed`, `rule-engine`, `user-provided`, `external` | `app/components/ui/Badges.tsx`, `ui/evidence.ts` |
| Charts | `BarChart`, `StackedBarChart`, `DonutChart`, `WaterfallChart`, `TimelineChart` (plain SVG, accessible) | `app/components/ui/Charts.tsx` |
| Tables, states, steps, overlays | `DataTable`; `LoadingState`, `EmptyState`, `ErrorState`, `PartialResultState`, `InsufficientEvidenceState`; `StepWizard`, `Checklist`; `Dialog`, `ConfirmationDialog`, `Drawer`; `Tabs`, `Tooltip`; `useToast`; `PageHeader` | `app/components/ui/*` |
| Motion | `app/motion/*` (Reveal, Parallax, CountUp …). The `motion` package may only be imported inside `app/motion/**` (ESLint enforces it). | — |
| API calls | `app/lib/apiClient.ts`, `apiFetch.ts`, `caseApi.ts`, hooks in `app/hooks/*`; shared client in `packages/api-client` (vendored, regenerate with `npm run generate`) | — |

Open the dev galleries with `npm run dev` in `apps/web`: **`/brand`** (logo, illustrations, backgrounds) and
**`/primitives`** (components). They exist only in development.

## 3. Ground rules (a change that breaks one of these will be reverted in review)

1. **No fabricated data.** Every figure, score, saving, status or count comes from an API response, or is
   labelled on screen as a synthetic example. No testimonials, user counts, "₹ saved" totals or accuracy
   percentages.
2. **No document vault.** Uploaded files are never stored (ADR-003). Show Kadi provenance (file name, SHA-256,
   extracted entities, redacted excerpt), never a preview or a download of the original.
3. **Honest endings.** DaaviSetu and BimaNyay end at "Package ready" / "Draft prepared". Never "Submitted",
   "Approved" or approval odds. BimaNyay's rule score is a starting estimate out of 100, not a probability.
4. **Medicine prices:** never present MRP as the ceiling price; compare per unit, with the NPPA basis shown.
   Combination products and unknown medicines are refusals, not "within cap".
5. **BillNyay:** "above the CGHS benchmark" is not "illegal" or "overcharged". Show the benchmark row used.
6. **SchemeSetu:** provisional eligibility only, with the decision basis. PM-JAY is always "verification
   needed" (its criteria are not collected).
7. **AI vs human:** AI output carries `ai-generated`; only a finalised reviewer statement is `human-reviewed`,
   and reviewer credentials are "self-declared" unless the API says otherwise.
8. **Privacy:** no patient data in URLs, `console.log`, analytics or animation services. Case IDs never in URLs.
   No new network endpoints (no CDN fonts, no Lottie/Rive/GSAP, no third-party scripts).
9. **Light first.** Light is the default; dark must also work because every colour is a token.
10. **Hindi and Marathi:** add keys for new copy; mark new hi/mr strings `UNREVIEWED: NEEDS NATIVE-SPEAKER QA`.

## 4. Budgets and quality gates (all must pass before review)

- **Web bundle:** every route at or below 170 KB gzip of initial JS. `/app` routes are at about 167.7 KB, so
  there are only about 2 KB to spare there. Public pages must stay Server Components; load heavy client
  widgets with `next/dynamic`. Illustrations and backgrounds cost no JS: prefer them to client-side animation.
- **Contrast:** use the token pairs. If you add a new text/background combination, add it to
  `packages/design-tokens/contrast.mjs` and keep `node --test packages/design-tokens/tests/*.test.mjs` green.
- **Reduced motion:** every new animation must stop under `prefers-reduced-motion` and `[data-motion="reduce"]`.
- **Commands** (from the repo root unless noted):
  - `cd apps/web && npm run lint && npx tsc --noEmit && npm test && npm run build`
  - `npm run check:web-budget` and `npm run check:generated` and `npm test`
  - `cd apps/mobile && npx tsc --noEmit && npm test` (if shared packages change)
  - Backend untouched? Then no pytest is needed. If you touch `apps/api` or `packages/*` (Python), run the
    full `pytest` from the root with `PYTHONPATH=apps/api`.
- **Browser:** check each page at 360, 390, 768, 1024, 1280 and 1440 px, in light and dark, with keyboard only.
  There must be no horizontal scroll.

## 5. Page work, in priority order

| # | Page(s) | Mockup screen | Notes |
|---|---|---|---|
| 1 | Module workspaces `/app/case/<module>` (BillNyay, BimaNyay, DawaCheck, DaaviSetu, SchemeSetu) | 95be66a3…, fc0c3bba…, 275f3364…, 666810eb…, 4c9fa17d… | Biggest gap. Restyle the existing views in `app/components/modules/*` onto the shared primitives; wire the unused backend routes listed in [FRONTEND_ARCHITECTURE.md](FRONTEND_ARCHITECTURE.md) only where the API exists. |
| 2 | Kadi documents and Evidence Explorer (`/app/case`, evidence graph) | ee1967ba… | Provenance cards, entity review, graph with an accessible table equivalent. |
| 3 | Case desk `/app` and mobile layout | 20aa2636…, ca7216e9… | Real case list only. |
| 4 | Landing `/` and public pages | 5fdc7a05… (+ 9b26009a…, b7c94cf8…) | Use the illustrations and backgrounds; keep the existing honest copy (`components/public/copy/*`). |
| 5 | Sign-in pages (45/55 split) | 2471128a… | Forest panel with `ArogyaWordmark tone="dark"` + `BotanicalGeometryBackground`. Keep "email is not sent" honesty. |
| 6 | Settings, reports, `/review` | a49396f7…, a6dc0d84… | Keep account deletion and case deletion working. |

Keep every existing test passing. If a test encodes an old visual detail, update it so it still checks the
same intent. Never delete a test that checks an honesty or privacy rule.

## 6. What to hand back for review

A branch with logical commits (one per page group), and a short note per page: what changed, which API calls
it uses, which states were seen in the browser (empty, loading, error, partial, success), and anything that
was not done or not verified. Claude Code will then review the diff, fix what it finds, and re-run every gate.
