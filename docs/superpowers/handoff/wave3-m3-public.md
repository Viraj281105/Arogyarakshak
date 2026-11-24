# Handoff: Wave 3 M3, public site (branch `wave3/m3-public`)

**Date:** 2026-11-24. **Worktree:** `D:\wt\w3-m3-public`, branched from `wave3/integration` at `c3cb002`.
**Not touched:** `globals.css`, `layout.tsx`, `translations.ts`, `shell/*` except `SiteFooter.tsx`, `nav.ts`,
`commands.ts`, `app/app/**`, `app/review/**`, `hooks/**`, `lib/**`, `packages/**`, `apps/api/**`, `apps/mobile/**`,
`PROJECT_CONTEXT.md`, `CHANGELOG.md`, `KNOWN_VIOLATIONS`. Nothing pushed. No new npm dependency.

## Routes (exact list for M4's header nav and command palette)

| Route | Title | What |
|---|---|---|
| `/` | ArogyaRakshak — Healthcare deserves transparency | Landing, redesigned |
| `/platform` | Platform · ArogyaRakshak | Ecosystem, Kadi layer, consent-gated case context, evidence vocabulary, guest vs account |
| `/platform/kadi` | Kadi documents · ArogyaRakshak | Capability page |
| `/platform/billnyay` | BillNyay bill audit · ArogyaRakshak | Capability page |
| `/platform/daavisetu` | DaaviSetu pre-authorisation · ArogyaRakshak | Capability page |
| `/platform/bimanyay` | BimaNyay claim denials · ArogyaRakshak | Capability page |
| `/platform/schemesetu` | SchemeSetu scheme eligibility · ArogyaRakshak | Capability page |
| `/platform/dawacheck` | DawaCheck medicine prices · ArogyaRakshak | Capability page |
| `/how-it-works` | How it works · ArogyaRakshak | Upload → extract → analyse → verify → understand → act; how checks share a case |
| `/security` | Security and privacy · ArogyaRakshak | Implemented controls with sources, data flow table, limitations |
| `/about` | About · ArogyaRakshak | Mission, principles, names, what it is not, how it is built |
| `/help` | Help and FAQ · ArogyaRakshak | Searchable FAQ (18 questions), module guides, deleting data |

Any other `/platform/<x>` is a 404 (`dynamicParams = false`). For M4: import `PUBLIC_ROUTES`,
`PUBLIC_ROUTE_LABELS` from `apps/web/app/components/public/publicRoutes.ts` (tiny, safe for the shell) and
`PUBLIC_MODULE_IDS` / `platformModuleHref` / `allPublicPaths()` from `components/public/publicNav.ts`. In-page
anchors that exist: `/help#help-faq-title`, `/help#help-guides-title`, `/help#help-delete-title`,
`/security#sec-limits-title`, `/security#sec-flow-title`, `/help#faq-<id>`.

## Files

- `app/components/public/`: `copy/en.ts` (site copy + FAQ), `copy/modules.ts` (six capability pages),
  `copy/types.ts`, `publicCopy.ts` (en/hi/mr record), `publicRoutes.ts` (footer), `publicNav.ts`, `PublicParts.tsx`
  (server primitives), `PublicLanguageNotice.tsx` and `HelpSearch.tsx` (the only client parts), `faqFilter.ts` (pure
  search), `publicIcons.ts` (static icon geometry), `public.css`.
- Routes: `app/platform/page.tsx`, `app/platform/[module]/page.tsx`, `app/how-it-works/page.tsx`,
  `app/security/page.tsx`, `app/about/page.tsx`, `app/help/page.tsx`.
- Landing: `app/page.tsx`, `components/landing/{LandingHero,LandingPage,Landing,ModuleOverview,CaseJourney,WorkedExample}.tsx`
  changed, `LandingSections.tsx` new.
- `app/shell/SiteFooter.tsx`: five public links appended to the Explore list.
- `apps/web/tests/public_site.test.ts` (new, 20 tests).

## Design decisions

- **Server Components everywhere.** Client code on public pages: `PublicLanguageNotice` (shows a notice when हिंदी /
  मराठी is selected) and `HelpSearch`. On `/`, the capability tabs (`ModuleOverview`) only switch panels; labels and
  panels are server-rendered nodes passed as props. Copy never enters a client bundle (a test enforces it).
- **Landing lost the full translations dictionary.** It only needed module names; the overview is server-rendered now.
  `/` went from 162.23 to 151.79 KB.
