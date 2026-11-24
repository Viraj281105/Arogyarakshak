# ArogyaRakshak — Typography System Specification

**Primary Heading Face:** Manrope (Variable, weights `500–800`)  
**Primary Interface & Body Face:** Inter (Variable, weights `400–600`)  
**Tabular Figures, Clauses & IDs:** JetBrains Mono (Variable, weights `400–600`)  
**Devanagari (Hindi / Marathi) Fallback:** `'Noto Sans Devanagari', 'Nirmala UI', 'Mangal', sans-serif`

---

## 1. Font Loading & Zero-External-Request Architecture

ArogyaRakshak enforces strict zero-third-party-network privacy on the client (no Google Fonts CDN requests).

- **Current repo state (`apps/web/package.json` & `apps/web/app/fonts.ts`):** Self-hosts `@fontsource-variable/fraunces`, `@fontsource-variable/plus-jakarta-sans`, `@fontsource-variable/inter`, and `@fontsource-variable/jetbrains-mono` via `next/font/local` with metric-matched fallbacks (`CLS = 0`).
- **Transformation change:**
  1. Add `@fontsource-variable/manrope` (`next/font/local`, `latin` preloaded + `latin-ext` lazy) and map `--font-headline` and `--font-display` to **Manrope**.
  2. Retain `@fontsource-variable/inter` (`--font-sans`) and `@fontsource-variable/jetbrains-mono` (`--font-mono`).
  3. Deprecate and remove `@fontsource-variable/fraunces` and `@fontsource-variable/plus-jakarta-sans` once migration completes, reducing web font payload and keeping initial route JS/CSS well within budgets.
  4. On React Native (`apps/mobile/src/theme/fontFamily.ts`), bundle Manrope + Inter static TTF weights for Latin and route Devanagari strings cleanly to the OS system Devanagari face.

```css
:root {
  --font-display: var(--font-face-manrope, 'Manrope'), 'Manrope', -apple-system, BlinkMacSystemFont, 'Noto Sans Devanagari', 'Nirmala UI', sans-serif;
  --font-headline: var(--font-face-manrope, 'Manrope'), 'Manrope', -apple-system, BlinkMacSystemFont, 'Noto Sans Devanagari', 'Nirmala UI', sans-serif;
  --font-sans: var(--font-face-inter, 'Inter'), 'Inter', -apple-system, BlinkMacSystemFont, 'Noto Sans Devanagari', 'Nirmala UI', sans-serif;
  --font-mono: var(--font-face-mono, 'JetBrains Mono'), 'JetBrains Mono', ui-monospace, SFMono-Regular, 'Noto Sans Devanagari', monospace;
}
```

---

## 2. Fluid Type Scale

Every heading uses `clamp()` for smooth scaling from `360px` mobile to `1440px` desktop without breakpoint jumps.

| Token | Role | Font Family | Fluid Size (`min → max`) | Weight | Line Height | Letter Spacing |
|---|---|---|---|---|---|---|
| `--type-display-xl` | Hero Display (`<h1>` Landing) | Manrope | `clamp(2.25rem, 4.2vw, 3.5rem)` (`36px → 56px`) | `700` | `1.12` | `-0.03em` |
| `--type-display-lg` | Page Title (`<h1>` Public/App) | Manrope | `clamp(1.75rem, 2.8vw, 2.5rem)` (`28px → 40px`) | `700` | `1.18` | `-0.025em` |
| `--type-heading-lg` | Section Heading (`<h2>`) | Manrope | `clamp(1.375rem, 2vw, 1.75rem)` (`22px → 28px`) | `700` | `1.25` | `-0.02em` |
| `--type-heading-md` | Card / Panel Heading (`<h3>`) | Manrope | `clamp(1.125rem, 1.4vw, 1.375rem)` (`18px → 22px`) | `600` | `1.32` | `-0.015em` |
| `--type-heading-sm` | Sub-panel / Table Group (`<h4>`) | Manrope | `1rem` (`16px`) | `600` | `1.38` | `-0.01em` |
| `--type-body-lg` | Editorial Lead / Hero Subcopy | Inter | `clamp(1rem, 1.2vw, 1.125rem)` (`16px → 18px`) | `400` | `1.62` | `0em` |
| `--type-body-md` | Standard UI & Reading Copy | Inter | `0.9375rem` (`15px`) | `400` | `1.58` | `0em` |
| `--type-body-sm` | Metadata, Helper Text, Table Cells | Inter | `0.8125rem` (`13px`) | `400` | `1.50` | `0.005em` |
| `--type-label-md` | Form Labels, Button Labels, Tabs | Inter | `0.875rem` (`14px`) | `600` | `1.35` | `0em` |
| `--type-label-xs` | Eyebrow Kickers, Provenance Badges | Inter / Mono | `0.75rem` (`12px`) | `600` | `1.30` | `0.04em` |
| `--type-metric-lg` | Key Financial Figure (`₹1,84,500`) | JetBrains Mono | `clamp(1.5rem, 2.2vw, 2rem)` (`24px → 32px`) | `600` | `1.20` | `-0.02em` |
| `--type-metric-md` | Table Amounts, Per-Unit Ceilings | JetBrains Mono | `0.9375rem` (`15px`) | `500` | `1.35` | `0em` |
| `--type-code` | Case IDs, SHA-256, IRDAI Clauses | JetBrains Mono | `0.8125rem` (`13px`) | `400` | `1.45` | `0.01em` |

---

## 3. Indian Numbering, Currency & Multilingual Rules

1. **Indian Lakh/Crore Grouping (`en-IN`):** Every monetary value MUST format via `Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 2 })` (e.g., `₹1,84,500`, `₹2.20 / tablet`).
2. **Tabular Numerals Everywhere:** Apply `font-variant-numeric: tabular-nums lining-nums` on all bill tables, price bars, SLA countdowns, and confidence meters so decimal points and columns align vertically.
3. **Devanagari Typography Adjustments (`:lang(hi)`, `:lang(mr)`):**
   - Increase `line-height` by `+0.12` (minimum `1.65` for body, `1.35` for headings) to give upper *matras* (शिरेखा / मात्रा) and lower vowel signs breathing room without clipping.
   - Reset negative heading `letter-spacing` to `0em` for Devanagari (`letter-spacing` breaks ligature connections in Devanagari scripts).
4. **Simple Language Mode:** When the user enables *Simple Language* in `/app/settings`, body font size scales up by `+1px`, line length caps at `62ch`, and jargon terms receive inline plain-language glosses.
5. **API-Sourced English Text Inside HI/MR Views:** Any backend-generated English string (e.g., raw CGHS rate names, audit timeline keys) MUST carry `lang="en"` so screen readers pronounce it accurately.
