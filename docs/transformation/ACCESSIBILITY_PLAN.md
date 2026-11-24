# ArogyaRakshak — Accessibility & Inclusive Design Plan

**Compliance Target:** **WCAG 2.1 Level AA** across Web (`apps/web`) and Mobile (`apps/mobile`), with **AAA (`>= 7:1`)** for primary reading text and provenance badge labels.

---

## 1. Visual & Colour Accessibility

1. **Automated Contrast CI Gate (`packages/design-tokens/contrast.mjs`):**
   - Every foreground/background token pair in both Light (Default) and Dark (Optional) themes is checked automatically on every build (`>= 4.5:1` normal text, `>= 3.0:1` large text and UI boundaries).
   - **Ink-Grade Semantic Text:** Mid-tone semantic seed colours (`#C28A35` Needs Attention, `#C4544F` Critical, `#89918C` Not Assessed) are restricted to icons, chart fills, and borders; text inside badges uses darkened hue-matched ink tokens (`#7A5312` 6.5:1, `#962F2B` 7.1:1, `#4E5651` 7.0:1).
   - **Ivory Surface Rule:** Small secondary text directly on Warm Ivory (`#F4F1E8`) uses `#56675E` (5.2:1) rather than `#64766C` (4.3:1 on Ivory; 4.8:1 on White).
2. **Never Colour Alone:** Every status badge, chart segment, and Evidence Explorer node pairs colour with a distinct **icon/shape + explicit text label** so deuteranopia/protanopia/tritanopia users never lose meaning.
3. **Typography & Reflow:**
   - Supports `200%` browser text zoom and `320px` CSS-pixel reflow without text clipping or horizontal page scrolling.
   - Devanagari (`:lang(hi)`, `:lang(mr)`) enforces `line-height >= 1.65` and `letter-spacing: 0` to prevent *matra* clipping.

---

## 2. Keyboard Navigation & Focus Architecture

- **Skip Link:** First focusable element on every page (`SkipLink.tsx` → `#main-content` with `tabIndex={-1}`).
- **Visible Focus Ring:** High-contrast `2px solid #142F2B` outline + `2px` offset (`#91B49C` in dark mode) on `:focus-visible`. Never `outline: none`.
- **Command Palette (`Ctrl/Cmd + K`):** Full WAI-ARIA combobox/listbox keyboard navigation (`ArrowUp`/`ArrowDown`, `Enter`, `Escape`).
- **Native `<dialog>` Modals & Drawers:** Browser-native focus trapping, `Escape` dismissal, backdrop click dismissal, and focus restoration to the triggering control. **Bug Fix Required (found in Wave 3 M4 handoff):** Ensure `ConfirmationDialog` sets initial focus safely on the **Cancel** button (not the close `×` button or destructive Delete button).
- **WAI-ARIA Tabs & Steppers:** Roving `tabindex` (`ArrowLeft`/`ArrowRight`/`Home`/`End`) on landing capability tabs, BimaNyay appeal draft tabs, and Clinical Review workspace tabs.
- **Evidence Explorer Graph:** Every SVG node is a keyboard-focusable `<g role="button" tabIndex={0} aria-label="...">` supporting `Tab`, `Enter`/`Space` to open the Provenance Inspector, and `Escape` to close.

---

## 3. Screen Reader & Semantic Landmarks

- **Landmarks:** Exactly one `<header>`, one `<nav aria-label="...">`, one `<main id="main-content">`, one `<footer>`, and exactly **one `<h1>`** per route.
- **Live Regions:**
  - SSE Kadi processing stages, FAQ search counts, and toast notifications announce via `aria-live="polite" role="status"`.
  - Form validation errors, 401 session expiry, and Clinical Safety Escalations announce via `aria-live="assertive" role="alert"`.
- **Chart Accessibility:** Every SVG chart in `ui/Charts.tsx` carries `role="img"` + descriptive `aria-label` (stating metric, units, source, and estimate/verified basis) plus an immediately adjacent `<details><summary>View data table</summary><table>...</table></details>`.
- **Multilingual `lang` Attributes:** `<html lang="en|hi|mr">` updates dynamically with `LanguageSwitcher`. API-sourced English strings rendered inside Hindi/Marathi views carry explicit `lang="en"`.

---

## 4. Cognitive Accessibility & Assistive Features (Preserved & Elevated)

1. **Simple Language Mode (`/app/settings` & header):** Switches complex clinical/legal phrasing to plain-language summaries with shorter line lengths (`62ch`) and larger body text.
2. **On-Device Read-Aloud (`ListenSummary.tsx`, ADR-016):** Browser Web Speech API reads findings, appeal summaries, and prescription translations aloud in EN/HI/MR with zero external network calls; cleanly toggleable in Settings.
3. **Dual Reduced-Motion Support:** Respects OS `@media (prefers-reduced-motion: reduce)` AND in-app `<html data-motion="reduce">` toggle (applied pre-paint via `layout.tsx` `<script>`).

---

## 5. Verification Checklist Before Release

- Automated `packages/design-tokens/contrast.mjs` passes 100% of pairs (0 failures).
- Full keyboard-only walkthrough (no mouse) across Landing, Login, Case Desk, Evidence Explorer, all 5 Module Workspaces, Settings, and `/review`.
- Screen-reader spot checks (NVDA on Windows / VoiceOver on macOS/iOS) verifying SSE announcements, `EvidenceBadge` labels, `ConfirmationDialog` focus, and `lang="en"` transitions inside Hindi/Marathi views.
- Lighthouse Accessibility score `>= 95` on `/` and `/app`.