- **No lucide components on public pages.** lucide-react 1.x icons are client components (`"use client"` in `Icon.mjs`).
  Rendering them from server pages made Turbopack split the shared layout chunk, and every route, `/app` included,
  grew by about 0.3 KB (measured: layout 12,399 B → 3,586 + 9,098 B). `/app` would then have failed its 183 KB ceiling.
  `publicIcons.ts` holds the same SVG geometry (ISC), drawn on the server; a test checks it equals the lucide files the
  shell maps use. The public `EvidenceBadge` in `PublicParts.tsx` renders the same markup, classes, labels and
  meanings as `components/ui/Badges.tsx`, with the static icon. If `ui/Badges` changes its markup, update both.
- **Footer kept minimal.** Labels in a separate 5-entry file; links appended to the existing list (no new column, since
  `shell.css` is not mine). Cost on every route: +0.15 KB.
- **Editorial system:** Fraunces display headings, Inter body, JetBrains Mono kickers/figures/paths; layered surfaces
  with thin borders; each capability has one accent (chart-series tokens, used only for icons, rules and fills, never
  text): Kadi cyan, BillNyay teal, DaaviSetu blue, BimaNyay violet, SchemeSetu amber, DawaCheck coral.
- **Motion:** CSS only. Section reveal uses scroll-driven animation (`animation-timeline: view()`) under
  `@supports` and `prefers-reduced-motion: no-preference`; content is visible by default. The landing keeps its existing
  JS reveal and scroll progress.
- **hi/mr:** `PUBLIC_COPY.hi` / `.mr` are explicit UNREVIEWED stubs (`translation: "pending"`, English text). Footer
  link labels are English in all languages (UNREVIEWED comment). The two notice strings in `publicNav.ts` are
  engineering-written Hindi/Marathi, marked NEEDS NATIVE-SPEAKER QA.

## Bundle sizes (gzip KB, fresh `next build`, Windows, Node 24.19.0)

| Route | Before (c3cb002) | After | Ceiling |
|---|---|---|---|
| `/` | 162.11 | 151.79 | 170 |
| `/app` | 182.74 | 182.89 | 183 (known violation, unchanged) |
| `/review` | 153.93 | 154.08 | 170 |
| `/_not-found` | 143.45 | 143.59 | 170 |
| `/_global-error` | 133.11 | 133.11 | 170 |
| `/platform`, `/platform/[module]`, `/how-it-works`, `/security`, `/about` | — | 144.13 | 170 |
| `/help` | — | 144.82 | 170 |

