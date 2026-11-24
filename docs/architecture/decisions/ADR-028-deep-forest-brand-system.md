# ADR-028: Deep Forest / Warm Ivory brand system (tokens, type, emblem, illustration library)

## Status
Accepted (2026-11-24). Supersedes the Wave 3 M2 navy/teal palette (tokens only; component structure is unchanged).

## Context
The maintainer supplied a transformation package (`docs/transformation/`) and Google Stitch mockups
(<https://stitch.google.com/projects/847521722700511340>) defining an official palette (Deep Forest #142F2B,
Secondary Forest #244C42, Muted Sage #91B49C, Pale Sage #D5E7D9, Warm Ivory #F4F1E8, text #1D2925 / #64766C,
borders #E2E2D8; semantic Verified #397A58, AI-derived #52769B, Human-reviewed #8066A5, Needs attention
#C28A35, Critical #C4544F, Not assessed #89918C), Manrope + Inter, light as the primary theme, a custom
emblem and an SVG illustration and motion system. Page implementation is split: Claude Code builds this
foundation, Antigravity builds pages on it, and Claude Code reviews them (`docs/transformation/ANTIGRAVITY_HANDOFF.md`).

## Decision
1. **Token values change, token names do not.** `packages/design-tokens/tokens.json` keeps every existing name
   (parity test), so no consumer breaks. New groups: `palette-*` (official seeds), `semantic-*` (the six
   semantic seeds, for marks), `module-*` (module accents), `chart-ai`, `chart-human`, `shadow-sm/md/lg`.
2. **Light is the default for everyone.** `<html data-theme="light">` is rendered on the server and the
   pre-paint script no longer follows the OS dark preference. Dark stays available as an explicit choice.
3. **Accessibility overrides the brief where they conflict.** `#64766C` is 4.3:1 or less on the ivory
   surfaces, so `text-secondary`/`text-muted` use `#52635A`/`#55665D`; `#64766C` remains as
   `palette-ink-secondary` for non-text use. Amber, red and grey seeds are used for marks (icons, bars,
   borders); text uses ink-grade shades (`#7A5312`, `#962F2B`, `#4E5651`). `contrast.mjs` checks every pair
   in both themes.
4. **A ninth evidence state, `human-reviewed`,** distinguishes finalised reviewer statements from AI output
   (web, mobile, icons, glyph, tokens).
5. **Type:** Manrope (display and headlines) and Inter (body) through `next/font/local` from the installed
   Fontsource files (no network). Fraunces and Plus Jakarta Sans are removed.
6. **Emblem:** a protective shield, two leaves cradling a human figure, a medical cross on the figure's chest.
   One geometry module (`app/components/brand/geometry.ts`) feeds the React components and the static files
   (`scripts/brand-assets.ts` writes SVGs and PNG icons with the `sharp` that Next.js already installs). At 32 px
   and below the figure is dropped (compact symbol). A first draft with a narrow arched torso read as a
   gravestone and was replaced.
7. **Illustrations and backgrounds are plain SVG + CSS** (no Lottie, Rive or GSAP: bundle budget and no new
   network dependency). They render on the server, cost no JS, take colours only from tokens, are decorative
   by default, use deterministic geometry, and every animation stops under reduced motion. Hospital crosses are
   green, never red (a red cross on white is a protected emblem).

## Consequences
- `/app` initial JS rose from 166.27 to 167.71 KB gzip (the emblem in the client header); every route still
  passes the 170 KB budget but the workspace has about 2 KB of headroom.
- Mobile receives the new colours through the generated `tokens.ts`; mobile screens still need the M7 visual pass.
- Hindi/Marathi copy is unchanged; the new evidence label "Human-reviewed" needs native-speaker translation.
- Not verified: PWA installation on a device; the Stitch mockups could not be opened without the
  maintainer's Google sign-in, so visual parity with them is unchecked.

## Amendment (2026-11-25, post-Antigravity review)
The client shell (`SiteHeader`, `SiteFooter`) no longer imports the brand components: it renders the static
`public/brand/*.svg` files as a light/dark `<img>` pair (`.ar-only-light` / `.ar-only-dark` in `brand.css`). Reasons:
the components put the full emblem geometry into every route's client JS (part of a regression to 168.6 KB), and
the header/footer always used the light emblem, which was nearly invisible in dark mode. The auth pages' brand panel
moved to the Server Component `components/auth/AuthSplit.tsx` for the same reason. The components remain the way
Server Components and pages draw the brand. See `docs/transformation/IMPLEMENTATION_STATUS.md` section 4.