`/app` has 0.11 KB headroom left; anything else added to the shell (M4's header links) must be weighed against it.

## Verification (run 2026-11-24 on the final tree)

| Command | Result |
|---|---|
| `cd apps/web && npm install` | ok |
| `npx tsc --noEmit` | clean |
| `npm run lint` | clean |
| `npm test` (apps/web) | 275 tests, 275 pass (20 new in `public_site.test.ts`) |
| `npm run build` | passed; 16 static pages incl. six `/platform/<id>` |
| root `npm run check:web-budget` | PASS (table above) |
| root `npm test` | 75 pass |
| root `npm run check:generated` | 3 checks passed |

**Browser (built-in browser pane, `next dev` on port 3101, no API running):**
- All 12 routes return 200; `/platform/nope` returns 404.
- Horizontal overflow measured in same-origin iframes at 360, 768, 1280 and 1440 px for all 12 routes: found
  12–173 px overflow on the six module pages at 360/768 (long repository paths); fixed (`overflow-wrap`) and
  re-measured: 0 on all 48 combinations. Every route has exactly one `<h1>`.
- Screenshots looked at: `/` 1280 dark and 360 light (hero, capability panel); `/platform/billnyay` 1280 dark (hero,
  how it works, worked example); `/platform` 1440 light (hero, ecosystem); `/security` 768 dark; `/help` 1440 light.
  Fixed from what was seen: inputs/outputs cards too narrow side by side; heroes without an aside left the title in a
  narrow column.
- Keyboard on `/`: Tab order is skip link → home → theme → menu → hero CTAs → reviewer link → the selected capability
  tab (one tab stop) → its panel and links → worked-example lines → section links → FAQ summaries → CTA → footer.
  ArrowDown ×2 from Kadi moved focus and selection to DaaviSetu with only its panel visible and roving tabindex correct.
- Help search: typing "delete" showed 4 of 18 questions with a live count.
- Switching to हिंदी on `/platform` showed the English-only notice; header/footer switched as before.
- Console: only `ERR_CONNECTION_REFUSED` (demo-status call to the API, which was not running).

## Not verified

- Reduced motion in the browser (the pane cannot emulate it); only the CSS structure is tested.
- Every page in both themes at every width by eye: overflow was measured for all, screenshots were taken for the
  pages listed above only. 1024 and 390 px not checked.
- Screen reader. Marathi notice on screen (code path is the same as Hindi). Lighthouse. Linux CI bundle measurement.
- Contrast of the new color-mix tints (accent backgrounds at 12–20%) is not in the token contrast test; text on them
  uses `text-primary`/`text-secondary`.
- Maintainer sign-off (definition of done item 8) has not happened.

## Content facts and their sources

| Fact on the site | Source |
|---|---|
| 27 CGHS rows, 15 categories, version CGHS-2024-REVISED, no retrieval date | `packages/billnyay/billnyay/data/cghs_rates.json` via `lib/referenceSnapshot.ts` |
| Law library: 5 provisions, 1 verified 2026-09-13 | `billnyay/data/law_library.json` |
| 7 NPPA formulations, no notification date | `packages/dawacheck/dawacheck/reference_data.py` |
| Upload types PDF/JPG/JPEG/PNG/WEBP/BMP/TXT/CSV, 10 MB | `apps/api/app/api/v1/endpoints/kadi/cases.py`, `app/config.py` |
| 8,000 px / 40 MP image limits; OCR English default, hi/mr optional | `packages/kadi/kadi/ocr/ocr_parser.py` |
| First 6,000 characters sent to Groq when a key is set; heuristic fallback otherwise | `packages/kadi/kadi/extraction.py` |
| Redaction scope (names, phone, email, Aadhaar, PAN, ABHA, address) | `packages/kadi/kadi/privacy/redaction.py` |
| Readiness states and which checks auto-run | `packages/kadi/kadi/triggers.py` |
| Consent stored on the case, checked per route | `apps/api/app/consent.py` |
| 90-day TTL, 6-hour sweep | `apps/api/app/config.py`, `app/case_retention.py`, ADR-010 |
| scrypt N=2^15 r=8 p=3, 12–128 chars, sessions, cookie, throttle, enumeration, deletion, mail disabled | ADR-026 |
| PBKDF2 600,000 → AES-256-GCM, DaaviSetu web only | ADR-014 |
| HMAC-signed appeal PDF | `apps/api/app/services/billnyay_appeal.py` |
| On-device read-aloud only | ADR-016 |
| No analytics in the web app | grep of `apps/web/app` (no analytics imports); fonts via `next/font/local` |
| BimaNyay rules, deadlines 15/15/365 calendar days, room-rent ground unverified | `packages/bimanyay/bimanyay/clause_auditor.py`, `tracker.py` |
| SchemeSetu: only residence decides; PM-JAY always ambiguous; "Pune" → Maharashtra | `packages/schemesetu/schemesetu/agent.py`, `thresholds.py`, `dialect_normalizer.py` |
| DawaCheck price basis, ₹33 strip example (+1,335% before ADR-012) | ADR-012, `dawacheck/price_basis.py` |
| DaaviSetu: Annexure-B layout, no insurer template shipped, manifest excludes originals | `packages/daavisetu/daavisetu/{generator,form_filler,package_assembler,readiness}.py` |
| Outcome estimate gives no number (no non-synthetic dataset ships) | `billnyay/outcome/dataset.py`, `data/dispute_outcomes/` (README only) |

Worked examples on module pages are labelled "Synthetic example" and say "made-up"; BillNyay's uses the same
`lib/illustrativeBill.ts` lines as the landing page.

## Follow-ups

1. **M4:** header nav and command palette entries for the routes above; mind `/app`'s 0.11 KB headroom (the labels are
   in `publicRoutes.ts`; reusing them adds nothing new).
2. **M4:** when web account pages and guest `sessionStorage` land, update `/help` (`delete-account`, `delete-case`,
   `account` FAQ entries and the deletion card) with the real UI steps, and `/platform`'s access table if anything
   changes. Today they describe API behaviour, not a web screen.
3. Native-speaker Hindi and Marathi copy for the public site (replace the stubs in `publicCopy.ts`, footer labels in
   `publicRoutes.ts`, review the two notice strings).
4. If the mail transport, DaaviSetu insurer integration, more reference data or new OCR languages arrive, update
   `copy/en.ts` / `copy/modules.ts` (the limitations are stated as facts about this build).
5. Consider making lucide icons usable from Server Components project-wide (static geometry like `publicIcons.ts`) to
   remove the client-reference chunk split for other server pages too.
